#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <target_id>" >&2
  exit 2
fi

target_id="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=cdp_common.sh
source "$SCRIPT_DIR/cdp_common.sh"
cdp_require_browser

curl -sf -m 5 -X GET "${CHROME_CDP_BASE}/json/activate/${target_id}" >/dev/null

if [[ -n "${CHROME_SELECT_TAB_FOCUS:-}" ]]; then
  open -a "Google Chrome" --args --user-data-dir="$HOME/Library/Application Support/Google/Chrome-Debug" 2>/dev/null || true
fi

curl -sf -m 5 "${CHROME_CDP_BASE}/json/list" | node -e "
const id = process.argv[1];
const pages = JSON.parse(require('fs').readFileSync(0, 'utf8')).filter((t) => t.type === 'page');
const p = pages.find((t) => t.id === id);
if (!p) {
  console.error('target not found: ' + id);
  process.exit(2);
}
process.stdout.write(String(p.url || '') + '\\n' + String(p.title || ''));
" "$target_id"
