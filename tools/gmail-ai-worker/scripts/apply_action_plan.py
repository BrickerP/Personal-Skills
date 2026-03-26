"""Apply a Codex-authored Gmail action plan locally."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import WorkerConfig
from gmail_ai_worker.gmail_client import (
    build_gmail_service,
    build_thread_snapshot,
    create_reply_draft,
    get_profile_email,
    resolve_label_id,
    write_json,
)
from gmail_ai_worker.mailboxes import MailboxRegistry
from gmail_ai_worker.models import ActionPlan


BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _daily_progress_path(runtime_dir: Path) -> Path:
    return runtime_dir / f"daily_progress_{datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')}.md"


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _append_daily_progress(runtime_dir: Path, status_payload: dict) -> None:
    path = _daily_progress_path(runtime_dir)
    lines = [
        f"## {status_payload['applied_at']}",
        f"- Goal: {status_payload.get('goal', '')}",
        f"- Applied actions: {status_payload.get('applied_count', 0)}",
        f"- Skipped actions: {status_payload.get('skipped_count', 0)}",
    ]
    for item in status_payload.get("results", []):
        lines.append(
            f"- {item['status']} | {item['kind']} | {item['mailbox_key']} | {item['thread_id']} | {item['reason']}"
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n\n")


def _prune_old_daily_progress(runtime_dir: Path, keep_days: int = 31) -> None:
    """Keep only the most recent daily progress files.

    Args:
        runtime_dir: Runtime directory containing daily progress files.
        keep_days: Maximum number of daily files to keep.
    """
    progress_files = sorted(runtime_dir.glob("daily_progress_*.md"))
    if len(progress_files) <= keep_days:
        return
    for stale_path in progress_files[: len(progress_files) - keep_days]:
        stale_path.unlink(missing_ok=True)


def main() -> int:
    """Apply pending Gmail actions from the latest action plan."""
    config = WorkerConfig.from_env()
    config.ensure_runtime_directories()
    if not config.action_plan_path.exists():
        status_payload = {
            "applied_at": _utc_now_iso(),
            "goal": "No action plan available",
            "applied_count": 0,
            "skipped_count": 0,
            "results": [],
        }
        write_json(config.apply_status_path, status_payload)
        _append_daily_progress(config.runtime_dir, status_payload)
        _prune_old_daily_progress(config.runtime_dir)
        return 0

    plan = ActionPlan.from_dict(
        json.loads(config.action_plan_path.read_text(encoding="utf-8"))
    )
    state = _load_json(config.apply_state_path, {"applied_action_ids": []})
    applied_ids = set(state.get("applied_action_ids", []))
    registry = MailboxRegistry()

    results: list[dict[str, object]] = []
    applied_count = 0
    skipped_count = 0

    for action in plan.actions:
        result = {
            "action_id": action.action_id,
            "mailbox_key": action.mailbox_key,
            "thread_id": action.thread_id,
            "kind": action.kind,
            "reason": action.reason,
            "status": "skipped",
        }
        if action.action_id in applied_ids:
            result["status"] = "already_applied"
            skipped_count += 1
            results.append(result)
            continue
        if action.needs_human_review:
            result["status"] = "needs_human_review"
            skipped_count += 1
            results.append(result)
            continue

        mailbox = registry.resolve_mailbox(action.mailbox_key)
        token_path = Path(mailbox["token_path"]).expanduser()
        service = build_gmail_service(token_path)
        self_email = get_profile_email(service)
        snapshot = build_thread_snapshot(
            service,
            action.thread_id,
            self_email=self_email,
            messages_per_thread=config.messages_per_thread,
            excerpt_chars=config.excerpt_chars,
        )
        if snapshot.latest_message_id != action.latest_message_id:
            result["status"] = "stale_thread"
            result["current_latest_message_id"] = snapshot.latest_message_id
            skipped_count += 1
            results.append(result)
            continue

        if action.kind == "create_draft":
            if not action.body:
                result["status"] = "invalid_missing_body"
                skipped_count += 1
                results.append(result)
                continue
            draft = create_reply_draft(
                service,
                thread_id=action.thread_id,
                subject=action.subject or snapshot.subject,
                body_text=action.body,
                to=action.to or snapshot.default_reply_to,
                cc=action.cc,
                reference_message_id=snapshot.reference_message_id,
            )
            result["status"] = "draft_created"
            result["draft_id"] = draft.get("id")
        elif action.kind in {"modify_thread", "archive_thread"}:
            add_labels = [resolve_label_id(service, label) for label in action.add_labels]
            remove_labels = [
                resolve_label_id(service, label) for label in action.remove_labels
            ]
            if action.archive and "INBOX" not in remove_labels:
                remove_labels.append("INBOX")
            response = (
                service.users()
                .threads()
                .modify(
                    userId="me",
                    id=action.thread_id,
                    body={
                        "addLabelIds": add_labels,
                        "removeLabelIds": remove_labels,
                    },
                )
                .execute()
            )
            result["status"] = "thread_modified"
            result["response_thread_id"] = response.get("id")
        else:
            result["status"] = "unsupported_action"
            skipped_count += 1
            results.append(result)
            continue

        applied_ids.add(action.action_id)
        applied_count += 1
        results.append(result)

    state["applied_action_ids"] = sorted(applied_ids)
    config.apply_state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    status_payload = {
        "applied_at": _utc_now_iso(),
        "goal": plan.goal,
        "plan_generated_at": plan.generated_at,
        "applied_count": applied_count,
        "skipped_count": skipped_count,
        "results": results,
    }
    write_json(config.apply_status_path, status_payload)
    _append_daily_progress(config.runtime_dir, status_payload)
    _prune_old_daily_progress(config.runtime_dir)
    print(json.dumps(status_payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
