#!/usr/bin/env bash
# Clone PDF A -> PDF B with text replacements; never modifies source.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/ensure-python.sh"

exec "$PDF_SANITIZE_PYTHON" "$SCRIPT_DIR/clone-edit.py" "$@"
