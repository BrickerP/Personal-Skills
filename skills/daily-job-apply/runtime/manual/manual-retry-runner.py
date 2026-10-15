#!/usr/bin/env python3
"""Run manual-retry queue with proper CSV parsing (handles commas in role titles)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[2]
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

sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_LOG = WORK_DIR / 'manual-retry.log' / "manual-retry-20260616.log"
DEFAULT_LOCKDIR = WORK_DIR / '.ashby-apply.lockdir' / ".ashby-apply.lockdir"
DEDUPE = SCRIPTS_DIR / 'job_dedupe_check.py' / "skills" / "daily-job-apply" / "scripts" / "job_dedupe_check.py"
APPLY = ADAPTERS_DIR / 'ashby_apply_applescript.py' / ".omx" / "ashby_apply_applescript.py"
TRACKER = TRACKER_CSV


def log_line(log_path: Path, text: str) -> None:
    print(text)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def verified_counts() -> tuple[int, int, int]:
    rows = list(csv.DictReader(TRACKER.open(newline="", encoding="utf-8")))
    verified = 0
    for day in ("2026-06-12", "2026-06-13", "2026-06-14", "2026-06-15", "2026-06-16", "2026-06-17"):
        verified += sum(
            1
            for row in rows
            if (row.get("Date") or "").startswith(day)
            and row.get("Application_Submitted") == "Yes"
            and row.get("Response_Status") in ("Submitted", "DuplicateSubmitted")
        )
    manualfinish = sum(1 for row in rows if row.get("Stage") == "ManualFinish")
    blocked = sum(1 for row in rows if row.get("Stage") == "Blocked")
    return verified, manualfinish, blocked


def run_apply(company: str, role: str, url: str, variant: str, log_path: Path) -> int:
    proc = subprocess.run(
        [
            sys.executable,
            "-u",
            str(APPLY),
            "--company",
            company,
            "--role",
            role,
            "--url",
            url,
            "--variant",
            variant,
            "--allow-auth-boolean",
            "--allow-manual-retry",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = proc.stdout or ""
    print(output, end="")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(output)
        if output and not output.endswith("\n"):
            handle.write("\n")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--wave-label", default="manual-retry")
    parser.add_argument("--form-load-wait", type=int, default=15)
    parser.add_argument("--sleep-between", type=int, default=90)
    args = parser.parse_args()

    queue = Path(args.queue)
    log_path = Path(args.log)
    form_load_wait = args.form_load_wait

    if not queue.exists():
        log_line(log_path, f"[error] queue not found: {queue}")
        return 2

    verified, manualfinish, blocked = verified_counts()
    log_line(log_path, "")
    log_line(log_path, f"=== {args.wave_label} start ===")
    log_line(log_path, f"queue={queue} lock={DEFAULT_LOCKDIR} form_load_wait={form_load_wait}s")
    log_line(log_path, f"baseline_verified={verified} manualfinish={manualfinish} blocked={blocked}")

    rows = list(csv.DictReader(queue.open(newline="", encoding="utf-8")))
    for row in rows:
        company = (row.get("company") or "").strip()
        role = (row.get("role") or "").strip()
        url = (row.get("url") or "").strip()
        variant = (row.get("variant") or "General SWE").strip()
        blocker = (row.get("blocker") or "").strip()
        action = (row.get("action") or "apply").strip().lower()

        if not company or not role:
            continue

        log_line(log_path, "")
        log_line(log_path, f"--- {company} | {role} ---")

        if action == "skip":
            log_line(log_path, f"[skip] {company} reason={blocker or 'explicit-skip'}")
            continue

        if action == "mark-submitted":
            log_line(log_path, f"[mark-submitted] {company} note={blocker or 'ashby-already-submitted-duplicate'}")
            subprocess.run(
                [
                    sys.executable,
                    str(APPLY),
                    "--company",
                    company,
                    "--role",
                    role,
                    "--url",
                    url,
                    "--variant",
                    variant,
                    "--dry-run",
                    "--no-record",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Direct tracker update via apply script record helper
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; sys.path.insert(0, 'str(ADAPTERS_DIR)'); "
                        "from ashby_apply_applescript import record; "
                        f"record({company!r}, {role!r}, {url!r}, 'DuplicateSubmitted', "
                        f"{blocker or 'ashby-already-submitted-duplicate'!r}, True, {variant!r})"
                    ),
                ],
                check=False,
            )
            continue

        log_line(log_path, f"[dedupe] {company}")
        dedupe = subprocess.run(
            [
                sys.executable,
                str(DEDUPE),
                "--company",
                company,
                "--role",
                role,
                "--url",
                url,
                "--company-cap",
                "20",
            ],
            text=True,
            capture_output=True,
        )
        log_line(log_path, (dedupe.stdout or dedupe.stderr or "").strip())

        if blocker in {"invalid-required-fields", "form-not-loaded", "submit-button-not-found"}:
            log_line(log_path, f"[preflight-wait] blocker={blocker} sleeping {form_load_wait}s before apply")
            time.sleep(form_load_wait)

        log_line(log_path, f"[apply] {company}")
        rc = run_apply(company, role, url, variant, log_path)
        log_line(log_path, f"[apply-exit] company={company} rc={rc}")
        time.sleep(args.sleep_between)

    verified, manualfinish, blocked = verified_counts()
    log_line(log_path, f"final_verified={verified} manualfinish={manualfinish} blocked={blocked}")
    log_line(log_path, f"=== {args.wave_label} done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
