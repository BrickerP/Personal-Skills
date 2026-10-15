#!/usr/bin/env python3
"""Load ROUND-MANIFEST.yaml from skill root and print JSON to stdout."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parent
sys.path.insert(0, str(_RUNTIME))
from paths import MANIFEST_PATH, SKILL_ROOT  # noqa: E402


def _parse_simple_yaml(text: str) -> dict:
    root: dict = {}
    section: dict | None = None
    section_key: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            section = None
            section_key = None
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                if value.isdigit():
                    root[key] = int(value)
                else:
                    root[key] = os.path.expanduser(value)
            else:
                section_key = key
                section = {}
                root[section_key] = section
            continue
        if section is None:
            continue
        m = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.isdigit():
            section[k] = int(v)
        else:
            section[k] = os.path.expanduser(v)
    return root


def _resolve_manifest_paths(data: dict) -> dict:
    skill = str(SKILL_ROOT)

    def fix(value):
        if isinstance(value, str):
            return value.replace("$SKILL_ROOT", skill)
        if isinstance(value, dict):
            return {k: fix(v) for k, v in value.items()}
        return value

    return fix(data)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"manifest not found: {MANIFEST_PATH}")
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except ImportError:
        data = _parse_simple_yaml(text)
    return _resolve_manifest_paths(data)


def main() -> int:
    try:
        data = load_manifest()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
