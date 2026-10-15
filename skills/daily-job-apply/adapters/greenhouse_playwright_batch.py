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
import collections
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_SCRIPTS = SCRIPTS_DIR

from ats_evolution_log import evolve_from_attempt  # noqa: E402


TRACKER = TRACKER_CSV
CANDIDATE_DIR = WORK_DIR / "candidate-pools"
DEFAULT_CSV = CANDIDATE_DIR / "greenhouse-classified-2026-06-03-wide2.csv"
APPLY = ADAPTERS_DIR / "greenhouse_playwright_apply.cjs"
LOG_DIR = ADAPTERS_DIR / 'logs'
NODE_PATH = str(ADAPTERS_DIR / "node_modules")
DEDUPE_SCRIPT = Path.home() / ".codex" / "skills" / "daily-job-apply" / "scripts" / "job_dedupe_check.py"

TITLE_ALLOW = re.compile(
    r"\b(software engineer|backend|back end|platform|infrastructure|infra|"
    r"site reliability|sre|devops|full[- ]?stack|machine learning|ml engineer|"
    r"ai engineer|distributed systems|cloud engineer|developer productivity|"
    r"data platform|data engineer|retrieval|systems engineer|security engineer)\b",
    re.I,
)
TITLE_BLOCK = re.compile(
    r"\b(admin|administrative|counsel|legal|solutions architect|solutions engineer|"
    r"sales engineer|manager|director|vice president|vp|head|product manager|data scientist|"
    r"designer|researcher|user research|ux research|recruiter|ios|android|hardware|manufacturing|embedded|gnc|intern|internship|phd early career|"
    r"procurement|officer)\b",
    re.I,
)
GREENHOUSE_JOB_URL_RE = re.compile(
    r"https?://(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)/jobs/([^/?#]+)",
    re.I,
)
LOCATION_ALLOW = re.compile(
    r"(\bremote\b|remote \(u\.s\.\)|remote - usa|remote,? us|remote,? united states|"
    r"united states|\busa\b|san francisco|bay area|california|new york|seattle|"
    r"austin|boston|washington|mountain view|los angeles|san mateo|costa mesa|"
    r"waltham|chicago|bellevue|st\. louis)",
    re.I,
)
LOCATION_BLOCK = re.compile(
    r"(remote - canada|canada|india|bangalore|emea|apac|united kingdom|\buk\b|"
    r"london|israel|singapore|japan|australia|ireland|netherlands|korea|"
    r"busan|switzerland|lausanne|germany|france|spain|poland|brazil|mexico|latam)",
    re.I,
)
BLOCKED_COMPANY_KEYS = {
    "speechify",
    "hightouch",
    "jobgether",
    "anthropic",
    "togetherai",
    "scaleai",
    "okta",
    "samsara",
    "pinterest",
    "verkada",
}


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value).rstrip("/")
    value = re.sub(r"/(?:application|confirmation|apply|thanks)$", "", value)
    return value.replace("https://boards.greenhouse.io/", "https://job-boards.greenhouse.io/").lower()


def company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def blocked_company(value: str) -> bool:
    return company_key(value) in BLOCKED_COMPANY_KEYS


def is_retryable_duplicate(row: dict, company_cap: int) -> bool:
    company = row.get("company") or ""
    role = row.get("role") or ""
    url = row.get("url") or ""
    if not company or not role or not url:
        return False
    proc = subprocess.run(
        [
            "python3",
            str(DEDUPE_SCRIPT),
            "--company",
            company,
            "--role",
            role,
            "--url",
            url,
            "--company-cap",
            str(company_cap),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode != 20:
        return False
    try:
        payload = json.loads(proc.stdout or "{}")
    except Exception:
        return False
    return payload.get("code") == "retryable-non-submitted-duplicate"


def first_value(row: dict, *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def parse_greenhouse_url(value: str) -> tuple[str, str]:
    match = GREENHOUSE_JOB_URL_RE.match(norm_url(value))
    if match:
        return match.group(1), match.group(2)
    resolver = Path.home() / ".codex" / "skills" / "daily-job-apply" / "scripts" / "greenhouse_url_resolver.py"
    if resolver.exists():
        proc = subprocess.run(
            ["python3", str(resolver), "--url", value],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            try:
                payload = json.loads(proc.stdout or "{}")
                if payload.get("ok"):
                    return payload.get("board", ""), payload.get("job_id", "")
            except json.JSONDecodeError:
                pass
    return "", ""


def is_greenhouse_url(value: str) -> bool:
    normalized = norm_url(value)
    return "job-boards.greenhouse.io/" in normalized or "boards.greenhouse.io/" in normalized


def normalize_greenhouse_row(row: dict) -> dict:
    normalized = dict(row)
    company = first_value(row, "company", "Company", "company_name")
    role = first_value(row, "role", "Role", "title")
    url = first_value(row, "url", "JD_URL", "jd_url", "Job_URL")
    board = first_value(row, "board", "Board", "board_id", "slug")
    job_id = first_value(row, "id", "job_id", "jobId", "posting_id")
    location = first_value(row, "location", "Location")
    ats = first_value(row, "ats", "ATS", "Ats")

    if (not board or not job_id) and url:
        parsed_board, parsed_job_id = parse_greenhouse_url(url)
        if not board:
            board = parsed_board
        if not job_id:
            job_id = parsed_job_id
    if not url and board and job_id:
        url = f"https://job-boards.greenhouse.io/{board}/jobs/{job_id}"

    normalized["company"] = company
    normalized["role"] = role
    normalized["url"] = url
    normalized["board"] = board
    normalized["id"] = job_id
    normalized["location"] = location
    normalized["ats"] = ats
    return normalized


def tracker_rows() -> list[dict]:
    if not TRACKER.exists():
        return []
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def row_date(row: dict) -> str:
    return (row.get("Date") or "").split()[0]


def submitted_count(rows: list[dict], *, count_date: str | None = None, since_date: str | None = None) -> int:
    count = 0
    for row in rows:
        if row.get("Application_Submitted") != "Yes":
            continue
        date = row_date(row)
        if since_date:
            if date >= since_date:
                count += 1
            continue
        if count_date:
            if date == count_date:
                count += 1
            continue
        count += 1
    return count


def count_scope(args: argparse.Namespace) -> dict:
    if args.since_date:
        return {"submitted_since": args.since_date}
    return {"submitted_date": args.count_date}


def resume_variant(company: str, role: str, url: str) -> str:
    text = f"{company} {role} {url}"
    if re.search(r"\b(ai|llm|genai|agent|machine learning|ml|inference|model|research)\b", text, re.I):
        return "AI Agent Infra"
    if re.search(r"\b(backend|back-end|platform|infra|infrastructure|devops|sre|reliability|data|distributed|cloud|golang|java|security)\b", text, re.I):
        return "Backend Platform"
    return "General SWE"


def should_ignore_risk_filters() -> bool:
    return os.getenv("GREENHOUSE_IGNORE_RISK", "").strip().lower() in {"1", "true", "yes", "on"}


def risky_tracker_scope(rows: list[dict]) -> tuple[set[str], set[str]]:
    risky_urls: set[str] = set()
    risky_companies: set[str] = set()
    hard_risk_re = re.compile(
        r"platform-anti-bot|danger|captcha|hcaptcha|possible spam|verify your application|"
        r"security verification|sms verification|stale-job",
        re.I,
    )
    soft_risk_re = re.compile(
        r"phone-required-no-active-number|"
        r"authentic-human-answer-or-challenge|unsupported-required|invalid-or-unhandled-required|"
        r"submit-unverified",
        re.I,
    )
    for row in rows:
        text = " ".join([
            row.get("Response_Status", ""),
            row.get("Stage", ""),
            row.get("Notes", ""),
        ])
        hard = hard_risk_re.search(text)
        soft = soft_risk_re.search(text)
        if not hard and not soft:
            continue
        url = norm_url(row.get("JD_URL", ""))
        if url:
            risky_urls.add(url)
            company = company_key(row.get("Company") or "")
            if company and hard:
                risky_companies.add(company)
    return risky_urls, risky_companies


def risky_log_scope() -> tuple[set[str], set[str]]:
    risky_urls: set[str] = set()
    risky_companies: set[str] = set()
    risk_codes = {"platform-anti-bot", "danger-text"}
    nonprogress_by_url: collections.Counter[str] = collections.Counter()
    nav_errors_by_company: collections.Counter[str] = collections.Counter()
    for path in sorted(LOG_DIR.glob("greenhouse-playwright-batch-*.jsonl"))[-20:]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event = payload.get("event") or {}
            nested = payload.get("payload") or {}
            code = event.get("result_code") or nested.get("code")
            url = norm_url(event.get("url") or nested.get("url") or "")
            company = company_key(event.get("company") or nested.get("company") or "")
            if url and code in {"submit-unverified", "invalid-or-unhandled-required"}:
                nonprogress_by_url[url] += 1
            stderr_tail = event.get("stderr_tail") or ""
            if company and event.get("status") == "RunnerError" and re.search(r"page\.goto|net::ERR_", stderr_tail, re.I):
                nav_errors_by_company[company] += 1
            if code not in risk_codes:
                continue
            if url:
                risky_urls.add(url)
            if company:
                risky_companies.add(company)
    risky_urls |= {url for url, count in nonprogress_by_url.items() if count >= 2}
    risky_companies |= {company for company, count in nav_errors_by_company.items() if count >= 2}
    return risky_urls, risky_companies


def candidate_ok(
    row: dict,
    known_submitted: set[str],
    risky_urls: set[str],
    risky_companies: set[str],
    submitted_by_company: collections.Counter[str],
    company_cap: int,
) -> bool:
    row = normalize_greenhouse_row(row)
    ats = (row.get("ats") or "").strip().lower()
    url = row.get("url") or ""
    if ats and ats != "greenhouse":
        return False
    if not ats and url and not is_greenhouse_url(url):
        if not row.get("board") or not row.get("id"):
            return False
    company = company_key(row.get("company") or "")
    board = company_key(row.get("board") or "")
    if not board or not row.get("id"):
        return False
    if blocked_company(company) or blocked_company(board):
        return False
    if company_cap > 0 and company and submitted_by_company[company] >= company_cap:
        return False
    url = norm_url(row.get("url", ""))
    canonical = ""
    if row.get("board") and row.get("id"):
        canonical = norm_url(f"https://job-boards.greenhouse.io/{row.get('board')}/jobs/{row.get('id')}")
    if not url or url in known_submitted or (canonical and canonical in known_submitted):
        return False
    if not is_retryable_duplicate(row, company_cap):
        return False
    if not should_ignore_risk_filters():
        if company in risky_companies:
            return False
        if url in risky_urls or (canonical and canonical in risky_urls):
            return False
    blockers = row.get("blockers", "")
    if any(blocker in blockers for blocker in [
        "phone-required-no-active-number",
        "cover-letter-required",
        "authentic-human-answer-or-challenge",
        "unknown-required",
        "current-employer-title-required",
        "many-required-react-select-mirrors",
        "react-required-mirrors",
        "voluntary-self-id-required-react-selects",
        "manual-resume-text-required",
        "questions-unavailable",
    ]):
        return False
    title = row.get("role", "")
    if not TITLE_ALLOW.search(title) or TITLE_BLOCK.search(title):
        return False
    location = row.get("location", "")
    if LOCATION_BLOCK.search(location) and not re.search(r"remote,? us|remote,? united states|united states|\busa\b|u\.s\.", location, re.I):
        return False
    if not LOCATION_ALLOW.search(location):
        return False
    return True


def load_queue(path: Path, limit: int, company_cap: int) -> list[dict]:
    rows = tracker_rows()
    # Track only submitted jobs as hard exclusions here.
    # Previously all touched rows were excluded, which blocked retries where
    # the shared dedupe step later in the apply path could still allow
    # legitimate reprocessing of non-submitted attempts.
    known_submitted = {
        norm_url(r.get("JD_URL", ""))
        for r in rows
        if r.get("JD_URL") and r.get("Application_Submitted") == "Yes"
    }
    submitted_by_company = collections.Counter(
        company_key(r.get("Company") or "")
        for r in rows
        if r.get("Application_Submitted") == "Yes" and (r.get("Company") or "").strip()
    )
    risky_urls, risky_companies = risky_tracker_scope(rows)
    log_risky_urls, log_risky_companies = risky_log_scope()
    risky_urls |= log_risky_urls
    risky_companies |= log_risky_companies
    with path.open(newline="", encoding="utf-8") as handle:
        raw = [normalize_greenhouse_row(row) for row in csv.DictReader(handle)]
    queue = [row for row in raw if candidate_ok(row, known_submitted, risky_urls, risky_companies, submitted_by_company, company_cap)]

    def score(row: dict) -> tuple[int, str, str]:
        text = f"{row.get('company','')} {row.get('role','')}"
        priority = 0
        blockers = row.get("blockers", "")
        if blockers:
            priority += 100
        if "questions-unavailable" in blockers:
            priority += 50
        if "required-selects" in blockers:
            priority += 20
        if re.search(r"\b(agent|ai|ml|machine learning|inference|llm|platform|infra|backend|security)\b", text, re.I):
            priority -= 10
        if row.get("company") in {"Anthropic", "Scale AI", "Postman", "Reddit", "Discord", "Okta", "Samsara"}:
            priority -= 2
        return (priority, row.get("company", ""), row.get("role", ""))

    queue.sort(key=score)
    return queue[:limit] if limit else queue


def run_apply(
    row: dict,
    *,
    allow_manual_retry: bool,
    company_cap: int,
    system_chrome: bool = False,
    job_timeout: int = 360,
) -> tuple[int, dict, str]:
    row = normalize_greenhouse_row(row)
    company = row.get("company") or ""
    role = row.get("role") or ""
    url = row.get("url") or ""
    board = row.get("board") or ""
    job_id = row.get("id") or ""
    if not company:
        return 1, {"ok": False, "status": "Skipped", "code": "invalid-row-fields", "field": "company", "row": row}, ""
    if not role:
        return 1, {"ok": False, "status": "Skipped", "code": "invalid-row-fields", "field": "role", "row": row}, ""
    if not board:
        return 1, {"ok": False, "status": "Skipped", "code": "invalid-row-fields", "field": "board", "row": row}, ""
    if not job_id:
        return 1, {"ok": False, "status": "Skipped", "code": "invalid-row-fields", "field": "job-id", "row": row}, ""
    variant = row.get("variant") or resume_variant(company, role, url)
    location = row.get("location") or ""
    cmd = [
        "node",
        str(APPLY),
        "--company",
        company,
        "--role",
        role,
        "--board",
        board,
        "--job-id",
        job_id,
        "--url",
        url,
        "--variant",
        variant,
        "--location",
        location,
        "--company-cap",
        str(company_cap),
        "--submit",
    ]
    if system_chrome:
        cmd.append("--system-chrome")
    if allow_manual_retry:
        cmd.append("--allow-manual-retry")
    env = os.environ.copy()
    env["NODE_PATH"] = NODE_PATH
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=job_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stderr_text = ""
        if exc.stderr:
            stderr_text = exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode("utf-8", "replace")
        payload = {
            "ok": False,
            "status": "RunnerError",
            "code": "apply-timeout",
            "timeout_seconds": job_timeout,
            "company": company,
            "role": role,
            "url": url,
        }
        return 1, payload, stderr_text[-4000:]
    payload: dict
    try:
        payload = json.loads(proc.stdout[proc.stdout.find("{") : proc.stdout.rfind("}") + 1])
    except Exception:
        payload = {"ok": False, "status": "RunnerError", "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    return proc.returncode, payload, proc.stderr


def parse_fields_missing(payload: dict, stderr: str) -> list[str]:
    text = json.dumps(payload, ensure_ascii=False) + stderr
    fields: list[str] = []
    for label in ("Phone Number", "Location", "Are you authorized", "city", "state"):
        if label.lower() in text.lower():
            fields.append(label)
    return fields


def record_failure(row: dict, payload: dict, stderr: str, *, submitted_after: int, submitted_before: int) -> None:
    if submitted_after > submitted_before:
        return
    status = payload.get("status") or "Blocked"
    if status in ("Submitted", "submitted"):
        return
    code = payload.get("code") or ""
    if code in ("skip-email-verification", "needsSecurityCode"):
        return
    evolve_from_attempt(
        platform="greenhouse",
        url=row.get("url", ""),
        status=str(status),
        blocker=str(code) if code else None,
        dom_snippet=(stderr or json.dumps(payload, ensure_ascii=False))[-800:],
        fields_missing=parse_fields_missing(payload, stderr),
        company=row.get("company", ""),
        role=row.get("role", ""),
        channel="greenhouse-batch",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--target-today", type=int, default=200)
    parser.add_argument("--target-submitted", type=int)
    parser.add_argument("--count-date", default=dt.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--since-date")
    parser.add_argument("--max-attempts", type=int, default=80)
    parser.add_argument("--min-success-gap", type=int, default=180)
    parser.add_argument("--company-cap", type=int, default=20)
    parser.add_argument("--allow-manual-retry", action="store_true")
    parser.add_argument("--headless", action="store_true", help="Use Playwright headless instead of system Chrome CDP")
    parser.add_argument(
        "--job-timeout",
        type=int,
        default=360,
        help="Per-job subprocess timeout in seconds; timeouts are recorded and the batch continues",
    )
    args = parser.parse_args()
    target = args.target_submitted if args.target_submitted is not None else args.target_today

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"greenhouse-playwright-batch-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    queue = load_queue(args.csv, args.max_attempts, args.company_cap)
    scope = count_scope(args)
    initial_count = submitted_count(tracker_rows(), count_date=args.count_date, since_date=args.since_date)
    print(json.dumps({"stage": "queue", "count": len(queue), "log": str(log_path), **scope, "submitted_count": initial_count, "target_submitted": target}, ensure_ascii=False), flush=True)

    last_success = 0.0
    attempted = 0
    success = 0
    for row in queue:
        current = submitted_count(tracker_rows(), count_date=args.count_date, since_date=args.since_date)
        if current >= target:
            break
        if last_success:
            remaining = args.min_success_gap - (time.time() - last_success)
            if remaining > 0:
                print(json.dumps({"stage": "cooldown", "seconds": int(remaining), **scope, "submitted_count": current}, ensure_ascii=False), flush=True)
                time.sleep(remaining)
        attempted += 1
        event = {
            "ts": now(),
            "stage": "attempt",
            "attempted": attempted,
            **scope,
            "submitted_count_before": current,
            "company": row.get("company"),
            "role": row.get("role"),
            "url": row.get("url"),
        }
        print(json.dumps(event, ensure_ascii=False), flush=True)
        code, payload, stderr = run_apply(
            row,
            allow_manual_retry=args.allow_manual_retry,
            company_cap=args.company_cap,
            system_chrome=False,
            job_timeout=args.job_timeout,
        )
        after = submitted_count(tracker_rows(), count_date=args.count_date, since_date=args.since_date)
        result = {
            **event,
            "stage": "result",
            "returncode": code,
            "status": payload.get("status"),
            "ok": payload.get("ok"),
            "result_code": payload.get("code"),
            "submitted_count_after": after,
            "stderr_tail": stderr[-1200:],
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": result, "payload": payload}, ensure_ascii=False) + "\n")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        record_failure(row, payload, stderr, submitted_after=after, submitted_before=current)
        if after > current:
            success += after - current
            last_success = time.time()
        if payload.get("code") in {"platform-anti-bot", "danger-text"}:
            print(json.dumps({"stage": "stop", "reason": payload.get("code")}, ensure_ascii=False), flush=True)
            return 11
    final_count = submitted_count(tracker_rows(), count_date=args.count_date, since_date=args.since_date)
    print(json.dumps({"stage": "done", "attempted": attempted, "success": success, **scope, "submitted_count": final_count, "target_submitted": target, "log": str(log_path)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
