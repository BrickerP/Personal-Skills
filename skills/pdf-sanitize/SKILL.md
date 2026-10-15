---
name: pdf-sanitize
description: >-
  Inspect PDF metadata and content structure, clone a PDF to a new file with
  layout-preserving text edits, and sanitize metadata/version history. Uses
  PyMuPDF, exiftool, and qpdf locally; never modifies the source file. Use when
  the user asks to clean PDF metadata, replicate a PDF with content changes,
  remove PDF version history, or produce PDF B from PDF A with the same layout.
---

# PDF Sanitize & Replicate

Produce a **new** PDF from source PDF A:

1. **Inspect** metadata + editable content structure
2. **Clone-edit** with layout-preserving text replacements (optional)
3. **Sanitize** metadata and drop incremental version history

**Never edit the source file.**

## Prerequisites

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/ensure-tools.sh
```

| Tool | Purpose |
|------|---------|
| `exiftool` | Metadata read/write |
| `qpdf` | Rebuild PDF, drop version history |
| `pymupdf` (Python) | Content analysis + in-place text replacement |
| `pillow` (Python, optional) | Visual diff verification |

## Capability matrix (be honest with the user)

| Scenario | Supported? |
|----------|------------|
| Same layout, change specific text strings | **Yes** — `clone-edit` / `replicate` |
| Inspect fonts, positions, page structure | **Yes** — `analyze-content` |
| Strip metadata + version history to new file | **Yes** — `sanitize` |
| Scanned PDF / text drawn as vectors (no text spans) | **No** — needs OCR or source document |
| Reflow paragraphs when new text is longer | **Partial** — auto-shrinks font slightly; may overflow |
| Edit text inside images | **No** |
| Preserve bookmarks, forms, hyperlinks | **No** — qpdf rebuild drops document-level features |
| Pixel-identical except edited regions | **Target** — verify with `--verify-visual` |

## Workflow

```
- [ ] Step 1: Inspect metadata + content (read-only)
- [ ] Step 2: Present findings; get approval + replacement list + metadata spec
- [ ] Step 3: replicate (or clone-edit + sanitize) → new output path
- [ ] Step 4: Verify output; confirm source unchanged
```

### Step 1 — Inspect

**Metadata:**

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/inspect.sh /path/to/A.pdf
```

**Content structure (fonts, spans, images, editability):**

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/analyze-content.sh /path/to/A.pdf
# JSON: analyze-content.sh --json /path/to/A.pdf
```

If `content_edit_supported: false`, warn the user before promising layout-preserving edits.

### Step 2 — Collect user spec

**Content replacements** (repeatable):

```json
[
  {"find": "DRAFT", "replace": "FINAL"},
  {"find": "Alice", "replace": "Bob", "pages": [0]}
]
```

Save as `replacements.json` or pass `--replace "old" "new"` on CLI.

**Metadata** (optional): `--author`, `--modify-date`, `--strip-all`, etc.

**Output path**: must differ from input (e.g. `B.pdf`).

### Step 3 — Replicate A → B (recommended one-shot)

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/replicate.sh \
  --input /path/to/A.pdf \
  --output /path/to/B.pdf \
  --replace "DRAFT" "FINAL" \
  --replace "2023" "2025" \
  --strip-all \
  --modify-date "2025:06:30 10:00:00"
```

Or JSON map:

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/replicate.sh \
  --input A.pdf --output B.pdf \
  --map replacements.json \
  --author "Acme Corp"
```

Pipeline:

1. **PyMuPDF clone-edit** — copy all pages; redact + reinsert text using original span font/size/color
2. **qpdf rebuild** — drop version history
3. **exiftool** — apply metadata to output only
4. **qpdf final pass** — drop ExifTool incremental patches

**Content-only** (no metadata pass):

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/clone-edit.sh \
  --input A.pdf --output B.staged.pdf \
  --replace "old" "new" --verify-visual
```

**Metadata-only** (no content changes):

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/sanitize.sh \
  --input A.pdf --output B.pdf --strip-all
```

### Step 4 — Verify

```bash
bash ~/.cursor/skills/pdf-sanitize/scripts/analyze-content.sh /path/to/B.pdf
bash ~/.cursor/skills/pdf-sanitize/scripts/inspect.sh /path/to/B.pdf
```

Confirm:

- Source SHA256/size unchanged
- `qpdf --check` passes on output
- Replaced strings appear in extracted text; find strings gone
- Metadata matches spec
- Optional: `--verify-visual` reports low pixel diff outside edited regions

## Safety rules

1. **Never** `-overwrite_original` on the user's source PDF.
2. **Never** `pdfresurrect -s` in-place; use qpdf rebuild.
3. Warn about scanned/outlined PDFs before content edits.
4. Embedded raster EXIF inside image streams is not stripped.

## Quick reference

```bash
# Self-test
bash ~/.cursor/skills/pdf-sanitize/scripts/dry-run.sh

# Analyze content
bash ~/.cursor/skills/pdf-sanitize/scripts/analyze-content.sh doc.pdf

# A → B with content + metadata
bash ~/.cursor/skills/pdf-sanitize/scripts/replicate.sh \
  --input A.pdf --output B.pdf \
  --replace "find" "replace" \
  --strip-all --modify-date "2025:06:30 10:00:00"
```
