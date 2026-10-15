#!/usr/bin/env python3
"""Mine NEW Ashby slugs from curated GitHub job-list repos."""

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
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

POOLS = HOME / "job-hunt" / "candidate-pools"
TRACKER = TRACKER_CSV

GITHUB_REPOS = [
    "SimplifyJobs/New-Grad-Positions",
    "SimplifyJobs/Summer2025-Internships",
    "SimplifyJobs/Listings",
    "pittcsc/Summer2026-Internships",
    "pittcsc/Summer2025-Internships",
    "Ouckah/New-Grad-2026",
    "Ouckah/New-Grad-2025",
    "Ouckah/SWE2026",
    "speedyapply/2026-SWE-College-Jobs",
    "speedyapply/2025-SWE-College-Jobs",
    "speedyapply/2026-New-Grad",
]

# Fast path: raw README/listing files (avoids slow gh api tree walks).
RAW_README_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Listings/main/README.md",
    "https://raw.githubusercontent.com/pittcsc/Summer2026-Internships/dev/README.md",
    "https://raw.githubusercontent.com/pittcsc/Summer2025-Internships/dev/README.md",
    "https://raw.githubusercontent.com/Ouckah/New-Grad-2026/main/README.md",
    "https://raw.githubusercontent.com/Ouckah/SWE2026/main/README.md",
    "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md",
    "https://raw.githubusercontent.com/speedyapply/2026-New-Grad/main/README.md",
]

SKIP_SLUGS = {
    "g2i", "g2iinc", "crusoe", "brainco", "lgads", "workos",
    "afterquery", "aida", "cognition", "beam", "adaption",
    "abundant", "cohere", "meshy", "relace", "additiveai",
    "a-team", "convex-dev", "andromeda", "wand-ai", "extropic",
    "speakeasy", "aim", "generalist", "console",
    "jack-jill-external-ats",
}

SLUG_RX = re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9._%-]+)", re.I)


def norm_key(slug: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", slug.casefold())


def known_slugs() -> set[str]:
    """Exclude spam/skip slugs and boards already present in tracker JD_URL.

    Do not scan all historical pool CSVs — that over-filters GitHub mines to zero
    once prior rounds sourced the same README slug universe.
    """
    slugs = {norm_key(s) for s in SKIP_SLUGS}
    rx = re.compile(r"https://jobs\.ashbyhq\.com/([^/\s,\"]+)", re.I)
    if TRACKER.is_file():
        import csv

        for row in csv.DictReader(TRACKER.open(encoding="utf-8")):
            url = row.get("JD_URL") or row.get("URL") or ""
            for m in rx.finditer(url):
                slugs.add(norm_key(urllib.parse.unquote(m.group(1))))
    return slugs


def gh_search_repo(repo: str, per_page: int = 100) -> str:
    try:
        proc = subprocess.run(
            ["gh", "api", f"search/code", "-f", f"q=repo:{repo} jobs.ashbyhq.com", "-f", f"per_page={per_page}"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        return proc.stdout if proc.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def fetch_raw_url(url: str, timeout: int = 20) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception:
        return ""


def gh_raw_repo_scan(repo: str) -> str:
    """Fallback: list repo tree and fetch likely listing files."""
    owner, name = repo.split("/", 1)
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/git/trees/HEAD?recursive=1"],
            capture_output=True,
            text=True,
            timeout=45,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    blobs = []
    for item in data.get("tree") or []:
        if item.get("type") != "blob":
            continue
        path = item.get("path") or ""
        if not re.search(r"\.(md|json|csv|yml|yaml|txt)$", path, re.I):
            continue
        if not re.search(r"(job|intern|listing|position|grad|swe)", path, re.I):
            continue
        blobs.append(path)
    text_parts: list[str] = []
    for path in blobs[:15]:
        try:
            proc2 = subprocess.run(
                ["gh", "api", f"repos/{owner}/{name}/contents/{urllib.parse.quote(path)}"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if proc2.returncode != 0:
            continue
        try:
            content = json.loads(proc2.stdout or "{}")
            import base64
            raw = base64.b64decode(content.get("content") or "").decode("utf-8", "replace")
            text_parts.append(raw)
        except Exception:
            continue
    return "\n".join(text_parts)


def board_alive(slug: str, timeout: int = 10) -> bool:
    url = f"https://jobs.ashbyhq.com/{urllib.parse.quote(slug, safe='-._~%')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8000).decode("utf-8", "replace")
            return "window.__appData" in body or "jobPostings" in body
    except Exception:
        return False


def extract_slugs(text: str, seen: set[str]) -> list[str]:
    found: list[str] = []
    for m in SLUG_RX.finditer(text):
        slug = urllib.parse.unquote(m.group(1)).strip().rstrip(").,;\"'")
        key = norm_key(slug)
        if not key or key in seen or len(slug) < 2:
            continue
        seen.add(key)
        found.append(slug)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-slugs", type=int, default=30)
    parser.add_argument("--offset", type=int, default=0, help="Skip first N verified candidates (dedupe across rounds)")
    parser.add_argument("--verify-boards", action="store_true", default=True)
    args = parser.parse_args()

    seen = known_slugs()
    candidates: list[str] = []
    repo_hits: dict[str, int] = {}

    for url in RAW_README_URLS:
        text = fetch_raw_url(url)
        if text:
            batch = extract_slugs(text, seen)
            repo_hits[url] = len(batch)
            candidates.extend(batch)

    for repo in GITHUB_REPOS:
        text = gh_search_repo(repo)
        if not text or "items" not in text:
            text = gh_raw_repo_scan(repo)
        else:
            # enrich with item metadata text
            try:
                data = json.loads(text)
                text = json.dumps(data)
            except json.JSONDecodeError:
                pass
        if not text:
            repo_hits[repo] = 0
            continue
        batch = extract_slugs(text, seen)
        repo_hits[repo] = len(batch)
        candidates.extend(batch)

        # also scan each search hit file content
        try:
            data = json.loads(gh_search_repo(repo))
            for item in (data.get("items") or [])[:10]:
                html_url = item.get("html_url") or ""
                if not html_url:
                    continue
                try:
                    raw_proc = subprocess.run(
                        ["gh", "api", html_url.replace("https://github.com/", "repos/").replace("/blob/", "/contents/")],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                except (subprocess.TimeoutExpired, OSError):
                    continue
                if raw_proc.returncode != 0:
                    continue
                try:
                    import base64
                    content = json.loads(raw_proc.stdout or "{}")
                    raw = base64.b64decode(content.get("content") or "").decode("utf-8", "replace")
                    candidates.extend(extract_slugs(raw, seen))
                except Exception:
                    continue
        except Exception:
            pass

    verified_all: list[str] = []
    for slug in candidates:
        if args.verify_boards:
            if board_alive(slug):
                verified_all.append(slug)
        else:
            verified_all.append(slug)

    offset = max(0, args.offset)
    verified = verified_all[offset : offset + args.min_slugs + 20]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = f"# round18 github repos {len(verified)} verified boards (candidates={len(candidates)})"
    out.write_text(header + "\n" + "\n".join(verified) + ("\n" if verified else ""), encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "candidates": len(candidates),
        "verified": len(verified),
        "verified_total": len(verified_all),
        "offset": offset,
        "repo_hits": repo_hits,
        "slugs": verified[:25],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
