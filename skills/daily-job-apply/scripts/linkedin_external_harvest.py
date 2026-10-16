#!/usr/bin/env python3
"""LinkedIn external apply harvest-only: discover roles, classify ATS, write CSV pool."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ats_platform_classify import (  # noqa: E402
    adapter_route_from_route,
    classify_url,
    harvest_status_from_route,
)

HOME = Path.home()
POOL_DIR = HOME / "job-hunt" / "candidate-pools"

# Browser automation goes through chrome-use, which drives the user's real,
# already-signed-in Chrome. There is no debug profile and no CDP port.
CHROME_USE = os.environ.get("CHROME_USE_BIN", "chrome-use")
CHROME_USE_SESSION = os.environ.get("CHROME_USE_SESSION", "harvest")
CHROME_USE_BROWSER = os.environ.get("CHROME_USE_BROWSER", "yplmicro@gmail.com")

SEARCHES = [
    "AI+Agent+Engineer+OR+AI+Platform+Engineer",
    "Backend+Engineer+AI+OR+ML+Infrastructure+Engineer",
    "Agent+Infrastructure+OR+Developer+Tools+AI",
    "Software+Engineer+Greenhouse+OR+Staff+Engineer+Remote",
    "ML+Platform+Engineer+OR+AI+Infrastructure",
]

BLOCKED_COMPANIES = {"speechify", "jobgether", "hightouch"}
HARVEST_FIELDS = ("url", "platform", "adapter_route", "status")
MAX_DETAIL_ERRORS = 3


class ChromeUseError(RuntimeError):
    """chrome-use was missing, timed out, failed, or the page was not what the harvest expects."""


def decode_safety_url(href: str) -> str:
    if not href:
        return ""
    if "linkedin.com/safety/go" in href:
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        raw = (qs.get("url") or [""])[0]
        return urllib.parse.unquote(raw)
    return href


def _parse_envelope(stdout: str) -> dict | None:
    """The `--json` envelope is the last stdout line that parses as an object with a `success` key."""
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "success" in payload:
            return payload
    return None


def _chrome_use(args: list[str], *, timeout: int = 60) -> dict:
    """Run one `chrome-use --json` command in the harvest session and return its `data`."""
    cmd = [CHROME_USE, "--session", CHROME_USE_SESSION, "--browser", CHROME_USE_BROWSER, "--json", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
    except FileNotFoundError as exc:
        raise ChromeUseError(f"{CHROME_USE} not found; install chrome-use first") from exc
    except subprocess.TimeoutExpired as exc:
        raise ChromeUseError(f"chrome-use {args[0]} timed out after {timeout}s") from exc
    envelope = _parse_envelope(proc.stdout)
    if envelope is None:
        detail = (proc.stderr or proc.stdout or "").strip()[:300] or f"exit code {proc.returncode}"
        raise ChromeUseError(f"chrome-use {args[0]} returned no JSON envelope: {detail}")
    if not envelope.get("success"):
        raise ChromeUseError(f"chrome-use {args[0]} failed: {envelope.get('error') or envelope.get('code')}")
    return envelope.get("data") or {}


def close_session() -> None:
    """Close the tabs the harvest session opened; the daemon would reap them when idle anyway."""
    try:
        _chrome_use(["close"], timeout=30)
    except ChromeUseError:
        pass


def page_eval(js: str, *, navigate: str | None = None):
    """Run `js` in the harvest session's own tab (opening `navigate` first) and return the eval result.

    The session opens its tab in the connected yplmicro profile, which is already signed in to
    LinkedIn; no tab has to be open beforehand and the user's own tabs are never touched.
    """
    if navigate:
        _chrome_use(["open", navigate], timeout=90)
        time.sleep(3.5)
    return _chrome_use(["eval", js]).get("result")


def page_json(js: str, *, navigate: str | None = None):
    """Like page_eval for JS that returns JSON.stringify(...); anything else raises instead of reading as empty."""
    result = page_eval(js, navigate=navigate)
    if not isinstance(result, str):
        return result
    try:
        return json.loads(result)
    except json.JSONDecodeError as exc:
        raise ChromeUseError(f"page JS did not return JSON: {result[:120]!r}") from exc


def require_linkedin_page(href: str) -> None:
    parsed = urllib.parse.urlsplit(href or "")
    host = (parsed.hostname or "").lower()
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        raise ChromeUseError(f"expected a linkedin.com page but landed on {href!r}")
    if re.search(r"/(login|authwall|checkpoint|uas/)", parsed.path):
        raise ChromeUseError(f"LinkedIn is asking for sign-in ({href!r}); sign in to the yplmicro Chrome profile first")


def scrape_search(keywords: str, max_cards: int = 25) -> list[dict]:
    url = (
        f"https://www.linkedin.com/jobs/search/?keywords={keywords}"
        "&location=United+States&f_TPR=r604800&sortBy=R"
    )
    page_eval("window.scrollTo(0, document.body.scrollHeight); 'scrolled'", navigate=url)
    time.sleep(2)
    scrape_js = f"""JSON.stringify((() => {{
      const seen = new Set();
      const jobs = [];
      const cards = document.querySelectorAll('li.scaffold-layout__list-item, div.job-card-container');
      for (const card of cards) {{
        const link = card.querySelector('a[href*="/jobs/view/"]');
        if (!link) continue;
        const lid = link.href.split('/jobs/view/')[1]?.split('/')[0];
        if (!lid || seen.has(lid)) continue;
        seen.add(lid);
        const text = (card.innerText || '').replace(/\\s+/g, ' ');
        const hasEasy = /easy apply/i.test(text);
        jobs.push({{
          linkedinUrl: 'https://www.linkedin.com/jobs/view/' + lid + '/',
          title: (link.innerText || '').replace(/\\s+/g, ' ').trim(),
          company: (card.querySelector('.artdeco-entity-lockup__subtitle, .job-card-container__company-name')?.innerText || '').trim(),
          location: (card.querySelector('.job-card-container__metadata-item')?.innerText || '').trim(),
          hasEasyApply: hasEasy,
          cardText: text.slice(0, 180),
        }});
        if (jobs.length >= {max_cards}) break;
      }}
      return {{href: location.href, jobs}};
    }})())"""
    payload = page_json(scrape_js)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ChromeUseError(f"unexpected job-card payload: {str(payload)[:120]!r}")
    require_linkedin_page(payload.get("href", ""))
    return payload["jobs"]


def extract_apply_url(linkedin_url: str) -> dict:
    js = """JSON.stringify((() => {
      const btn = Array.from(document.querySelectorAll('a,button')).find(e => /^apply$/i.test((e.innerText||'').trim()));
      const href = btn?.href || '';
      const easy = /easy apply/i.test(document.body.innerText.slice(0, 10000));
      const title = document.querySelector('.job-details-jobs-unified-top-card__job-title, h1')?.innerText?.trim() || '';
      const company = document.querySelector('.job-details-jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name')?.innerText?.trim() || '';
      return {href: location.href, title, company, applyHref: href, easyApply: easy};
    })())"""
    data = page_json(js, navigate=linkedin_url)
    if isinstance(data, dict) and not data.get("applyHref") and not data.get("easyApply"):
        time.sleep(2)
        data = page_json(js)
    if not isinstance(data, dict):
        raise ChromeUseError(f"unexpected job-detail payload: {str(data)[:120]!r}")
    require_linkedin_page(data.get("href", ""))
    data["externalUrl"] = decode_safety_url(data.get("applyHref", ""))
    data["linkedinUrl"] = linkedin_url
    return data


def harvest_row(job: dict, detail: dict) -> dict | None:
    company = (detail.get("company") or job.get("company") or "Unknown").strip()
    if detail.get("easyApply"):
        return None
    ext_url = detail.get("externalUrl") or ""
    if not ext_url:
        return None
    if re.sub(r"[^a-z0-9]+", "", company.casefold()) in BLOCKED_COMPANIES:
        return None

    route = classify_url(ext_url)
    apply_url = route.get("resolved_url") or ext_url
    return {
        "url": apply_url,
        "platform": route.get("platform_id", "custom"),
        "adapter_route": adapter_route_from_route(route),
        "status": harvest_status_from_route(route),
    }


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HARVEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in HARVEST_FIELDS})


def run_harvest(source_limit: int) -> tuple[list[dict], int, int]:
    """Search, then read each external-apply candidate. Returns (rows, cards_seen, detail_errors)."""
    sourced: dict[str, dict] = {}
    cards_seen = 0
    for kw in SEARCHES:
        jobs = scrape_search(kw, max_cards=20)
        cards_seen += len(jobs)
        for job in jobs:
            if job.get("hasEasyApply"):
                continue
            sourced[job["linkedinUrl"]] = job
        if len(sourced) >= source_limit:
            break
        time.sleep(2)

    rows: list[dict] = []
    detail_errors = 0
    for job in list(sourced.values())[:source_limit]:
        try:
            detail = extract_apply_url(job["linkedinUrl"])
        except ChromeUseError as exc:
            detail_errors += 1
            print(f"warning: skipped {job['linkedinUrl']}: {exc}", file=sys.stderr)
            if detail_errors >= MAX_DETAIL_ERRORS:
                raise
            continue
        time.sleep(1.5)
        row = harvest_row(job, detail)
        if row:
            rows.append(row)
    return rows, cards_seen, detail_errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest LinkedIn external apply candidates without applying")
    parser.add_argument("--source-limit", type=int, default=40)
    parser.add_argument("--out")
    args = parser.parse_args()

    today = dt.date.today().isoformat()
    out_path = Path(args.out) if args.out else POOL_DIR / f"linkedin-external-harvest-{today}.csv"

    try:
        rows, cards_seen, detail_errors = run_harvest(args.source_limit)
    except ChromeUseError as exc:
        print(f"harvest aborted: {exc}", file=sys.stderr)
        return 2
    finally:
        close_session()

    if cards_seen == 0:
        print(
            "harvest found no job cards in any search; LinkedIn may be signed out, rate-limited, or its markup changed",
            file=sys.stderr,
        )
        return 3

    write_csv(rows, out_path)
    summary = {
        "stage": "harvest-summary",
        "out": str(out_path),
        "sourced": len(rows),
        "detail_errors": detail_errors,
        "routable": sum(1 for r in rows if r["status"] == "routable"),
        "unsupported_direct": sum(1 for r in rows if r["status"] == "unsupported-direct"),
        "needs_parse": sum(1 for r in rows if r["status"] == "needs-parse"),
        "by_platform": {},
    }
    for row in rows:
        pid = row["platform"]
        summary["by_platform"][pid] = summary["by_platform"].get(pid, 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
