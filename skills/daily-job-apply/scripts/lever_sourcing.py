#!/usr/bin/env python3
"""Build a non-LinkedIn Lever official application queue."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


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

DEFAULT_COMPANIES = """
anthropic applydigital calendly canonical checkr circleci cloudflare cohere
coinbase crusoe cursor databricks docker elastic figma flexport grammarly
hashicorp hex hightouch lattice linear modal notion nuro plaid postman ramp
replit rippling runway scaleai segment sentry sourcegraph stackblitz stripe
temporal vercel zapier
""".split()

TITLE_ALLOW = re.compile(
    r"\b(software engineer|backend|back end|platform|infrastructure|infra|"
    r"site reliability|sre|devops|full[- ]?stack|machine learning|"
    r"ml engineer|ai engineer|distributed systems|cloud engineer|"
    r"developer productivity|data platform|data engineer|retrieval)\b",
    re.I,
)
TITLE_BLOCK = re.compile(
    r"\b(manager|director|vp|head|product manager|designer|solutions engineer|"
    r"sales engineer|customer|support|recruiter|account|marketing|program manager|"
    r"intern|apprentice|android|ios|hardware|robotics)\b",
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


def curl_json(url: str, max_time: int = 8) -> list[dict] | None:
    try:
        proc = subprocess.run(
            ["curl", "-L", "--max-time", str(max_time), "-s", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=max_time + 3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0 or not proc.stdout.lstrip().startswith("["):
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def company_jobs(company: str, known_urls: set[str], max_jobs_per_company: int) -> list[dict]:
    if blocked_company(company):
        return []
    data = curl_json(f"https://api.lever.co/v0/postings/{company}?mode=json")
    if data is None:
        return []
    rows: list[dict] = []
    for job in data:
        title = (job.get("text") or "").strip()
        categories = job.get("categories") or {}
        location = (categories.get("location") or "").strip()
        team = (categories.get("team") or "").strip()
        url = (job.get("hostedUrl") or job.get("applyUrl") or "").strip()
        if not url or norm_url(url) in known_urls:
            continue
        if not TITLE_ALLOW.search(title):
            continue
        if TITLE_BLOCK.search(title):
            continue
        if location and LOCATION_BLOCK.search(location):
            continue
        if location and not LOCATION_ALLOW.search(location):
            continue
        rows.append(
            {
                "status": "candidate",
                "company_slug": company,
                "company": company,
                "role": title,
                "location": location,
                "team": team,
                "url": url,
                "id": str(job.get("id") or ""),
            }
        )
        if max_jobs_per_company and len(rows) >= max_jobs_per_company:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="")
    parser.add_argument("--companies", nargs="*", default=DEFAULT_COMPANIES)
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--max-jobs-per-company", type=int, default=8)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--company-cap", type=int, default=20)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    known = load_known_urls()
    company_counts = load_company_submitted_counts()
    companies = [
        company for company in dict.fromkeys(c.strip().lower() for c in args.companies if c.strip())
        if not blocked_company(company)
    ]
    if args.company_cap > 0:
        companies = [
            company for company in companies
            if company_counts.get(company_key(company), 0) < args.company_cap
        ]
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = [
            pool.submit(company_jobs, company, known, args.max_jobs_per_company)
            for company in companies
        ]
        for future in as_completed(futures):
            rows.extend(future.result())
    rows.sort(key=lambda row: (row["company"], row["role"], row["location"]))
    if args.limit:
        rows = rows[: args.limit]

    date = args.date or subprocess.check_output(
        ["bash", "-lc", "TZ=Asia/Shanghai date +%Y-%m-%d"], text=True
    ).strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else OUT_DIR / f"lever-candidates-{date}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["status", "company", "role", "location", "team", "url", "company_slug", "id"]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)

    print(json.dumps({"out": str(out_path), "count": len(rows)}, indent=2))
    for row in rows[:50]:
        print(f"{row['company']} | {row['role']} | {row['location']} | {row['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
