#!/usr/bin/env python3
"""Build a safer non-LinkedIn Greenhouse application queue.

The output separates roles that are likely auto-fillable from roles that need
human judgement. It intentionally uses curl with per-request timeouts because
some Greenhouse TLS connections can hang in Python's urllib on this machine.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Downloads" / ".omx"))
from greenhouse_embed_skip import is_embed_career_site_url


TRACKER = Path.home() / "job-hunt" / "tracker.csv"
OUT_DIR = Path.home() / "job-hunt" / "candidate-pools"
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
    "coder",
    "decagon",
    "entefy",
    "aifund",
}
BLOCKED_COMPANY_KEYS.update({
    "abnormal",
    "affirm",
    "airops",
    "amplitude",
    "anduril",
    "andurilindustries",
    "attadale",
    "axon",
    "backflip",
    "bjak",
    "brightplan",
    "browserbase",
    "canonical",
    "checkr",
    "chipply",
    "clickhouse",
    "cribl",
    "crossinghurdles",
    "databricks",
    "dataiku",
    "defenseunicorns",
    "doxel",
    "elastic",
    "enterpriseknowledge",
    "fal",
    "fin",
    "gitlab",
    "hanwhaenergyusa",
    "highnote",
    "honeycomb",
    "insightglobal",
    "intercom",
    "invicti",
    "jobrightai",
    "justworks",
    "kiewit",
    "kraftkennedy",
    "largetongroup",
    "launchdarkly",
    "livekit",
    "micro1",
    "mindex",
    "millennium",
    "modal",
    "motionrecruitment",
    "nubank",
    "nuro",
    "olo",
    "openly",
    "pacer",
    "pacergroup",
    "princetonit",
    "quantumworldtechnologies",
    "railway",
    "revstar",
    "robert_half",
    "roberthalf",
    "robinhood",
    "roblox",
    "saragossa",
    "tailscale",
    "technogen",
    "thejudgegroup",
    "tiktok",
    "toast",
    "twilio",
    "ventureup",
    "zscaler",
    "zuora",
    "zum",
})

DEFAULT_BOARDS = """
airtable affirm andurilindustries anthropic anyscale assemblyai asana brex
calendly cartesia cerebras cloudflare cohere databricks datadog deepgram
discord elastic elevenlabs fireworksai figma gitlab gleanwork groq gusto
harvey huggingface instacart langchain mercury mixpanel mongodb notion okta
perplexityai pinecone plaid reddit render replicate retool rippling samsara
sentry snowflake sourcegraph stripe supabase temporal vercel warp writer
""".split()

TITLE_ALLOW = re.compile(
    r"\b(software engineer|backend|back end|platform|infrastructure|infra|"
    r"site reliability|sre|devops|full[- ]?stack|machine learning|"
    r"ml engineer|ai engineer|distributed systems|cloud engineer|"
    r"developer productivity|data platform|data engineer|retrieval)\b",
    re.I,
)
TITLE_BLOCK = re.compile(
    r"\b(manager|director|vp|head|product manager|designer|researcher|"
    r"user research|ux research|solutions engineer|sales engineer|customer|support|recruiter|account|marketing|program manager|"
    r"intern|internship|apprentice|android|ios|robotics|hardware)\b",
    re.I,
)
LOCATION_ALLOW = re.compile(
    r"(remote|usa|united states|san francisco|new york|california|bay area|"
    r"seattle|boston|austin|americas)",
    re.I,
)
LOCATION_BLOCK = re.compile(
    r"(canada|india|bangalore|emea|apac|united kingdom|\buk\b|london|"
    r"israel|singapore|japan|australia|ireland|netherlands|germany|"
    r"france|spain|poland|brazil|mexico|latam)",
    re.I,
)
PHONE_RE = re.compile(r"\bphone\b", re.I)
COVER_RE = re.compile(r"\bcover letter\b", re.I)
ANTI_AI_RE = re.compile(
    r"no ai-generated|ai-generated answers|if you.?re an ai tool|"
    r"activation function|application challenge|security code|shared block|"
    r"captcha|hcaptcha",
    re.I,
)
LOCATION_QUESTION_RE = re.compile(
    r"current country|country of residence|country in which|located|"
    r"based in|work.*office|in person|hybrid",
    re.I,
)
AUTH_QUESTION_RE = re.compile(r"sponsor|authorization|legally authorized|visa", re.I)
AGREEMENT_RE = re.compile(r"employment agreement|non-compete|post-employment", re.I)
CURRENT_EMPLOYER_REQUIRED_RE = re.compile(
    r"current (?:or most recent |or more recent |)?employer|"
    r"most recent employer|recent employer|current company|"
    r"current (?:or most recent |or more recent |)?job title|"
    r"most recent job title|recent job title",
    re.I,
)


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value)
    value = value.rstrip("/")
    value = re.sub(r"/apply$", "", value)
    return value.lower()


def load_known_urls() -> set[str]:
    known: set[str] = set()
    if not TRACKER.exists():
        return known
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("JD_URL"):
                known.add(norm_url(row["JD_URL"]))
    return known


def company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def blocked_company(value: str) -> bool:
    return company_key(value) in BLOCKED_COMPANY_KEYS


def load_company_submitted_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    if not TRACKER.exists():
        return counts
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = company_key(row.get("Company", ""))
            if not key or row.get("Application_Submitted") != "Yes":
                continue
            counts[key] = counts.get(key, 0) + 1
    return counts


def curl_json(url: str, max_time: int = 8) -> dict | None:
    try:
        proc = subprocess.run(
            ["curl", "-L", "--max-time", str(max_time), "-s", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max_time + 3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0 or not proc.stdout.lstrip().startswith("{"):
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def curl_text(url: str, max_time: int = 8) -> str:
    try:
        proc = subprocess.run(
            ["curl", "-L", "--max-time", str(max_time), "-s", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max_time + 3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout


def board_jobs(board: str, known_urls: set[str], max_jobs_per_board: int) -> list[dict]:
    if blocked_company(board):
        return []
    data = curl_json(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=false"
    )
    if not data:
        return []
    rows: list[dict] = []
    for job in data.get("jobs", []):
        title = (job.get("title") or "").strip()
        location = ((job.get("location") or {}).get("name") or "").strip()
        url = (job.get("absolute_url") or "").strip().rstrip("/")
        company = (job.get("company_name") or board).strip()
        if is_embed_career_site_url(url):
            continue
        if blocked_company(company):
            continue
        if not url or norm_url(url) in known_urls:
            continue
        if not TITLE_ALLOW.search(title):
            continue
        if TITLE_BLOCK.search(title):
            continue
        if LOCATION_BLOCK.search(location):
            continue
        if not LOCATION_ALLOW.search(location):
            continue
        rows.append(
            {
                "board": board,
                "id": str(job.get("id") or ""),
                "company": company,
                "role": title,
                "location": location,
                "url": url,
            }
        )
        if max_jobs_per_board and len(rows) >= max_jobs_per_board:
            break
    return rows


def classify_questions(job: dict) -> dict:
    detail = curl_json(
        f"https://boards-api.greenhouse.io/v1/boards/{job['board']}/jobs/{job['id']}?questions=true"
    )
    if not detail:
        job["status"] = "source_error"
        job["blockers"] = "questions-unavailable"
        job["question_labels"] = ""
        return job

    questions = detail.get("questions", [])
    labels: list[str] = []
    blockers: list[str] = []
    cautions: list[str] = []
    required_selects = 0
    for question in questions:
        label = re.sub(r"\s+", " ", (question.get("label") or "").strip())
        required = bool(question.get("required"))
        if not label:
            continue
        labels.append(label + ("*" if required else ""))
        fields = question.get("fields") or []
        if required and any("select" in (field.get("type") or "") for field in fields):
            required_selects += 1
        if required and PHONE_RE.search(label):
            blockers.append("phone-required-no-active-number")
        if required and COVER_RE.search(label):
            blockers.append("cover-letter-required")
        if required and CURRENT_EMPLOYER_REQUIRED_RE.search(label):
            blockers.append("current-employer-title-required")
        if ANTI_AI_RE.search(label):
            blockers.append("authentic-human-answer-or-challenge")
        if required and LOCATION_QUESTION_RE.search(label):
            cautions.append("location-question")
        if required and AUTH_QUESTION_RE.search(label):
            cautions.append("authorization-question")
        if required and AGREEMENT_RE.search(label):
            cautions.append("employment-agreement-question")

    page_html = curl_text(job["url"])
    required_input_count = page_html.count("remix-css-1a0ro4n-requiredInput")
    has_voluntary_self_id = "Voluntary Self Identification" in page_html
    if required_selects:
        blockers.append(f"required-react-selects:{required_selects}")
    if has_voluntary_self_id and required_input_count >= 4:
        blockers.append("voluntary-self-id-required-react-selects")
    elif required_input_count > 4:
        blockers.append(f"many-required-react-select-mirrors:{required_input_count}")

    job["question_labels"] = " || ".join(labels)[:1600]
    job["blockers"] = ",".join(dict.fromkeys(blockers))
    job["cautions"] = ",".join(dict.fromkeys(cautions))
    job["status"] = "manual" if blockers else "auto_candidate"
    return job


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="")
    parser.add_argument("--boards", nargs="*", default=DEFAULT_BOARDS)
    parser.add_argument("--max-workers", type=int, default=10)
    parser.add_argument("--max-jobs-per-board", type=int, default=12)
    parser.add_argument("--limit-raw", type=int, default=180)
    parser.add_argument("--company-cap", type=int, default=20)
    args = parser.parse_args()

    known = load_known_urls()
    company_counts = load_company_submitted_counts()
    boards = [
        board for board in dict.fromkeys(board.strip().lower() for board in args.boards if board.strip())
        if not blocked_company(board)
    ]
    raw: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = [
            pool.submit(board_jobs, board, known, args.max_jobs_per_board)
            for board in boards
        ]
        for future in as_completed(futures):
            raw.extend(future.result())
    raw = sorted(raw, key=lambda row: (row["board"], row["company"], row["role"]))
    if args.company_cap > 0:
        raw = [
            row for row in raw
            if not blocked_company(row.get("company", ""))
            and company_counts.get(company_key(row.get("company", "")), 0) < args.company_cap
        ]
    if args.limit_raw:
        raw = raw[: args.limit_raw]

    detailed: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(4, args.max_workers // 2)) as pool:
        futures = [pool.submit(classify_questions, job) for job in raw]
        for future in as_completed(futures):
            detailed.append(future.result())

    detailed.sort(key=lambda row: (row["status"], row["company"], row["role"]))
    date = args.date or subprocess.check_output(
        ["bash", "-lc", "TZ=Asia/Shanghai date +%Y-%m-%d"], text=True
    ).strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"greenhouse-classified-{date}.csv"
    fields = [
        "status",
        "company",
        "role",
        "location",
        "url",
        "board",
        "id",
        "blockers",
        "cautions",
        "question_labels",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in detailed)

    counts: dict[str, int] = {}
    for row in detailed:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(json.dumps({"out": str(out_path), "raw": len(raw), "counts": counts}, indent=2))
    for row in detailed[:40]:
        print(
            f"{row['status']}: {row['company']} | {row['role']} | "
            f"{row['location']} | {row.get('blockers','')} | {row['url']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
