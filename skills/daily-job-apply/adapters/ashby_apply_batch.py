#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    SCRIPTS_DIR,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    PDF_DIR,
    resume_pdf,
)

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))

import argparse
import csv
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_SCRIPTS = SCRIPTS_DIR

from ats_evolution_log import evolve_from_attempt  # noqa: E402

SKIP_ROLE_RX = re.compile(r"\bAI Trainer\b", re.I)
SKIP_SLUGS = {
    "g2i",
    "g2iinc",
    "crusoe",
    "brainco",
    "lgads",
    "workos",
    "afterquery",  # spam cooldown 24h (round12c)
    "aida",  # spam cooldown 24h (round12c)
    "jackjillexternalats",  # runtime "Talk to Jack" gate not in metadata (round16)
    "scribe",  # platform-anti-bot spam flag (round29); temp skip
    "pearl",  # platform-anti-bot spam cooldown (round50/51)
    "scrunch",  # platform-anti-bot spam cooldown (round50/51)
}


def slug_key(row: dict) -> str:
    return re.sub(r"[^a-z0-9]+", "", (row.get("slug") or row.get("url") or "").casefold())


TRACKER = TRACKER_CSV
DEFAULT_CSV = WORK_DIR / 'candidate-pools' / 'ashby-fresh.csv' / "ashby-fresh-2026-06-10.csv"
APPLY = ADAPTERS_DIR / 'ashby_apply_applescript.py'
LOG_DIR = ADAPTERS_DIR / 'logs'


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")


def tracker_rows() -> list[dict]:
    if not TRACKER.exists():
        return []
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def submitted_count(rows: list[dict], count_date: str) -> int:
    return sum(
        1
        for row in rows
        if (row.get("Date") or "").startswith(count_date) and row.get("Application_Submitted") == "Yes"
    )


def load_queue(path: Path) -> list[dict]:
    rows = []
    for row in csv.DictReader(path.open(newline="", encoding="utf-8")):
        if row.get("status") != "auto_candidate":
            continue
        if SKIP_ROLE_RX.search(row.get("role", "")):
            continue
        key = slug_key(row)
        url_lower = (row.get("url") or "").lower()
        if key in SKIP_SLUGS or "/g2i/" in url_lower or "/crusoe/" in url_lower or "/workos/" in url_lower:
            continue
        rows.append(row)
    return rows


def run_apply(row: dict, *, allow_manual_retry: bool) -> tuple[int, str]:
    cmd = [
        "python3",
        str(APPLY),
        "--company",
        row.get("company", ""),
        "--role",
        row.get("role", ""),
        "--url",
        row.get("url", ""),
        "--variant",
        row.get("variant") or "AI Agent Infra",
        "--window",
        "1",
        "--allow-auth-boolean",
    ]
    if allow_manual_retry:
        cmd.append("--allow-manual-retry")
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode, output
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + ("\n" + (exc.stderr or "") if exc.stderr else "")
        return 124, output + "\n[batch] subprocess timeout after 600s"
    except Exception as exc:
        return 125, f"[batch] subprocess error: {exc}"


def parse_fields_missing(output_tail: str) -> list[str]:
    fields: list[str] = []
    for label in ("Phone Number", "Location", "Are you authorized", "city", "state"):
        if label.lower() in output_tail.lower():
            fields.append(label)
    return fields


def is_dedupe_only_output(output: str, returncode: int) -> bool:
    """True when output is job_dedupe_check JSON, not a live apply attempt."""
    if returncode != 20:
        return False
    lower = output.lower()
    return "duplicate-url" in lower and '"matches"' in output


def is_live_antibot_signal(output: str, returncode: int) -> bool:
    """Detect live page spam/CAPTCHA — ignore historical platform-anti-bot in dedupe ledger."""
    if is_dedupe_only_output(output, returncode):
        return False
    lower = output.lower()
    if '"code": "danger-text"' in output or '"code":"danger-text"' in output:
        return True
    if '"code": "platform-anti-bot"' in output or '"code":"platform-anti-bot"' in output:
        return True
    if '"danger": true' in lower or '"danger":true' in lower:
        return True
    if "danger-text" in lower:
        return True
    if "platform-anti-bot" in lower:
        return True
    return False


def record_failure(row: dict, code: int, output: str, *, submitted_after: int, submitted_before: int) -> None:
    if submitted_after > submitted_before:
        return
    status = "ManualFinish" if "ManualFinish" in output or code in (21, 22) else "Blocked"
    blocker = None
    lower = output.lower()
    if "phone" in lower:
        blocker = "phone-required-no-active-number"
    elif "resume-upload" in lower:
        blocker = "resume-upload-missing"
    elif is_live_antibot_signal(output, code):
        blocker = "platform-anti-bot"
    evolve_from_attempt(
        platform="ashby",
        url=row.get("url", ""),
        status=status,
        blocker=blocker or f"returncode-{code}",
        dom_snippet=output[-800:],
        fields_missing=parse_fields_missing(output),
        company=row.get("company", ""),
        role=row.get("role", ""),
        channel="ashby-batch",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--target-submitted", type=int, default=100)
    parser.add_argument("--count-date", default=dt.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--max-attempts", type=int, default=67)
    parser.add_argument("--max-attempts-per-slug", type=int, default=0)
    parser.add_argument("--min-success-gap", type=int, default=120)
    parser.add_argument("--allow-manual-retry", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"ashby-apply-batch-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    queue = load_queue(args.csv)
    initial = submitted_count(tracker_rows(), args.count_date)
    print(
        json.dumps(
            {
                "stage": "queue",
                "count": len(queue),
                "log": str(log_path),
                "submitted_date": args.count_date,
                "submitted_count": initial,
                "target_submitted": args.target_submitted,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    last_success = 0.0
    attempted = 0
    slug_attempts: dict[str, int] = {}
    skipped_antibot_slugs: set[str] = set()
    for row in queue:
        current = submitted_count(tracker_rows(), args.count_date)
        if current >= args.target_submitted:
            break
        if attempted >= args.max_attempts:
            break
        slug = slug_key(row)
        if args.max_attempts_per_slug and slug_attempts.get(slug, 0) >= args.max_attempts_per_slug:
            print(
                json.dumps(
                    {
                        "stage": "skip-slug-cap",
                        "reason": "max-attempts-per-slug",
                        "slug": slug,
                        "attempts": slug_attempts.get(slug, 0),
                        "cap": args.max_attempts_per_slug,
                        "company": row.get("company"),
                        "role": row.get("role"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue
        if last_success:
            remaining = args.min_success_gap - (time.time() - last_success)
            if remaining > 0:
                time.sleep(remaining)
        attempted += 1
        slug_attempts[slug] = slug_attempts.get(slug, 0) + 1
        before = current
        event = {
            "ts": now(),
            "stage": "attempt",
            "attempted": attempted,
            "submitted_date": args.count_date,
            "submitted_count_before": before,
            "company": row.get("company"),
            "role": row.get("role"),
            "url": row.get("url"),
        }
        print(json.dumps(event, ensure_ascii=False), flush=True)
        code, output = run_apply(row, allow_manual_retry=args.allow_manual_retry)
        after = submitted_count(tracker_rows(), args.count_date)
        result = {
            **event,
            "stage": "result",
            "returncode": code,
            "submitted_count_after": after,
            "output_tail": output[-2000:],
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        record_failure(row, code, output, submitted_after=after, submitted_before=before)
        if after > before:
            last_success = time.time()
        if is_live_antibot_signal(output, code):
            slug = slug_key(row)
            skipped_antibot_slugs.add(slug)
            SKIP_SLUGS.add(slug)
            print(
                json.dumps(
                    {
                        "stage": "skip-slug",
                        "reason": "platform-anti-bot",
                        "slug": slug,
                        "company": row.get("company"),
                        "role": row.get("role"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue

    final_count = submitted_count(tracker_rows(), args.count_date)
    print(
        json.dumps(
            {
                "stage": "done",
                "attempted": attempted,
                "skipped_antibot_slugs": sorted(skipped_antibot_slugs),
                "submitted_date": args.count_date,
                "submitted_count": final_count,
                "target_submitted": args.target_submitted,
                "log": str(log_path),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
