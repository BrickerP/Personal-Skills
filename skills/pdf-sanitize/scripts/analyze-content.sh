#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/ensure-python.sh"
exec "$PDF_SANITIZE_PYTHON" "$SCRIPT_DIR/analyze-content.py" "$@"
