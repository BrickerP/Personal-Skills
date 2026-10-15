#!/usr/bin/env python3
"""Audit the Lavayou author-lens skill package for minimum usable evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "SKILL.md",
    "data/source-index.jsonl",
    "data/corpus-stats.json",
    "references/00-overview.md",
    "references/01-operating-frame.md",
    "references/02-topic-map.md",
    "references/03-response-playbook.md",
    "references/04-corpus-audit.md",
    "scripts/search_source_index.py",
]
FORBIDDEN_CARD_FIELDS = {"text", "content", "content_html", "rendered", "fulltext"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(SKILL_ROOT))
    parser.add_argument("--expected-count", type=int, default=1005)
    args = parser.parse_args()
    root = Path(args.root)
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            return fail(f"missing {rel}")
    cards = load_jsonl(root / "data" / "source-index.jsonl")
    stats = load_json(root / "data" / "corpus-stats.json")
    if len(cards) != int(stats.get("article_count", -1)):
        return fail(f"index count {len(cards)} != stats article_count {stats.get('article_count')}")
    if len(cards) < args.expected_count:
        return fail(f"index has {len(cards)} cards, expected at least {args.expected_count}")
    for idx, card in enumerate(cards, start=1):
        forbidden = FORBIDDEN_CARD_FIELDS.intersection(card)
        if forbidden:
            return fail(f"card {idx} contains forbidden fulltext-like fields: {sorted(forbidden)}")
        for key in ["url", "date", "title", "topics", "reasoning_patterns", "summary_auto"]:
            if key not in card or card[key] in (None, "", []):
                return fail(f"card {idx} missing usable {key}")
    print(
        json.dumps(
            {
                "ok": True,
                "skill_root": str(root),
                "article_count": len(cards),
                "date_range": stats.get("date_range"),
                "fulltext_fields_present": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
