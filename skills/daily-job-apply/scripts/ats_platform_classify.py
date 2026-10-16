#!/usr/bin/env python3
"""Classify an application URL/page into a platform and apply route (adapter script or playbook)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ats_registry import domain_matches, find_platform_for_url, load_registry  # noqa: E402
from greenhouse_url_resolver import resolve_greenhouse_url  # noqa: E402

UNSUPPORTED_STATUSES = {"unsupported", "unsupported-direct"}
# Applyable status -> registry field that must be non-empty for the platform to be applyable.
APPLYABLE_STATUS_FIELDS = {"production": "adapter_script", "playbook": "playbook"}
HARVEST_STATUSES = {"routable", "unsupported-direct", "needs-parse"}


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_applyable(status: str, entry: dict | None) -> bool:
    required = APPLYABLE_STATUS_FIELDS.get(status)
    return bool(required) and _has_text((entry or {}).get(required))


def harvest_status_from_route(route: dict) -> str:
    platform_status = (route.get("status") or "").lower()
    if platform_status in UNSUPPORTED_STATUSES:
        return "unsupported-direct"
    if route.get("apply_allowed"):
        return "routable"
    return "needs-parse"


def adapter_route_from_route(route: dict) -> str:
    platform_id = route.get("platform_id") or "custom"
    if not route.get("apply_allowed"):
        return platform_id
    script = route.get("adapter_script")
    if script:
        return str(script)
    if platform_id == "greenhouse" and route.get("board") and route.get("job_id"):
        return f"greenhouse:{route['board']}/{route['job_id']}"
    if _has_text(route.get("playbook")):
        return f"playbook:{platform_id}"
    return platform_id


def classify_from_html(html: str) -> str | None:
    text = (html or "")[:50000].lower()
    hints = [
        ("ashby", r"ashbyhq|ashby-application|_systemfield_resume"),
        ("greenhouse", r"greenhouse\.io|grnhse\.|gh_jid"),
        ("lever", r"jobs\.lever\.co|lever-application"),
        ("workable", r"workable\.com|apply\.workable"),
        ("workday", r"myworkdayjobs|workday"),
        ("jackandjill", r"jackandjill\.ai"),
        ("jobright", r"jobright\.ai"),
        ("remotehunter", r"remotehunter\.com"),
    ]
    for platform_id, pattern in hints:
        if re.search(pattern, text, re.I):
            return platform_id
    return None


def classify_url(url: str, *, html: str | None = None, registry_path: Path | None = None) -> dict:
    registry = load_registry(registry_path)
    platform_id, entry = find_platform_for_url(registry, url)

    if platform_id == "custom" and html:
        html_guess = classify_from_html(html)
        if html_guess:
            platform_id = html_guess
            entry = registry.get("platforms", {}).get(platform_id)

    if domain_matches(url, ["greenhouse.io"]):
        platform_id = "greenhouse"
        entry = registry.get("platforms", {}).get("greenhouse")

    status = (entry or {}).get("status") or "experimental"
    adapter_script = (entry or {}).get("adapter_script")
    playbook = (entry or {}).get("playbook")
    route = {
        "platform_id": platform_id,
        "status": status,
        "adapter_script": adapter_script,
        "playbook": playbook,
        "apply_allowed": _is_applyable(status, entry),
        "skip_reason": None,
        "resolved_url": url,
        "board": "",
        "job_id": "",
    }

    if status in UNSUPPORTED_STATUSES:
        route["apply_allowed"] = False
        route["skip_reason"] = f"unsupported-platform:{platform_id}"
    elif platform_id == "custom":
        route["apply_allowed"] = False
        route["skip_reason"] = "unknown-platform"

    if platform_id == "greenhouse" and url:
        gh = resolve_greenhouse_url(url)
        route["greenhouse_resolution"] = gh.to_dict()
        if gh.ok:
            route["resolved_url"] = gh.canonical_url
            route["board"] = gh.board
            route["job_id"] = gh.job_id
        elif status in APPLYABLE_STATUS_FIELDS:
            route["apply_allowed"] = False
            route["skip_reason"] = gh.error or "greenhouse-unresolved"

    return route


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify ATS platform from URL/HTML")
    parser.add_argument("--url", required=True)
    parser.add_argument("--html-file")
    parser.add_argument("--registry")
    args = parser.parse_args()

    html = None
    if args.html_file:
        html = Path(args.html_file).read_text(encoding="utf-8", errors="ignore")

    registry_path = Path(args.registry) if args.registry else None
    result = classify_url(args.url, html=html, registry_path=registry_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
