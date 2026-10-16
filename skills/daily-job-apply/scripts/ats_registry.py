#!/usr/bin/env python3
"""Load and update the persistent ATS adapter registry."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SKILL_DATA = Path(__file__).resolve().parent.parent / "data"
REGISTRY_PATH = SKILL_DATA / "ats-adapter-registry.json"
MIRROR_PATH = Path.home() / "job-hunt" / "ats-adapter-registry.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_registry() -> dict[str, Any]:
    return {"version": 1, "updated_at": _utc_now(), "platforms": {}}


def load_registry(path: Path | None = None) -> dict[str, Any]:
    target = path or REGISTRY_PATH
    if not target.exists():
        return default_registry()
    with target.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_registry(registry: dict[str, Any], *, mirror: bool = True) -> Path:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry = deepcopy(registry)
    registry["updated_at"] = _utc_now()
    payload = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    REGISTRY_PATH.write_text(payload, encoding="utf-8")
    if mirror:
        MIRROR_PATH.parent.mkdir(parents=True, exist_ok=True)
        MIRROR_PATH.write_text(payload, encoding="utf-8")
    return REGISTRY_PATH


def get_platform(registry: dict[str, Any], platform_id: str) -> dict[str, Any] | None:
    return (registry.get("platforms") or {}).get(platform_id)


def _host(url: str) -> str:
    value = (url or "").strip()
    if "://" not in value:
        value = "//" + value
    try:
        return (urlsplit(value).hostname or "").lower()
    except ValueError:
        return ""


def domain_matches(url: str, domain_patterns: list[str]) -> bool:
    """True when the URL's host is a pattern or a subdomain of it; lookalike hosts do not match."""
    host = _host(url)
    for pattern in domain_patterns:
        needle = pattern.lower().strip()
        if needle and host and (host == needle or host.endswith("." + needle)):
            return True
    return False


def find_platform_for_url(registry: dict[str, Any], url: str) -> tuple[str, dict[str, Any] | None]:
    best_id = "custom"
    best_entry: dict[str, Any] | None = get_platform(registry, "custom")
    for platform_id, entry in (registry.get("platforms") or {}).items():
        if platform_id == "custom":
            continue
        patterns = entry.get("domain_patterns") or []
        if domain_matches(url, patterns):
            return platform_id, entry
    return best_id, best_entry


def _count(value: Any) -> int:
    """Stored counters may be null, missing or malformed; treat all of those as 0."""
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def update_platform_stats(
    registry: dict[str, Any],
    platform_id: str,
    *,
    success: bool | None = None,
    blocker: str | None = None,
    field_pattern: str | None = None,
    answer: str | None = None,
) -> dict[str, Any]:
    registry = deepcopy(registry)
    platforms = registry.setdefault("platforms", {})
    entry = deepcopy(platforms.get(platform_id) or {
        "platform_id": platform_id,
        "domain_patterns": [],
        "adapter_script": None,
        "status": "experimental",
        "field_mappings": {"radio": {}, "text": {}},
        "blockers_seen": [],
        "attempts": 0,
        "successes": 0,
    })
    attempts = _count(entry.get("attempts"))
    successes = _count(entry.get("successes"))
    if success is not None:
        entry["last_attempt"] = _utc_now()[:10]
        attempts += 1
        if success:
            successes += 1
    entry["attempts"] = attempts
    entry["successes"] = successes
    entry["success_rate"] = round(min(successes / attempts, 1.0), 3) if attempts else None
    if blocker:
        seen = list(entry.get("blockers_seen") or [])
        if blocker not in seen:
            seen.append(blocker)
        entry["blockers_seen"] = seen[-20:]
    if field_pattern and answer:
        mappings = entry.setdefault("field_mappings", {})
        bucket = mappings.setdefault("radio", {})
        if field_pattern not in bucket:
            bucket[field_pattern] = answer
    platforms[platform_id] = entry
    return registry
