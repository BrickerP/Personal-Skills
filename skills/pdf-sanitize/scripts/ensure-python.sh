#!/usr/bin/env bash
# Resolve Python + venv for pdf-sanitize scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/../.venv"

ensure_venv() {
  if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install -q --upgrade pip
  python -m pip install -q pymupdf pillow reportlab
}

ensure_venv
export PDF_SANITIZE_PYTHON="$VENV/bin/python"
