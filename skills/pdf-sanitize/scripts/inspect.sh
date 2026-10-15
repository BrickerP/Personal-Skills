#!/usr/bin/env bash
# Read-only PDF metadata and version-history report.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: inspect.sh file.pdf" >&2
  exit 1
fi

PDF="$1"
if [[ ! -f "$PDF" ]]; then
  echo "ERROR: not a file: $PDF" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/ensure-tools.sh" >/dev/null

echo "=== PDF Inspect Report ==="
echo "File: $PDF"
echo "Size: $(wc -c <"$PDF" | tr -d ' ') bytes"
if command -v shasum >/dev/null 2>&1; then
  echo "SHA256: $(shasum -a 256 "$PDF" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  echo "SHA256: $(sha256sum "$PDF" | awk '{print $1}')"
fi
echo

echo "--- qpdf check ---"
if qpdf --check "$PDF" >/dev/null 2>&1; then
  echo "Structure: OK (qpdf --check passed)"
else
  echo "Structure: WARN (qpdf --check reported issues; file may still be readable)"
  qpdf --check "$PDF" 2>&1 | head -20 || true
fi
echo

echo "--- Document info (exiftool) ---"
exiftool -a -G1 -s "$PDF" 2>/dev/null | grep -E '^\[.*\]' | grep -iE 'PDF|XMP|Author|Title|Subject|Keywords|Creator|Producer|CreateDate|ModifyDate|Create|Modify|Metadata|Trapped|Encryption' || exiftool -a -G1 -s "$PDF" | head -40
echo

echo "--- All metadata (compact) ---"
exiftool -s -s -s "$PDF" 2>/dev/null | head -60
total=$(exiftool "$PDF" 2>/dev/null | wc -l | tr -d ' ')
if (( total > 60 )); then
  echo "... ($total lines total; truncated)"
fi
echo

echo "--- Version history ---"
if command -v pdfresurrect >/dev/null 2>&1; then
  versions=$(pdfresurrect -q "$PDF" 2>/dev/null || echo "?")
  echo "pdfresurrect -q: $versions version(s)"
  if [[ "$versions" =~ ^[0-9]+$ ]] && (( versions > 1 )); then
    echo "NOTE: Multiple versions detected — incremental save history may contain old content."
  fi
else
  echo "pdfresurrect: not installed (optional). Install from https://github.com/enferex/pdfresurrect"
  echo "Sanitize pipeline uses qpdf rebuild to drop version history regardless."
fi
echo
echo "=== End Report ==="
