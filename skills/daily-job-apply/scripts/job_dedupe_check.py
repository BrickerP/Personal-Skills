#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
import signal
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ats_registry import domain_matches
from job_archive import DEFAULT_APPLICATIONS as ARCHIVE_DIR, split_md_row


TRACKER = Path.home() / "job-hunt" / "tracker.csv"
LEDGER = Path.home() / "job-hunt" / "application-ledger.md"
APPLIED_STATUSES = {"submitted", "duplicatesubmitted", "ack", "rejected"}
CANONICAL_BLOCKLIST = Path.home() / "job-hunt" / "data" / "blocked-companies.json"
SKILL_BLOCKLIST = Path(__file__).resolve().parent.parent / "data" / "blocked-companies.json"


def load_blocked_company_keys() -> set[str]:
    for path in (CANONICAL_BLOCKLIST, SKILL_BLOCKLIST):
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid blocklist object: {path}")
        keys = data.get("blocked_company_keys") or data.get("keys")
        if keys is not None and (
            not isinstance(keys, list)
            or any(not isinstance(key, str) or not company_key(key) for key in keys)
        ):
            raise ValueError(f"Invalid blocklist keys: {path}")
        if keys:
            return {company_key(key) for key in keys}
    raise FileNotFoundError(
        f"blocked-companies.json not found in {CANONICAL_BLOCKLIST} or {SKILL_BLOCKLIST}"
    )


def norm_url(value: str) -> str:
    """Compare requisitions, preserving identity-bearing query parameters; no network I/O."""
    value = (value or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if domain_matches(value, ["greenhouse.io"]):
        match = re.search(r"/jobs/(\d+)(?:/|$)", parts.path)
        job_id = match.group(1) if match else query.get("token", query.get("gh_jid", ""))
        if job_id.isdigit():
            return f"gh:{job_id}"
    for domain, prefix in (("ashbyhq.com", "ashby"), ("lever.co", "lever")):
        if domain_matches(value, [domain]):
            match = re.search(r"/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})(?:/|$)", parts.path, re.I)
            if match:
                return f"{prefix}:{match.group(1).lower()}"
    if parts.hostname == "news.ycombinator.com":
        match = re.fullmatch(r"/item/(\d+)/?", parts.path)
        job_id = match.group(1) if match else query.get("id", "")
        if job_id.isdigit():
            return f"hn:{job_id}"
    path = re.sub(r"/(?:application|confirmation|apply|thanks)$", "", parts.path.rstrip("/"), flags=re.I)
    query_pairs = sorted((key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                         if not key.lower().startswith("utm_") and key.lower() not in {"gh_src", "fbclid"})
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query_pairs), ""))


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def company_keys(company: str, url: str) -> set[str]:
    """Check both the supplied display name and the official ATS board slug."""
    keys = {company_key(company)}
    parts = urlsplit(url)
    if domain_matches(url, ["greenhouse.io"]):
        match = re.match(r"/([^/]+)/jobs/", parts.path)
        board = match.group(1) if match else dict(parse_qsl(parts.query)).get("for", "")
        keys.add(company_key(board))
    elif domain_matches(url, ["ashbyhq.com", "lever.co"]):
        keys.add(company_key(parts.path.strip("/").split("/")[0]))
    return keys - {""}


def match_text(match: dict) -> str:
    return json.dumps(match, ensure_ascii=False)


def archive_submitted_rows(directory: Path) -> list[dict]:
    """Applied rows of the Vault application batch files (`job_archive.py emit` writes them).

    Handles both layouts: `# | Status | Company | Role | JD_URL` and the older LinkedIn
    `# | Status | Company | Role | Job ID | Link | Notes`. Other statuses prove nothing about a
    submission, so they are ignored and the role stays retryable.
    """
    rows: list[dict] = []
    try:
        paths = sorted(p for p in directory.iterdir() if re.fullmatch(r".*-batch-.*\.md", p.name))
    except FileNotFoundError:
        return rows
    # iterdir surfaces directory read errors; glob may suppress OSError.
    for path in paths:
        date = re.search(r"\d{4}-\d{2}-\d{2}", path.name)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [cell.replace(r"\|", "|") for cell in split_md_row(line)]
            if len(cells) < 5 or not re.fullmatch(r"\d+", cells[0]):
                continue
            if cells[1].casefold() not in APPLIED_STATUSES:
                continue
            url = next((cell for cell in cells[4:6] if re.match(r"https?://", cell)), "")
            rows.append(
                {
                    "date": date.group(0) if date else "",
                    "status": cells[1],
                    "company": cells[2],
                    "role": cells[3],
                    "url": url,
                }
            )
    return rows


def is_retryable_non_submitted_duplicate(matches: list[dict]) -> bool:
    """Allow retry only when prior same-URL records prove no submission happened.

    An agent may revisit an incomplete form after a safe omission is resolved.
    An uncertain prior submit or human/account-risk blocker is not retryable.
    """
    if not matches:
        return False

    hard_stop = re.compile(
        r"\|\s*(Submitted|DuplicateSubmitted|Ack|Rejected)\s*\||"
        r'"submitted"\s*:\s*true|'
        r'"status"\s*:\s*"(Submitted|DuplicateSubmitted|Ack|Rejected)"|'
        r"submit-unverified|submit-failed|submission-unverified|outcome-unknown|"
        r"phone-required|phone-rejected|platform-anti-bot|captcha|hcaptcha|turnstile|"
        r"possible spam|verify your application|wrong-window|stale-job",
        re.I,
    )
    retryable = re.compile(
        r"script-gap:(resume-input-not-found|greenhouse-invalid-required-fields|greenhouse-fill-timeout|fill-failed-returncode-1)|"
        r"unsupported-required-question:unsupported-required:|"
        r"manual-finish-needed:unsupported-required:|"
        r"manual-finish-needed:(fill-failed|pre-submit-check-failed|invalid-required-fields|unhandled-required|greenhouse-fill-timeout)|form-not-loaded",
        re.I,
    )

    saw_retryable = False
    for match in matches:
        text = match_text(match)
        if match.get("submitted") is True:
            return False
        if match.get("status", "").casefold() in APPLIED_STATUSES:
            return False
        if hard_stop.search(text):
            return False
        if retryable.search(text):
            saw_retryable = True
        if match.get("source") == "tracker" and match.get("status") == "ManualFinish" and not match.get("submitted"):
            saw_retryable = True
        if match.get("source") == "ledger" and re.search(r"\|\s*ManualFinish\s*\|", match.get("line", "")):
            saw_retryable = True
    return saw_retryable


def check_application(args: argparse.Namespace) -> tuple[int, dict]:
    target_url = norm_url(args.url)
    target_keys = company_keys(args.company, args.url)
    target_role = norm_text(args.role)

    def verdict(ok: bool, code: str | None = None, **details) -> tuple[int, dict]:
        result = {"ok": ok, "company": args.company, "role": args.role, "url": args.url, **details}
        if code:
            result["code"] = code
        return (0 if ok else 20), result

    if target_keys & load_blocked_company_keys():
        return verdict(False, "company-blocked", reason="hard-blocked-after-overapplication")

    exact_matches = []
    company_matches = []
    counted = set()

    def add_record(record: dict) -> None:
        identity = norm_url(record.get("url", ""))
        if identity and identity == target_url:
            exact_matches.append(record)
        if not record.get("submitted") or not (target_keys & company_keys(record.get("company", ""), record.get("url", ""))):
            return
        application = identity or f"{company_key(record.get('company', ''))}|{norm_text(record.get('role', ''))}"
        if application not in counted:
            counted.add(application)
            company_matches.append({**record, "same_role": norm_text(record.get("role", "")) == target_role})

    def known_stop() -> tuple[int, dict] | None:
        # A proven denial needs no slower evidence source. Never short-circuit an allow.
        if exact_matches and not is_retryable_non_submitted_duplicate(exact_matches):
            return verdict(False, "duplicate-url", matches=exact_matches)
        if len(counted) >= args.company_cap:
            return verdict(False, "company-cap-reached", submitted_count=len(counted),
                           company_cap=args.company_cap, matches=company_matches[:10])
        return None

    try:
        tracker_handle = TRACKER.open(newline="", encoding="utf-8")
    except FileNotFoundError:
        tracker_handle = None
    if tracker_handle is not None:
        with tracker_handle as handle:
            reader = csv.DictReader(handle)
            if not {"Company", "Role", "JD_URL", "Application_Submitted", "Response_Status"} <= set(reader.fieldnames or []):
                raise ValueError("Tracker is missing required columns")
            for row in reader:
                status = row.get("Response_Status", "") or ""
                add_record({
                    "source": "tracker", "date": row.get("Date", ""),
                    "company": row.get("Company", "") or "", "role": row.get("Role", "") or "",
                    "status": status,
                    "submitted": row.get("Application_Submitted") == "Yes" or status.casefold() in APPLIED_STATUSES,
                    "url": row.get("JD_URL", "") or "", "notes": row.get("Notes", "") or "",
                })
        if stop := known_stop():
            return stop

    try:
        ledger_text = LEDGER.read_text(encoding="utf-8")
    except FileNotFoundError:
        ledger_text = ""
    if ledger_text:
        for line in ledger_text.splitlines():
            cells = split_md_row(line)
            if len(cells) < 4 or not re.match(r"https?://", cells[3]):
                continue
            company, _, role = cells[2].partition(" - ")
            add_record({
                "source": "ledger", "line": line, "status": cells[1],
                "submitted": cells[1].casefold() in APPLIED_STATUSES,
                "company": company, "role": role, "url": cells[3],
            })
        if stop := known_stop():
            return stop

    # Count each submitted requisition only once across all evidence sources.
    for row in archive_submitted_rows(ARCHIVE_DIR):
        add_record({"source": "archive", "submitted": True, **row})
    if stop := known_stop():
        return stop

    same_role_matches = [match for match in company_matches if match.get("same_role")]
    if same_role_matches:
        return verdict(False, "duplicate-role", matches=same_role_matches)
    if exact_matches:
        return verdict(True, "retryable-non-submitted-duplicate", matches=exact_matches)
    return verdict(True, same_company_submitted_matches=company_matches[:10])


def main() -> int:
    parser = argparse.ArgumentParser(description="Prevent duplicate job applications (macOS/Linux).")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--company-cap", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10, help="Local evidence-read deadline in seconds (default: 10)")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and greater than zero")
    if not 1 <= args.company_cap <= 20:
        parser.error("--company-cap must be between 1 and 20")

    def deadline_expired(signum, frame):
        raise TimeoutError("Local evidence read exceeded the deadline; stop application work")

    previous_handler = signal.signal(signal.SIGALRM, deadline_expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, args.timeout)
        parsed = urlsplit(args.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not company_key(args.company) or not args.role.strip():
            raise ValueError("A company, role and absolute HTTP(S) job URL are required")
        code, result = check_application(args)
    except (OSError, ValueError, csv.Error) as exc:
        code = 21
        result = {"ok": False, "code": "dedupe-check-timeout" if isinstance(exc, TimeoutError) else "dedupe-check-error",
                  "reason": str(exc), "company": args.company, "role": args.role, "url": args.url}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
