#!/usr/bin/env python3
"""Append structured ATS attempt outcomes and evolve the adapter registry."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ats_registry import load_registry, save_registry, update_platform_stats

SKILL_DATA = Path(__file__).resolve().parent.parent / "data"
EVOLUTION_LOG = Path.home() / "job-hunt" / "ats-evolution-log.jsonl"
EVOLUTION_LOG_MIRROR = SKILL_DATA / "ats-evolution-log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_event(event: dict) -> Path:
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("timestamp", _utc_now())
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with EVOLUTION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)
    EVOLUTION_LOG_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    with EVOLUTION_LOG_MIRROR.open("a", encoding="utf-8") as handle:
        handle.write(line)
    return EVOLUTION_LOG


def evolve_from_attempt(
    *,
    platform: str,
    url: str,
    status: str,
    blocker: str | None = None,
    dom_snippet: str | None = None,
    fields_missing: list[str] | None = None,
    company: str = "",
    role: str = "",
    channel: str = "linkedin-external",
) -> dict:
    registry = load_registry()
    success = status == "Submitted"
    registry = update_platform_stats(registry, platform, success=success, blocker=blocker)

    platforms = registry.setdefault("platforms", {})
    entry = platforms.get(platform)
    if entry is None and platform not in platforms:
        platforms[platform] = {
            "platform_id": platform,
            "display_name": platform,
            "domain_patterns": [],
            "adapter_script": None,
            "status": "experimental",
            "field_mappings": {"radio": {}, "text": {}},
            "blockers_seen": [],
            "attempts": 1,
            "successes": 1 if success else 0,
            "last_attempt": _utc_now()[:10],
            "notes": "Auto-discovered during evolution loop.",
        }
        entry = platforms[platform]

    if fields_missing and entry:
        mappings = entry.setdefault("field_mappings", {})
        radio = mappings.setdefault("radio", {})
        text = mappings.setdefault("text", {})
        for field in fields_missing:
            label = field.strip()
            if not label:
                continue
            if re.search(r"authorized|sponsor|visa|relocate", label, re.I):
                answer = "Yes" if re.search(r"authorized|eligible", label, re.I) else "No"
                key = label[:80]
                if key not in radio:
                    radio[key] = answer
            elif re.search(r"city|state|location", label, re.I):
                key = label[:80]
                if key not in text:
                    text[key] = "San Francisco, California"

    if blocker and entry and entry.get("status") == "custom":
        entry["status"] = "experimental"

    save_registry(registry)

    event = {
        "platform": platform,
        "url": url,
        "status": status,
        "blocker": blocker,
        "dom_snippet": (dom_snippet or "")[:2000],
        "fields_missing": fields_missing or [],
        "company": company,
        "role": role,
        "channel": channel,
    }
    log_path = append_event(event)
    return {"ok": True, "log": str(log_path), "registry_updated": True, "platform": platform, "status": status}


def main() -> int:
    parser = argparse.ArgumentParser(description="Log ATS attempt and evolve registry")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--blocker")
    parser.add_argument("--dom-snippet")
    parser.add_argument("--fields-missing", nargs="*", default=[])
    parser.add_argument("--company", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--channel", default="linkedin-external")
    args = parser.parse_args()

    result = evolve_from_attempt(
        platform=args.platform,
        url=args.url,
        status=args.status,
        blocker=args.blocker,
        dom_snippet=args.dom_snippet,
        fields_missing=args.fields_missing,
        company=args.company,
        role=args.role,
        channel=args.channel,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
