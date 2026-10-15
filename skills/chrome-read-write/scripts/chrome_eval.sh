#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <target_id> <js_file_or_inline_js>" >&2
  exit 2
fi

target_id="$1"
js_arg="$2"

tmp_js=""
if [[ -f "$js_arg" ]]; then
  js_file="$js_arg"
else
  tmp_js="$(mktemp "${TMPDIR:-/tmp}/chrome-eval.XXXXXX")"
  printf '%s' "$js_arg" >"$tmp_js"
  js_file="$tmp_js"
  cleanup() {
    [[ -n "$tmp_js" ]] && rm -f "$tmp_js"
  }
  trap cleanup EXIT
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=cdp_common.sh
source "$SCRIPT_DIR/cdp_common.sh"
cdp_require_browser
"$SCRIPT_DIR/cdp_ensure_deps.sh"

NODE_BIN="${NODE:-$(command -v node)}"
export NODE_PATH="$SCRIPT_DIR/.cdp-deps/node_modules${NODE_PATH:+:$NODE_PATH}"

exec "$NODE_BIN" "$SCRIPT_DIR/cdp_eval.cjs" "$target_id" "$js_file"
