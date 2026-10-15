#!/usr/bin/env bash
# Shared Chrome DevTools Protocol settings (Chrome-Debug on :9222).
CHROME_CDP_HOST="${CHROME_CDP_HOST:-127.0.0.1}"
CHROME_CDP_PORT="${CHROME_CDP_PORT:-9222}"
CHROME_CDP_BASE="http://${CHROME_CDP_HOST}:${CHROME_CDP_PORT}"

cdp_require_browser() {
  if ! curl -sf -m 2 "${CHROME_CDP_BASE}/json/version" >/dev/null; then
    if [[ -x "$HOME/bin/chrome-debug.sh" ]]; then
      "$HOME/bin/chrome-debug.sh" >/dev/null 2>&1 || true
    fi
  fi

  if ! curl -sf -m 2 "${CHROME_CDP_BASE}/json/version" >/dev/null; then
    echo "chrome CDP: no browser on ${CHROME_CDP_BASE}" >&2
    echo "  Run: ~/bin/chrome-debug.sh" >&2
    echo "  If Chrome-Debug is already running without CDP, quit only that Debug Chrome and retry." >&2
    echo "  Verify: curl -s ${CHROME_CDP_BASE}/json/version | head -c 120" >&2
    exit 4
  fi
}
