#!/usr/bin/env bash
# Full replicate: content clone + metadata sanitize -> new output file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INPUT=""
OUTPUT=""
STAGE=""
SANITIZE_ARGS=()
CLONE_ARGS=()

usage() {
  cat <<'EOF'
Usage: replicate.sh --input A.pdf --output B.pdf [clone options] [sanitize options]

Clone options (passed to clone-edit.py):
  --replace FIND REPLACE   Repeatable text replacement pair
  --map FILE.json          JSON replacement map

Sanitize options (passed to sanitize.sh):
  --strip-all
  --author VAL  --title VAL  --subject VAL  --keywords VAL
  --creator VAL  --producer VAL
  --create-date VAL  --modify-date VAL

Example:
  replicate.sh --input report.pdf --output report.clean.pdf \
    --replace "Draft" "Final" --replace "2023" "2025" \
    --strip-all --modify-date "2025:06:30 10:00:00"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --replace) CLONE_ARGS+=("$1" "$2" "$3"); shift 3 ;;
    --map) CLONE_ARGS+=("$1" "$2"); shift 2 ;;
    --strip-all) SANITIZE_ARGS+=("$1"); shift ;;
    --author|--title|--subject|--keywords|--creator|--producer|--create-date|--modify-date)
      SANITIZE_ARGS+=("$1" "$2"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$INPUT" || -z "$OUTPUT" ]]; then
  echo "ERROR: --input and --output required" >&2
  usage
  exit 1
fi

if [[ "$INPUT" == "$OUTPUT" ]]; then
  echo "ERROR: output must differ from input" >&2
  exit 1
fi

WORKDIR=$(mktemp -d)
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

STAGE="$WORKDIR/staged.pdf"

echo "=== Phase 1: Content clone (layout-preserving text edits) ==="
bash "$SCRIPT_DIR/clone-edit.sh" --input "$INPUT" --output "$STAGE" "${CLONE_ARGS[@]}"

echo
echo "=== Phase 2: Sanitize metadata + drop version history ==="
if ((${#SANITIZE_ARGS[@]} == 0)); then
  SANITIZE_ARGS=(--strip-all)
fi
bash "$SCRIPT_DIR/sanitize.sh" --input "$STAGE" --output "$OUTPUT" "${SANITIZE_ARGS[@]}"

echo
echo "=== Done ==="
echo "Source unchanged: $INPUT"
echo "Output: $OUTPUT"
