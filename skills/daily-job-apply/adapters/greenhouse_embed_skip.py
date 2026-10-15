#!/usr/bin/env python3
"""Shared Greenhouse embed career-site URL filter.

Skip at sourcing/precheck before Playwright — these URLs timeout on embedded
career pages (vectra.ai, zipline.com, sambanova.ai, careers.* hosts).

Canonical domain list: ~/job-hunt/data/embed-career-domains.json
"""

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

import json
from pathlib import Path

_FALLBACK_EMBED_CAREER_SITE_DOMAINS = (
    "vectra.ai",
    "zipline.com",
    "sambanova.ai",
    "careers.",
)
EMBED_DATA_JSON = DATA_DIR / 'embed-career-domains.json'


def load_embed_career_site_domains() -> tuple[str, ...]:
    if EMBED_DATA_JSON.exists():
        data = json.loads(EMBED_DATA_JSON.read_text(encoding="utf-8"))
        domains = data.get("domains")
        if domains:
            return tuple(str(domain) for domain in domains)
    return _FALLBACK_EMBED_CAREER_SITE_DOMAINS


EMBED_CAREER_SITE_DOMAINS = load_embed_career_site_domains()


def is_embed_career_site_url(url: str) -> bool:
    lower = (url or "").lower()
    return any(domain in lower for domain in load_embed_career_site_domains())
