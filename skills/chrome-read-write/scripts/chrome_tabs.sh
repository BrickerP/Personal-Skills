#!/usr/bin/env bash
set -euo pipefail

pattern="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=cdp_common.sh
source "$SCRIPT_DIR/cdp_common.sh"
cdp_require_browser

curl -sf -m 5 "${CHROME_CDP_BASE}/json/list" | node -e "
const pattern = process.argv[1] || '';
const pages = JSON.parse(require('fs').readFileSync(0, 'utf8')).filter((t) => t.type === 'page');
pages.forEach((p, i) => {
  const title = String(p.title || '').replace(/\\s+/g, ' ').trim();
  const url = String(p.url || '');
  const line = 'target=' + p.id + ' tab=' + (i + 1) + ' title=' + title + ' url=' + url;
  if (!pattern || title.includes(pattern) || url.includes(pattern)) {
    console.log(line);
  }
});
" "$pattern"
