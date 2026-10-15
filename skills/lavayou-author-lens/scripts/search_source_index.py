#!/usr/bin/env python3
"""Search derived Lavayou source cards without loading the whole index into prompt context."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(__file__).resolve().parents[1] / "data" / "source-index.jsonl"


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score(row: dict[str, Any], terms: list[str]) -> int:
    haystack = "\n".join(
        [
            row.get("title", ""),
            " ".join(row.get("categories", [])),
            " ".join(row.get("tags", [])),
            " ".join(row.get("topics", [])),
            " ".join(row.get("reasoning_patterns", [])),
            " ".join(row.get("keywords", [])),
            row.get("summary_auto", ""),
        ]
    ).lower()
    total = 0
    for term in terms:
        total += haystack.count(term.lower()) * max(1, len(term))
    return total


def matches_filters(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.topic and args.topic not in row.get("topics", []):
        return False
    if args.pattern and args.pattern not in row.get("reasoning_patterns", []):
        return False
    if args.year and args.year != row.get("year"):
        return False
    return True


def render_markdown(rows: list[dict[str, Any]]) -> str:
    chunks = []
    for row in rows:
        chunks.append(
            "\n".join(
                [
                    f"- {row.get('date')} [{row.get('title')}]({row.get('url')})",
                    f"  - topics: {', '.join(row.get('topics', []))}",
                    f"  - patterns: {', '.join(row.get('reasoning_patterns', []))}",
                    f"  - keywords: {', '.join(row.get('keywords', [])[:8])}",
                    f"  - summary: {row.get('summary_auto', '')}",
                ]
            )
        )
    return "\n".join(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", help="Search terms. Space-separated terms are AND-like scoring terms.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX))
    parser.add_argument("--topic")
    parser.add_argument("--pattern")
    parser.add_argument("--year")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [row for row in load_rows(Path(args.index)) if matches_filters(row, args)]
    terms = [term for item in args.query for term in re.split(r"\s+", item) if term]
    if terms:
        scored = [(score(row, terms), row) for row in rows]
        rows = [row for value, row in sorted(scored, key=lambda item: (-item[0], item[1].get("date", "")), reverse=False) if value > 0]
    else:
        rows = sorted(rows, key=lambda row: (row.get("date", ""), row.get("id", 0)), reverse=True)
    rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
