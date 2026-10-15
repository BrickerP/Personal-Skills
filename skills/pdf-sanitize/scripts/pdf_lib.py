#!/usr/bin/env python3
"""Shared PDF content helpers for pdf-sanitize skill."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:
    print(
        "ERROR: PyMuPDF not installed. Run: python3 -m pip install pymupdf",
        file=sys.stderr,
    )
    raise


@dataclass
class SpanInfo:
    page: int
    text: str
    font: str
    size: float
    color: int
    bbox: tuple[float, float, float, float]
    flags: int

    @property
    def baseline(self) -> tuple[float, float]:
        x0, _y0, _x1, y1 = self.bbox
        return (x0, y1)


def open_pdf(path: str | Path) -> fitz.Document:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"not a file: {p}")
    return fitz.open(p)


def iter_spans(page: fitz.Page, page_index: int) -> list[SpanInfo]:
    spans: list[SpanInfo] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                bbox = tuple(span.get("bbox", (0, 0, 0, 0)))
                spans.append(
                    SpanInfo(
                        page=page_index,
                        text=text,
                        font=str(span.get("font", "helv")),
                        size=float(span.get("size", 12)),
                        color=int(span.get("color", 0)),
                        bbox=bbox,  # type: ignore[arg-type]
                        flags=int(span.get("flags", 0)),
                    )
                )
    return spans


def span_for_rect(page: fitz.Page, page_index: int, rect: fitz.Rect) -> SpanInfo | None:
    best: SpanInfo | None = None
    best_area = 0.0
    for span in iter_spans(page, page_index):
        sb = fitz.Rect(span.bbox)
        inter = sb & rect
        if inter.is_empty:
            continue
        area = inter.get_area()
        if area > best_area:
            best_area = area
            best = span
    return best


def color_from_int(color: int) -> tuple[float, float, float]:
    r = ((color >> 16) & 255) / 255.0
    g = ((color >> 8) & 255) / 255.0
    b = (color & 255) / 255.0
    return (r, g, b)


def analyze_document(doc: fitz.Document) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    total_spans = 0
    total_images = 0
    total_drawings = 0

    for i, page in enumerate(doc):
        spans = iter_spans(page, i)
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        text_chars = sum(len(s.text) for s in spans)
        pages.append(
            {
                "index": i,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "rotation": page.rotation,
                "span_count": len(spans),
                "text_chars": text_chars,
                "image_count": len(images),
                "drawing_path_count": len(drawings),
                "spans_preview": [
                    {
                        "text": s.text[:120],
                        "font": s.font,
                        "size": s.size,
                        "bbox": [round(v, 2) for v in s.bbox],
                    }
                    for s in spans[:25]
                ],
                "editable_text": text_chars > 0,
                "likely_scanned_or_outlined": text_chars == 0
                and (len(images) > 0 or len(drawings) > 0),
            }
        )
        total_spans += len(spans)
        total_images += len(images)
        total_drawings += len(drawings)

    return {
        "page_count": doc.page_count,
        "metadata": dict(doc.metadata or {}),
        "total_spans": total_spans,
        "total_images": total_images,
        "total_drawings": total_drawings,
        "pages": pages,
        "content_edit_supported": total_spans > 0,
    }


def replace_text_on_page(
    page: fitz.Page,
    page_index: int,
    find: str,
    replace: str,
) -> int:
    if not find or find == replace:
        return 0

    count = 0
    spans = iter_spans(page, page_index)
    matching = [s for s in spans if find in s.text]

    # Pass 1: span-aware replacement (best layout fidelity)
    if matching:
        for span in matching:
            pad = fitz.Rect(span.bbox)
            pad = fitz.Rect(pad.x0 - 1, pad.y0 - 1, pad.x1 + 1, pad.y1 + 1)
            page.add_redact_annot(pad, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        for span in matching:
            new_text = span.text.replace(find, replace)
            baseline = span.baseline
            rgb = color_from_int(span.color)
            fontsize = span.size
            fontname = span.font
            rect = fitz.Rect(span.bbox)
            while fontsize > 4:
                try:
                    width = fitz.get_text_length(
                        new_text, fontname=fontname, fontsize=fontsize
                    )
                except (ValueError, RuntimeError):
                    fontname = "helv"
                    width = fitz.get_text_length(
                        new_text, fontname=fontname, fontsize=fontsize
                    )
                if width <= (rect.width + 6):
                    break
                fontsize *= 0.95
            try:
                page.insert_text(
                    baseline,
                    new_text,
                    fontname=fontname,
                    fontsize=fontsize,
                    color=rgb,
                    overlay=True,
                )
            except Exception:
                page.insert_text(
                    baseline,
                    new_text,
                    fontname="helv",
                    fontsize=fontsize,
                    color=rgb,
                    overlay=True,
                )
            count += 1
        return count

    # Pass 2: fallback to literal search regions
    rects = page.search_for(find)
    if not rects:
        return 0

    jobs: list[tuple[fitz.Rect, SpanInfo]] = []
    for rect in rects:
        span = span_for_rect(page, page_index, rect)
        if span is None:
            span = SpanInfo(
                page=page_index,
                text=find,
                font="helv",
                size=12.0,
                color=0,
                bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                flags=0,
            )
        jobs.append((rect, span))

    for rect, _span in jobs:
        pad = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)
        page.add_redact_annot(pad, fill=(1, 1, 1))

    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    for rect, span in jobs:
        baseline = span.baseline
        rgb = color_from_int(span.color)
        fontsize = span.size
        fontname = span.font

        while fontsize > 4:
            try:
                width = fitz.get_text_length(
                    replace, fontname=fontname, fontsize=fontsize
                )
            except (ValueError, RuntimeError):
                fontname = "helv"
                width = fitz.get_text_length(
                    replace, fontname=fontname, fontsize=fontsize
                )
            if width <= (rect.width + 4):
                break
            fontsize *= 0.95

        try:
            page.insert_text(
                baseline,
                replace,
                fontname=fontname,
                fontsize=fontsize,
                color=rgb,
                overlay=True,
            )
        except Exception:
            page.insert_text(
                baseline,
                replace,
                fontname="helv",
                fontsize=fontsize,
                color=rgb,
                overlay=True,
            )
        count += 1

    return count


def clone_with_replacements(
    input_path: str | Path,
    output_path: str | Path,
    replacements: list[dict[str, Any]],
) -> dict[str, Any]:
    src = open_pdf(input_path)
    doc = fitz.open()
    doc.insert_pdf(src)
    src.close()

    report: dict[str, Any] = {"replacements": [], "total_hits": 0}

    for item in replacements:
        find = str(item.get("find", ""))
        replace = str(item.get("replace", ""))
        pages = item.get("pages")
        if pages is None:
            page_range = range(doc.page_count)
        else:
            page_range = [int(p) for p in pages]

        hits = 0
        missing_pages: list[int] = []
        for page_index in page_range:
            if page_index < 0 or page_index >= doc.page_count:
                continue
            page = doc[page_index]
            n = replace_text_on_page(page, page_index, find, replace)
            hits += n
            if n == 0 and pages is not None:
                missing_pages.append(page_index)

        report["replacements"].append(
            {
                "find": find,
                "replace": replace,
                "hits": hits,
                "missing_pages": missing_pages,
            }
        )
        report["total_hits"] += hits

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(
        out,
        garbage=4,
        deflate=True,
        clean=True,
        pretty=False,
    )
    doc.close()

    return report


def render_page_png(doc: fitz.Document, page_index: int, dpi: int = 150) -> bytes:
    page = doc[page_index]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def visual_diff_ratio(png_a: bytes, png_b: bytes) -> float:
    try:
        from PIL import Image
        import io
    except ImportError:
        return -1.0

    img_a = Image.open(io.BytesIO(png_a)).convert("RGB")
    img_b = Image.open(io.BytesIO(png_b)).convert("RGB")
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size)

    diff_pixels = 0
    total = img_a.size[0] * img_a.size[1]
    pa = img_a.load()
    pb = img_b.load()
    for y in range(img_a.size[1]):
        for x in range(img_a.size[0]):
            if pa[x, y] != pb[x, y]:
                diff_pixels += 1
    return diff_pixels / total if total else 0.0


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
