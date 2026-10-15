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
import json
import subprocess
import sys
from pathlib import Path


def dedupe_ok(script: Path, row: dict) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(script),
        "--company",
        row.get("company", ""),
        "--role",
        row.get("role", ""),
        "--url",
        row.get("url", ""),
        "--company-cap",
        "20",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, (proc.stdout or "").strip()
    return False, (proc.stdout or proc.stderr or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dedupe-script",
        type=Path,
        default=Path.home() / ".codex/skills/daily-job-apply/scripts/job_dedupe_check.py",
    )
    args = parser.parse_args()

    fields = [
        "status",
        "company",
        "role",
        "location",
        "url",
        "slug",
        "posting_id",
        "variant",
        "blocker",
        "published",
        "updated",
    ]
    rows_in = list(csv.DictReader(args.input.open(newline="", encoding="utf-8")))
    kept: list[dict] = []
    stats = {"checked": 0, "auto_in": 0, "dedupe_pass": 0, "dedupe_fail": 0, "not_auto": 0}

    for row in rows_in:
        if row.get("status") != "auto_candidate":
            stats["not_auto"] += 1
            continue
        stats["auto_in"] += 1
        stats["checked"] += 1
        ok, detail = dedupe_ok(args.dedupe_script, row)
        if ok:
            stats["dedupe_pass"] += 1
            kept.append(row)
        else:
            stats["dedupe_fail"] += 1
            print(json.dumps({"skip": row.get("company"), "role": row.get("role"), "detail": detail[:300]}), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(kept)

    summary = {"output": str(args.output), "kept": len(kept), **stats}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
