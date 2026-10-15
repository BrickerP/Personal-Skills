#!/usr/bin/env python3
"""Analyze PDF content structure for format-aware editing."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from pdf_lib import analyze_document, dump_json, open_pdf  # noqa: E402


def human_report(data: dict) -> str:
    lines = [
        "=== PDF Content Analysis ===",
        f"Pages: {data['page_count']}",
        f"Editable text spans: {data['total_spans']}",
        f"Images: {data['total_images']}",
        f"Vector drawing paths: {data['total_drawings']}",
        f"Content edit supported: {'YES' if data['content_edit_supported'] else 'NO (likely scanned/outlined)'}",
        "",
    ]

    if data.get("metadata"):
        lines.append("--- Document metadata (PyMuPDF) ---")
        for k, v in data["metadata"].items():
            if v:
                lines.append(f"{k}: {v}")
        lines.append("")

    for page in data["pages"]:
        lines.append(
            f"--- Page {page['index'] + 1} ({page['width']} x {page['height']} pt) ---"
        )
        lines.append(
            f"spans={page['span_count']} chars={page['text_chars']} "
            f"images={page['image_count']} drawings={page['drawing_path_count']}"
        )
        if page["likely_scanned_or_outlined"]:
            lines.append("WARN: no editable text; clone-edit may not preserve layout for text changes")
        for span in page["spans_preview"][:10]:
            preview = span["text"].replace("\n", " ")
            lines.append(
                f"  [{span['font']} {span['size']}pt] {preview[:80]}"
            )
        if page["span_count"] > 10:
            lines.append(f"  ... {page['span_count'] - 10} more spans")
        lines.append("")

    lines.append("=== End Content Analysis ===")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze PDF content structure")
    parser.add_argument("pdf", help="Input PDF path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    doc = open_pdf(args.pdf)
    data = analyze_document(doc)
    doc.close()

    if args.json:
        print(dump_json(data))
    else:
        print(human_report(data))
        print()
        print("(Full machine-readable report: analyze-content.py --json ...)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
