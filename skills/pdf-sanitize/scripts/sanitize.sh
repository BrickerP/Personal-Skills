#!/usr/bin/env bash
# Rebuild PDF to a NEW file: drop version history, apply metadata. Never touch source.
set -euo pipefail

INPUT=""
OUTPUT=""
STRIP_ALL=0
declare -a EXIF_ARGS=()

usage() {
  cat <<'EOF'
Usage: sanitize.sh --input SOURCE.pdf --output OUT.pdf [options]

Options:
  --strip-all              Remove all metadata on output
  --author VAL             -Author=
  --title VAL              -Title=
  --subject VAL            -Subject=
  --keywords VAL           -Keywords=
  --creator VAL            -Creator=
  --producer VAL           -Producer=
  --create-date VAL        -CreateDate=  (YYYY:MM:DD HH:MM:SS)
  --modify-date VAL        -ModifyDate=

Source file is never modified. Temporary files use mktemp and are removed on exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --strip-all) STRIP_ALL=1; shift ;;
    --author) EXIF_ARGS+=("-Author=$2"); shift 2 ;;
    --title) EXIF_ARGS+=("-Title=$2"); shift 2 ;;
    --subject) EXIF_ARGS+=("-Subject=$2"); shift 2 ;;
    --keywords) EXIF_ARGS+=("-Keywords=$2"); shift 2 ;;
    --creator) EXIF_ARGS+=("-Creator=$2"); shift 2 ;;
    --producer) EXIF_ARGS+=("-Producer=$2"); shift 2 ;;
    --create-date) EXIF_ARGS+=("-CreateDate=$2"); shift 2 ;;
    --modify-date) EXIF_ARGS+=("-ModifyDate=$2"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$INPUT" || -z "$OUTPUT" ]]; then
  echo "ERROR: --input and --output are required" >&2
  usage
  exit 1
fi

if [[ ! -f "$INPUT" ]]; then
  echo "ERROR: input not found: $INPUT" >&2
  exit 1
fi

if [[ "$INPUT" == "$OUTPUT" ]]; then
  echo "ERROR: output must differ from input (never overwrite source)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/ensure-tools.sh" >/dev/null

SOURCE_HASH=""
if command -v shasum >/dev/null 2>&1; then
  SOURCE_HASH=$(shasum -a 256 "$INPUT" | awk '{print $1}')
elif command -v sha256sum >/dev/null 2>&1; then
  SOURCE_HASH=$(sha256sum "$INPUT" | awk '{print $1}')
fi
SOURCE_SIZE=$(wc -c <"$INPUT" | tr -d ' ')

WORKDIR=$(mktemp -d)
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

REBUILT="$WORKDIR/rebuilt.pdf"
META="$WORKDIR/with_meta.pdf"

echo "Step 1/3: Rebuild pages (drop version history)..."
qpdf --empty --pages "$INPUT" 1-z -- "$REBUILT"

echo "Step 2/3: Apply metadata..."
if (( STRIP_ALL == 1 )); then
  if ((${#EXIF_ARGS[@]} > 0)); then
    exiftool -all:all= "${EXIF_ARGS[@]}" "$REBUILT" -o "$META"
  else
    exiftool -all:all= "$REBUILT" -o "$META"
  fi
elif ((${#EXIF_ARGS[@]} > 0)); then
  exiftool -all:all= "${EXIF_ARGS[@]}" "$REBUILT" -o "$META"
else
  exiftool -all:all= "$REBUILT" -o "$META"
fi

exiftool -XMPToolkit= "$META" -o "$WORKDIR/meta_clean.pdf"
META="$WORKDIR/meta_clean.pdf"

echo "Step 3/3: Final qpdf pass (drop ExifTool incremental data)..."
mkdir -p "$(dirname "$OUTPUT")"
qpdf "$META" "$OUTPUT"

if [[ -n "$SOURCE_HASH" ]]; then
  AFTER_HASH=$(shasum -a 256 "$INPUT" 2>/dev/null | awk '{print $1}' || sha256sum "$INPUT" | awk '{print $1}')
  AFTER_SIZE=$(wc -c <"$INPUT" | tr -d ' ')
  if [[ "$SOURCE_HASH" != "$AFTER_HASH" || "$SOURCE_SIZE" != "$AFTER_SIZE" ]]; then
    echo "ERROR: source file changed — aborting trust in output" >&2
    rm -f "$OUTPUT"
    exit 1
  fi
  echo "Source unchanged: SHA256=$SOURCE_HASH"
fi

if ! qpdf --check "$OUTPUT" >/dev/null 2>&1; then
  echo "ERROR: output failed qpdf --check" >&2
  exit 1
fi

echo "Wrote: $OUTPUT ($(wc -c <"$OUTPUT" | tr -d ' ') bytes)"
echo "Run inspect.sh on output to verify metadata."
