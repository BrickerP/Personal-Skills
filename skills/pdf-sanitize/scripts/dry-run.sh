#!/usr/bin/env bash
# Self-test: metadata sanitize + layout-preserving content clone.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY=$(mktemp -d)
cleanup() { rm -rf "$DRY"; }
trap cleanup EXIT

echo "=== pdf-sanitize dry run ==="
bash "$SCRIPT_DIR/ensure-tools.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/ensure-python.sh"

"$PDF_SANITIZE_PYTHON" - <<PY
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "reportlab"])
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
from pathlib import Path
p = Path("$DRY/source.pdf")
c = canvas.Canvas(str(p), pagesize=letter)
c.setFont("Helvetica", 14)
c.drawString(72, 720, "Invoice #INV-2023-001")
c.setFont("Helvetica", 11)
c.drawString(72, 690, "Customer: Alice Example")
c.drawString(72, 670, "Amount: USD 1,250.00")
c.drawString(72, 640, "Status: DRAFT")
c.save()
print("Created test PDF")
PY

exiftool -Author="Old Author" -Title="Old Title" -ModifyDate="2020:01:01 00:00:00" \
  "$DRY/source.pdf" -overwrite_original >/dev/null

SRC_HASH=$(shasum -a 256 "$DRY/source.pdf" | awk '{print $1}')

echo
echo "--- Content analysis ---"
"$PDF_SANITIZE_PYTHON" "$SCRIPT_DIR/analyze-content.py" "$DRY/source.pdf"

echo
echo "--- Metadata inspect ---"
bash "$SCRIPT_DIR/inspect.sh" "$DRY/source.pdf" | sed -n '1,30p'

echo
echo "--- Content clone (layout-preserving replacements) ---"
"$PDF_SANITIZE_PYTHON" "$SCRIPT_DIR/clone-edit.py" \
  --input "$DRY/source.pdf" \
  --output "$DRY/cloned.pdf" \
  --replace "INV-2023-001" "INV-2025-999" \
  --replace "Alice Example" "Bob Sample" \
  --replace "DRAFT" "FINAL" \
  --verify-visual

echo
echo "--- Full replicate (clone + sanitize metadata) ---"
bash "$SCRIPT_DIR/replicate.sh" \
  --input "$DRY/source.pdf" \
  --output "$DRY/final.pdf" \
  --replace "USD 1,250.00" "USD 999.00" \
  --author "Dry Run Corp" \
  --modify-date "2025:06:30 12:00:00"

AFTER_HASH=$(shasum -a 256 "$DRY/source.pdf" | awk '{print $1}')
if [[ "$SRC_HASH" != "$AFTER_HASH" ]]; then
  echo "FAIL: source file was modified" >&2
  exit 1
fi

TEXT=$("$PDF_SANITIZE_PYTHON" - <<PY
import fitz
doc = fitz.open("$DRY/final.pdf")
print(doc[0].get_text())
doc.close()
PY
)

echo "Extracted text from final.pdf:"
echo "$TEXT"

echo "$TEXT" | grep -q "USD 999.00" || { echo "FAIL: replaced amount missing"; exit 1; }
echo "$TEXT" | grep -q "DRAFT" || { echo "FAIL: unchanged DRAFT label missing"; exit 1; }

CLONED=$("$PDF_SANITIZE_PYTHON" - <<PY
import fitz
doc = fitz.open("$DRY/cloned.pdf")
print(doc[0].get_text())
doc.close()
PY
)
echo "$CLONED" | grep -q "FINAL" || { echo "FAIL: clone-edit did not replace DRAFT"; exit 1; }
echo "$CLONED" | grep -q "Bob Sample" || { echo "FAIL: clone-edit customer replace failed"; exit 1; }

AUTHOR=$(exiftool -s -s -s -Author "$DRY/final.pdf")
[[ "$AUTHOR" == "Dry Run Corp" ]] || { echo "FAIL: Author=$AUTHOR"; exit 1; }

qpdf --check "$DRY/final.pdf" >/dev/null

echo
echo "PASS: dry run OK (content clone + metadata sanitize)"
echo "Skill path: $SKILL_DIR"
