#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPS_DIR="$SCRIPT_DIR/.cdp-deps"
MARKER="$DEPS_DIR/node_modules/chrome-remote-interface/package.json"

if [[ -f "$MARKER" ]]; then
  exit 0
fi

NODE="${NODE:-$(command -v node)}"
NPX="${NPX:-$(command -v npx)}"
if [[ -z "$NODE" ]]; then
  echo "cdp_ensure_deps: node not found on PATH" >&2
  exit 2
fi

mkdir -p "$DEPS_DIR"
(
  cd "$DEPS_DIR"
  "$NODE" -e "const fs=require('fs'); if(!fs.existsSync('package.json')) fs.writeFileSync('package.json', JSON.stringify({name:'chrome-read-write-cdp',private:true},null,2));"
  "$NPX" npm@10 i chrome-remote-interface@0.33.3 --silent --no-fund --no-audit
)

if [[ ! -f "$MARKER" ]]; then
  echo "cdp_ensure_deps: failed to install chrome-remote-interface under $DEPS_DIR" >&2
  exit 2
fi
