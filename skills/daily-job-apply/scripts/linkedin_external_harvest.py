#!/usr/bin/env python3
"""LinkedIn external apply harvest-only: discover roles, classify ATS, write CSV pool."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
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
LINKEDIN_TARGET = "9AD6CCD3448F5EB1FB88374AEF1F2C0A"

SEARCHES = [
    "AI+Agent+Engineer+OR+AI+Platform+Engineer",
    "Backend+Engineer+AI+OR+ML+Infrastructure+Engineer",
    "Agent+Infrastructure+OR+Developer+Tools+AI",
    "Software+Engineer+Greenhouse+OR+Staff+Engineer+Remote",
    "ML+Platform+Engineer+OR+AI+Infrastructure",
]

BLOCKED_COMPANIES = {"speechify", "jobgether", "hightouch"}
HARVEST_FIELDS = ("url", "platform", "adapter_route", "status")


def decode_safety_url(href: str) -> str:
    if not href:
        return ""
    if "linkedin.com/safety/go" in href:
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        raw = (qs.get("url") or [""])[0]
        return urllib.parse.unquote(raw)
    return href


def cdp_eval(js: str, *, navigate: str | None = None) -> dict:
    skill = HOME / ".codex" / "skills" / "chrome-read-write"
    if navigate:
        subprocess.run(
            [
                str(skill / "scripts/chrome_eval.sh"),
                LINKEDIN_TARGET,
                f"location.href={json.dumps(navigate)}; 'ok'",
            ],
            env={**dict(__import__("os").environ), "CHROME_EVAL_URL_MUST_CONTAIN": "linkedin.com"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        time.sleep(3.5)
    proc = subprocess.run(
        [str(skill / "scripts/chrome_eval.sh"), LINKEDIN_TARGET, js],
        env={**dict(__import__("os").environ), "CHROME_EVAL_URL_MUST_CONTAIN": "linkedin.com"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    raw = (proc.stdout or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def scrape_search(keywords: str, max_cards: int = 25) -> list[dict]:
    url = (
        f"https://www.linkedin.com/jobs/search/?keywords={keywords}"
        "&location=United+States&f_TPR=r604800&sortBy=R"
    )
    cdp_eval("window.scrollTo(0, document.body.scrollHeight); 'scrolled'", navigate=url)
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
      return jobs;
    }})())"""
    cdp_eval(scrape_js, navigate=url)
    raw = cdp_eval(scrape_js)
    return raw if isinstance(raw, list) else []


def extract_apply_url(linkedin_url: str) -> dict:
    js = """JSON.stringify((() => {
      const btn = Array.from(document.querySelectorAll('a,button')).find(e => /^apply$/i.test((e.innerText||'').trim()));
      const href = btn?.href || '';
      const easy = /easy apply/i.test(document.body.innerText.slice(0, 10000));
      const title = document.querySelector('.job-details-jobs-unified-top-card__job-title, h1')?.innerText?.trim() || '';
      const company = document.querySelector('.job-details-jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name')?.innerText?.trim() || '';
      return {title, company, applyHref: href, easyApply: easy};
    })())"""
    cdp_eval(js, navigate=linkedin_url)
    data = cdp_eval(js)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest LinkedIn external apply candidates without applying")
    parser.add_argument("--source-limit", type=int, default=40)
    parser.add_argument("--out")
    args = parser.parse_args()

    today = dt.date.today().isoformat()
    out_path = Path(args.out) if args.out else POOL_DIR / f"linkedin-external-harvest-{today}.csv"

    sourced: dict[str, dict] = {}
    for kw in SEARCHES:
        for job in scrape_search(kw, max_cards=20):
            if job.get("hasEasyApply"):
                continue
            sourced[job["linkedinUrl"]] = job
        if len(sourced) >= args.source_limit:
            break
        time.sleep(2)

    rows: list[dict] = []
    for job in list(sourced.values())[: args.source_limit]:
        detail = extract_apply_url(job["linkedinUrl"])
        time.sleep(1.5)
        row = harvest_row(job, detail)
        if row:
            rows.append(row)

    write_csv(rows, out_path)
    summary = {
        "stage": "harvest-summary",
        "out": str(out_path),
        "sourced": len(rows),
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
