#!/bin/bash
# Chrome 148+ requires non-default user-data-dir for remote debugging.
# Parameterized profile via CHROME_PROFILE (default: Profile 2).
# macOS + Google Chrome required.

PROFILE="${CHROME_DEBUG_USER_DATA:-$HOME/Library/Application Support/Google/Chrome-Debug}"
PROFILE_DIR="${CHROME_PROFILE:-${CHROME_DEBUG_PROFILE_DIR:-Profile 2}}"

if pgrep -f "user-data-dir=$PROFILE" >/dev/null; then
  if curl -sf -m 1 http://localhost:9222/json/version >/dev/null; then
    exit 0
  fi
fi

if ! pgrep -f "user-data-dir=$PROFILE" >/dev/null; then
  rm -f "$PROFILE/SingletonLock" "$PROFILE/SingletonCookie" "$PROFILE/SingletonSocket"
fi

if [ "$#" -eq 0 ]; then
  set -- about:blank
fi

open -g -n -a "Google Chrome" --args \
  --user-data-dir="$PROFILE" \
  --profile-directory="$PROFILE_DIR" \
  --remote-debugging-port=9222 \
  '--remote-allow-origins=*' \
  --no-first-run \
  --no-default-browser-check \
  "$@"

for _ in {1..10}; do
  if curl -sf -m 1 http://localhost:9222/json/version >/dev/null; then
    exit 0
  fi
  sleep 1
done

echo "Chrome Debug started but CDP :9222 did not become ready" >&2
echo "Quit stale Chrome-Debug processes and retry: $0" >&2
exit 1
