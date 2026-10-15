#!/usr/bin/env python3
"""Emit or backfill Obsidian application batch rows.

This helper is intentionally small and dependency-free. It is used by
daily-job-apply after verified external ATS submissions and for one-off
historical repair from tracker.csv.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path


DEFAULT_TRACKER = Path.home() / "job-hunt" / "tracker.csv"
DEFAULT_APPLICATIONS = Path(
    "/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/applications"
)
SUBMITTED_RE = re.compile(r"^(yes|true|1)$|submitted|applied", re.I)


def today_bjt() -> str:
    # The local machine is normally BJT; keep this deterministic without deps.
    return dt.datetime.now().strftime("%Y-%m-%d")


def normalize_channel(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    if "linkedin" in text:
        return "linkedin"
    if "greenhouse" in text:
        return "greenhouse"
    if "lever" in text:
        return "lever"
    if "ashby" in text:
        return "ashby"
    if "workday" in text:
        return "workday"
    if "referral" in text:
        return "referral"
    if "direct" in text or "company" in text:
        return "direct"
    cleaned = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return cleaned or "unknown"


def status_from_tracker(row: dict[str, str]) -> str:
    submitted = row.get("Application_Submitted", "")
    response = row.get("Response_Status", "")
    stage = row.get("Stage", "")
    if SUBMITTED_RE.search(f"{submitted} {response} {stage}"):
        return "Submitted"
    if re.search(r"manual", f"{response} {stage}", re.I):
        return "ManualFinish"
    if re.search(r"blocked", f"{response} {stage}", re.I):
        return "Blocked"
    if re.search(r"skipped", f"{response} {stage}", re.I):
        return "Skipped"
    return response.strip() or stage.strip() or "Touched"


def row_date(row: dict[str, str]) -> str:
    for key in ("Date", "Submitted_At", "Applied_Date", "Last_Updated"):
        value = (row.get(key) or "").strip()
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)
    return ""


def md_cell(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", r"\|").strip()


def split_md_row(line: str) -> list[str]:
    cells: list[str] = []
    cur: list[str] = []
    escaped = False
    for ch in line.strip():
        if escaped:
            cur.append(ch)
            escaped = False
        elif ch == "\\":
            cur.append(ch)
            escaped = True
        elif ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur).strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def existing_keys(path: Path) -> tuple[set[str], int]:
    keys: set[str] = set()
    max_row = 0
    if not path.exists():
        return keys, max_row
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = split_md_row(line)
        if len(cells) < 5 or not re.fullmatch(r"\d+", cells[0]):
            continue
        max_row = max(max_row, int(cells[0]))
        company = cells[2].replace(r"\|", "|").strip().lower()
        jd_url = cells[4].replace(r"\|", "|").strip()
        role = cells[3].replace(r"\|", "|").strip().lower()
        if jd_url:
            keys.add(f"url:{jd_url}")
        keys.add(f"company-url:{company}|{jd_url}")
        keys.add(f"company-role:{company}|{role}")
    return keys, max_row


def ensure_batch(path: Path, channel: str, date: str, backfilled: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    mode = "backfilled from tracker.csv" if backfilled else "emitted by daily-job-apply"
    path.write_text(
        f"# {channel} batch {date} ({mode} on {today_bjt()})\n\n"
        "| # | Status | Company | Role | JD_URL |\n"
        "|---|---|---|---|---|\n",
        encoding="utf-8",
    )


def append_batch_row(
    applications: Path,
    channel_raw: str,
    date: str,
    status: str,
    company: str,
    role: str,
    jd_url: str,
    *,
    backfilled: bool = False,
    dry_run: bool = False,
) -> tuple[str, Path]:
    channel = normalize_channel(channel_raw)
    if not date:
        date = today_bjt()
    path = applications / f"{channel}-batch-{date}.md"
    keys, max_row = existing_keys(path)
    company_key = company.strip().lower()
    role_key = role.strip().lower()
    candidates = {
        f"company-url:{company_key}|{jd_url.strip()}",
        f"company-role:{company_key}|{role_key}",
    }
    if jd_url.strip():
        candidates.add(f"url:{jd_url.strip()}")
    if keys & candidates:
        return "SKIP duplicate", path
    if dry_run:
        return "DRYRUN append", path
    ensure_batch(path, channel, date, backfilled)
    _, max_row = existing_keys(path)
    row_no = max_row + 1
    line = (
        f"| {row_no} | {md_cell(status)} | {md_cell(company)} | "
        f"{md_cell(role)} | {md_cell(jd_url)} |\n"
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return "WROTE", path


def is_submitted(row: dict[str, str]) -> bool:
    return status_from_tracker(row) == "Submitted"


def command_emit(args: argparse.Namespace) -> int:
    action, path = append_batch_row(
        args.applications,
        args.channel,
        args.date or today_bjt(),
        args.status,
        args.company,
        args.role,
        args.jd_url,
        backfilled=False,
        dry_run=args.dry_run,
    )
    print(f"{action} {path}")
    return 0


def command_backfill(args: argparse.Namespace) -> int:
    target_channels = {normalize_channel(c) for c in args.channels}
    buckets: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with args.tracker.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date = row_date(row)
            if args.date and date != args.date:
                continue
            channel = normalize_channel(row.get("Channel", ""))
            if target_channels and channel not in target_channels:
                continue
            status = status_from_tracker(row)
            if args.submitted_only and status != "Submitted":
                continue
            buckets[(channel, date)].append(
                {
                    "status": status,
                    "company": row.get("Company", "").strip(),
                    "role": row.get("Role", "").strip(),
                    "jd_url": row.get("JD_URL", "").strip(),
                }
            )
    total_written = 0
    total_skipped = 0
    for (channel, date), rows in sorted(buckets.items()):
        if not date:
            continue
        for row in rows:
            action, path = append_batch_row(
                args.applications,
                channel,
                date,
                row["status"],
                row["company"],
                row["role"],
                row["jd_url"],
                backfilled=True,
                dry_run=args.dry_run,
            )
            if action.startswith("WROTE") or action.startswith("DRYRUN"):
                total_written += 1
            elif action.startswith("SKIP"):
                total_skipped += 1
        print(f"{path}: processed={len(rows)}")
    print(f"summary written={total_written} skipped={total_skipped}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.set_defaults(func=None)
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit", help="Append one idempotent batch row.")
    emit.add_argument("--applications", type=Path, default=DEFAULT_APPLICATIONS)
    emit.add_argument("--channel", required=True)
    emit.add_argument("--date", default=today_bjt())
    emit.add_argument("--status", default="Submitted")
    emit.add_argument("--company", required=True)
    emit.add_argument("--role", required=True)
    emit.add_argument("--jd-url", required=True)
    emit.add_argument("--dry-run", action="store_true")
    emit.set_defaults(func=command_emit)

    backfill = sub.add_parser("backfill", help="Backfill batch rows from tracker.csv.")
    backfill.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER)
    backfill.add_argument("--applications", type=Path, default=DEFAULT_APPLICATIONS)
    backfill.add_argument("--date", help="YYYY-MM-DD; omit to scan all dates.")
    backfill.add_argument("--channels", nargs="+", default=["lever", "greenhouse"])
    backfill.add_argument("--submitted-only", action=argparse.BooleanOptionalAction, default=True)
    backfill.add_argument("--dry-run", action="store_true")
    backfill.set_defaults(func=command_backfill)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
