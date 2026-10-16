#!/usr/bin/env python3
"""Canonical path resolution for daily-job-apply skill (portable, no Mac-local hardcoding)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# SKILL_ROOT = parent of runtime/
SKILL_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = SKILL_ROOT / "runtime"
ADAPTERS_DIR = SKILL_ROOT / "adapters"
DATA_DIR = SKILL_ROOT / "data"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
STATE_DIR = SKILL_ROOT / "state"
BIN_DIR = SKILL_ROOT / "bin"
CONFIG_ENV = Path.home() / ".config" / "daily-job-apply" / "env"


def _load_config_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not CONFIG_ENV.exists():
        return out
    for raw in CONFIG_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = os.path.expanduser(value.strip().strip("\"'"))
    return out


_CFG = _load_config_env()


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key) or _CFG.get(key) or default


WORK_DIR = Path(_cfg("DAILY_JOB_APPLY_WORK_DIR", str(Path.home() / "job-hunt")))
CANDIDATE_POOLS_DIR = WORK_DIR / "candidate-pools"
LEDGER_PATH = WORK_DIR / "application-ledger.md"

CHROME_PROFILE = _cfg("CHROME_PROFILE", _cfg("CHROME_DEBUG_PROFILE_DIR", "Profile 2"))
GMAIL_PROFILE = _cfg("GMAIL_PROFILE", CHROME_PROFILE)

PDF_DIR = Path(_cfg("DAILY_JOB_APPLY_PDF_DIR", ""))
if not PDF_DIR:
    profile_path = DATA_DIR / "profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            resume_paths = profile.get("resume_paths") or {}
            one_p = (
                resume_paths.get("ai_agent_1p_en")
                or resume_paths.get("default_en")
                or resume_paths.get("default_1p_en")
                or resume_paths.get("ai_agent")
                or resume_paths.get("backend_platform")
                or resume_paths.get("general_swe")
            )
            if one_p:
                PDF_DIR = Path(one_p).parent
        except (json.JSONDecodeError, OSError):
            pass
if not PDF_DIR:
    PDF_DIR = Path.home() / "Documents" / "resumes"

NODE_MODULES = ADAPTERS_DIR / "node_modules"
NODE_PATH = _cfg("NODE_PATH", str(NODE_MODULES) if NODE_MODULES.is_dir() else "")

CHROME_USE_BIN = _cfg("CHROME_USE_BIN", "chrome-use")


def _tracker_has_data(path: Path) -> bool:
    if not path.exists():
        return False
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return len(lines) > 1


def tracker_csv() -> Path:
    override = _cfg("DAILY_JOB_APPLY_TRACKER")
    if override:
        return Path(override)
    state_tracker = STATE_DIR / "tracker.csv"
    work_tracker = WORK_DIR / "tracker.csv"
    if _tracker_has_data(work_tracker) and not _tracker_has_data(state_tracker):
        return work_tracker
    return state_tracker


TRACKER_CSV = tracker_csv()
MANIFEST_PATH = SKILL_ROOT / "ROUND-MANIFEST.yaml"

# Back-compat aliases used by migrated scripts
JOB_HUNT = WORK_DIR
JOB_HUNT_DATA = DATA_DIR
OMX = ADAPTERS_DIR
SKILL_DATA = DATA_DIR


def resume_pdf(variant: str = "1p") -> Path:
    profile_path = DATA_DIR / "profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            paths_map = profile.get("resume_paths") or {}
            if variant in ("2p", "2P"):
                key = "ai_agent_2p_en"
            else:
                key = "ai_agent_1p_en"
            for candidate in (key, "default_en", "default_1p_en", "ai_agent", "backend_platform", "general_swe"):
                if paths_map.get(candidate):
                    return Path(paths_map[candidate])
        except (json.JSONDecodeError, OSError):
            pass
    return PDF_DIR / "Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf"


def ensure_runtime_dirs() -> None:
    for path in (STATE_DIR, CANDIDATE_POOLS_DIR, ADAPTERS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def as_dict() -> dict[str, Any]:
    return {
        "SKILL_ROOT": str(SKILL_ROOT),
        "RUNTIME_ROOT": str(RUNTIME_ROOT),
        "ADAPTERS_DIR": str(ADAPTERS_DIR),
        "DATA_DIR": str(DATA_DIR),
        "WORK_DIR": str(WORK_DIR),
        "TRACKER_CSV": str(TRACKER_CSV),
        "PDF_DIR": str(PDF_DIR),
        "MANIFEST_PATH": str(MANIFEST_PATH),
        "CHROME_PROFILE": CHROME_PROFILE,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        import json as _json

        print(_json.dumps(as_dict(), indent=2))
    else:
        for key, value in as_dict().items():
            print(f"{key}={value}")
