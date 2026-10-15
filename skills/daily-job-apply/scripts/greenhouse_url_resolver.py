#!/usr/bin/env python3
"""Resolve Greenhouse board/job-id from standard or embed URLs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.parse
from dataclasses import dataclass, asdict

STANDARD_RE = re.compile(
    r"https?://(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)/jobs/([^/?#]+)",
    re.I,
)
EMBED_RE = re.compile(
    r"https?://app\.greenhouse\.io/embed/job_app\?([^#]+)",
    re.I,
)
EMBED_BOARD_RE = re.compile(
    r"(?:boards|job-boards)\.greenhouse\.io/([^/\"'\s]+)/jobs/(\d+)",
    re.I,
)
EMBED_FOR_RE = re.compile(r"(?:\?|&)for=([^&\"'\s]+)", re.I)
GH_JID_RE = re.compile(r"(?:^|[?&])gh_jid=(\d+)", re.I)


@dataclass
class GreenhouseResolution:
    ok: bool
    board: str = ""
    job_id: str = ""
    canonical_url: str = ""
    source: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value).rstrip("/")
    value = re.sub(r"/(?:application|confirmation|apply|thanks)$", "", value, flags=re.I)
    return value.replace("https://boards.greenhouse.io/", "https://job-boards.greenhouse.io/")


def parse_standard_url(url: str) -> GreenhouseResolution:
    normalized = norm_url(url)
    match = STANDARD_RE.match(normalized) or STANDARD_RE.match(url.strip())
    if not match:
        return GreenhouseResolution(ok=False, error="not-standard-greenhouse-url")
    board, job_id = match.group(1), match.group(2)
    canonical = f"https://job-boards.greenhouse.io/{board}/jobs/{job_id}"
    return GreenhouseResolution(ok=True, board=board, job_id=job_id, canonical_url=canonical, source="standard-path")


def fetch_embed_html(token: str) -> str:
    query = urllib.parse.urlencode({"token": token})
    target = f"https://app.greenhouse.io/embed/job_app?{query}"
    proc = subprocess.run(
        ["curl", "-fsSL", "--max-time", "20", target],
        capture_output=True,
        text=True,
        timeout=25,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "curl-failed")
    return proc.stdout


def resolve_embed_url(url: str) -> GreenhouseResolution:
    match = EMBED_RE.match(url.strip())
    if not match:
        return GreenhouseResolution(ok=False, error="not-embed-url")
    qs = urllib.parse.parse_qs(match.group(1), keep_blank_values=True)
    token = (qs.get("token") or [""])[0].strip()
    if not token:
        return GreenhouseResolution(ok=False, error="embed-missing-token")
    try:
        html = fetch_embed_html(token)
    except Exception as exc:
        return GreenhouseResolution(ok=False, error=f"embed-fetch-failed:{exc}")

    board_job = EMBED_BOARD_RE.search(html)
    if board_job:
        board, job_id = board_job.group(1), board_job.group(2)
        canonical = f"https://job-boards.greenhouse.io/{board}/jobs/{job_id}"
        return GreenhouseResolution(ok=True, board=board, job_id=job_id, canonical_url=canonical, source="embed-html")

    for_param = EMBED_FOR_RE.search(url) or EMBED_FOR_RE.search(html)
    if for_param:
        board = for_param.group(1)
        canonical = f"https://job-boards.greenhouse.io/{board}/jobs/{token}"
        return GreenhouseResolution(ok=True, board=board, job_id=token, canonical_url=canonical, source="embed-for-param")

    return GreenhouseResolution(ok=False, error="embed-unresolved")


def resolve_greenhouse_url(url: str) -> GreenhouseResolution:
    raw = (url or "").strip()
    if not raw:
        return GreenhouseResolution(ok=False, error="empty-url")

    standard = parse_standard_url(raw)
    if standard.ok:
        return standard

    if "app.greenhouse.io/embed" in raw.lower():
        embed = resolve_embed_url(raw)
        if embed.ok:
            return embed

    parsed = urllib.parse.urlparse(raw)
    gh_jid = ""
    if parsed.query:
        gh_jid = (urllib.parse.parse_qs(parsed.query).get("gh_jid") or [""])[0]
    if not gh_jid:
        gh_match = GH_JID_RE.search(raw)
        gh_jid = gh_match.group(1) if gh_match else ""

    if gh_jid and "greenhouse.io" in parsed.netloc.lower():
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[-2] == "jobs":
            board = path_parts[-3] if len(path_parts) >= 3 else path_parts[0]
            canonical = f"https://job-boards.greenhouse.io/{board}/jobs/{gh_jid}"
            return GreenhouseResolution(ok=True, board=board, job_id=gh_jid, canonical_url=canonical, source="gh_jid-param")

    if "app.greenhouse.io/embed" in raw.lower():
        return resolve_embed_url(raw)
    return GreenhouseResolution(ok=False, error="unresolved-greenhouse-url")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Greenhouse board and job id from a URL")
    parser.add_argument("--url", required=True)
    parser.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args()
    result = resolve_greenhouse_url(args.url)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
