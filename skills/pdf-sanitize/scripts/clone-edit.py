#!/usr/bin/env python3
"""Clone PDF to a new file with in-place text replacements, preserving layout/fonts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from pdf_lib import (  # noqa: E402
    clone_with_replacements,
    open_pdf,
    render_page_png,
    visual_diff_ratio,
)


def parse_replacements(args: argparse.Namespace) -> list[dict]:
    items: list[dict] = []

    if args.map_file:
        raw = json.loads(Path(args.map_file).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("replacements", [])
        if not isinstance(raw, list):
            raise ValueError("map file must be a JSON list or {replacements: [...]}")
        items.extend(raw)

    pairs = args.replace or []
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError("--replace requires find/replace pairs")
        items.append({"find": pair[0], "replace": pair[1]})

    if not items:
        raise ValueError("no replacements provided; use --replace or --map")

    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone PDF with content edits")
    parser.add_argument("--input", required=True, help="Source PDF (never modified)")
    parser.add_argument("--output", required=True, help="New output PDF path")
    parser.add_argument(
        "--replace",
        nargs=2,
        action="append",
        metavar=("FIND", "REPLACE"),
        help="Text replacement pair; repeatable",
    )
    parser.add_argument(
        "--map",
        dest="map_file",
        help="JSON file: [{find, replace, pages?}, ...]",
    )
    parser.add_argument(
        "--verify-visual",
        action="store_true",
        help="Render page 1 and report pixel diff vs source (needs Pillow)",
    )
    args = parser.parse_args()

    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()
    if inp == out:
        print("ERROR: output must differ from input", file=sys.stderr)
        return 1
    if not inp.is_file():
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 1

    replacements = parse_replacements(args)

    src_hash = inp.read_bytes()
    report = clone_with_replacements(inp, out, replacements)

    if inp.read_bytes() != src_hash:
        print("ERROR: source file was modified", file=sys.stderr)
        out.unlink(missing_ok=True)
        return 1

    print("=== Clone Edit Report ===")
    for item in report["replacements"]:
        status = "OK" if item["hits"] > 0 else "MISS"
        print(
            f"{status}: {item['find']!r} -> {item['replace']!r} "
            f"(hits={item['hits']})"
        )
    print(f"Total replacements applied: {report['total_hits']}")
    print(f"Wrote: {out} ({out.stat().st_size} bytes)")
    print("Source unchanged.")

    if args.verify_visual:
        before = open_pdf(inp)
        after = open_pdf(out)
        if before.page_count != after.page_count:
            print("WARN: page count changed", file=sys.stderr)
        png_a = render_page_png(before, 0)
        png_b = render_page_png(after, 0)
        ratio = visual_diff_ratio(png_a, png_b)
        before.close()
        after.close()
        if ratio < 0:
            print("Visual verify skipped (install Pillow: pip install pillow)")
        else:
            print(f"Visual diff page 1: {ratio * 100:.2f}% pixels changed")

    missing = [r for r in report["replacements"] if r["hits"] == 0]
    if missing:
        print("WARN: some find strings had zero hits", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
