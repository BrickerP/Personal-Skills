#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt >/tmp/gmail-ai-worker-install.log 2>&1 || {
  echo "Failed to install dependencies."
  echo "See /tmp/gmail-ai-worker-install.log for details."
  exit 1
}

python scripts/install_launchd_refresh.py
