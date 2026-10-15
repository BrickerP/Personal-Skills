#!/usr/bin/env bash
# Install exiftool, qpdf, and Python deps if missing. Idempotent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
missing=()

require() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "OK: $1 ($("$1" --version 2>/dev/null | head -1 || "$1" -ver 2>/dev/null || echo present))"
  else
    missing+=("$1")
    echo "MISSING: $1"
  fi
}

ensure_python() {
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/ensure-python.sh"
  echo "OK: pymupdf (venv: $SCRIPT_DIR/../.venv)"
}

require exiftool
require qpdf

if ((${#missing[@]} == 0)); then
  ensure_python
  echo "All required tools present."
  exit 0
fi

echo "Installing: ${missing[*]}"

if [[ "$(uname -s)" == "Darwin" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew required to install: ${missing[*]}" >&2
    exit 1
  fi
  to_install=()
  for tool in "${missing[@]}"; do
    case "$tool" in
      exiftool) to_install+=(exiftool) ;;
      qpdf) to_install+=(qpdf) ;;
    esac
  done
  brew install "${to_install[@]}"
elif command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  pkgs=()
  for tool in "${missing[@]}"; do
    case "$tool" in
      exiftool) pkgs+=(libimage-exiftool-perl) ;;
      qpdf) pkgs+=(qpdf) ;;
    esac
  done
  sudo apt-get install -y "${pkgs[@]}"
else
  echo "ERROR: Unsupported OS. Install manually: ${missing[*]}" >&2
  exit 1
fi

require exiftool
require qpdf
ensure_python
echo "Install complete."
