"""Refresh Gmail cache for all active mailboxes as a short-lived local task."""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import WorkerConfig
from gmail_ai_worker.gmail_client import (
    build_gmail_service,
    collect_snapshot_bundle,
    get_profile_email,
    write_json,
)
from gmail_ai_worker.mailboxes import MailboxRegistry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    """Refresh recent and review windows for each active mailbox."""
    socket.setdefaulttimeout(30)
    config = WorkerConfig.from_env()
    config.ensure_runtime_directories()
    registry = MailboxRegistry()
    settings_path = config.runtime_dir / "skill_settings.json"
    settings = (
        json.loads(settings_path.read_text(encoding="utf-8"))
        if settings_path.exists()
        else {}
    )
    automation_defaults = settings.get("automation_defaults", {})
    recent_query = automation_defaults.get("hourly_recent_query", config.gmail_query)
    review_query = automation_defaults.get("daily_review_query", config.gmail_query)
    recent_limit = int(automation_defaults.get("recent_scan_limit", 50))
    review_limit = int(
        automation_defaults.get(
            "max_candidate_threads_scan",
            automation_defaults.get("review_scan_limit", config.max_threads),
        )
    )

    results: list[dict[str, object]] = []
    had_failure = False
    for mailbox_key in registry.data.get("active_mailboxes", []):
        mailbox = registry.resolve_mailbox(mailbox_key)
        token_path = Path(mailbox["token_path"]).expanduser()
        mailbox_result: dict[str, object] = {
            "mailbox_key": mailbox_key,
            "email": mailbox["email"],
        }
        try:
            service = build_gmail_service(token_path)
            self_email = get_profile_email(service)
            mailbox_result["recent"] = collect_snapshot_bundle(
                service,
                self_email=self_email,
                query=recent_query,
                max_threads=recent_limit,
                messages_per_thread=config.messages_per_thread,
                excerpt_chars=config.excerpt_chars,
            )
            mailbox_result["review"] = collect_snapshot_bundle(
                service,
                self_email=self_email,
                query=review_query,
                max_threads=review_limit,
                messages_per_thread=2,
                excerpt_chars=min(config.excerpt_chars, 1200),
            )
            mailbox_result["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            had_failure = True
            mailbox_result["status"] = "error"
            mailbox_result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(mailbox_result)

    cache_payload = {
        "generated_at": _utc_now_iso(),
        "recent_query": recent_query,
        "review_query": review_query,
        "mailboxes": results,
    }
    status_payload = {
        "generated_at": cache_payload["generated_at"],
        "mailbox_count": len(results),
        "ok_count": sum(1 for item in results if item.get("status") == "ok"),
        "error_count": sum(1 for item in results if item.get("status") == "error"),
        "errors": [
            {
                "mailbox_key": item["mailbox_key"],
                "error": item["error"],
            }
            for item in results
            if item.get("status") == "error"
        ],
    }

    write_json(config.refresh_cache_path, cache_payload)
    write_json(config.refresh_status_path, status_payload)
    print(json.dumps(status_payload, indent=2, ensure_ascii=False))
    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
