#!/usr/bin/env bash
# Print: "<window_id> <tab_index>" for a Google Chrome tab whose URL contains
# PATTERN (default app.opentrain.ai). Prefers the *active* tab of each window
# so we do not pick a stale background OpenTrain tab while the user is on
# Mercor/Gmail in the same window.
set -euo pipefail

PAT="${1:-app.opentrain.ai}"

out="$(
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_RESOLVE_PAT="$PAT" osascript \
    -e 'tell application "Google Chrome"' \
    -e 'set p to (system attribute "CHROME_RESOLVE_PAT")' \
    -e 'if p is "" then return "err"' \
    -e 'repeat with wi from 1 to (count windows)' \
    -e 'set w to window wi' \
    -e 'try' \
    -e 'set uact to URL of active tab of w' \
    -e 'if uact contains p then' \
    -e 'set wid to id of w' \
    -e 'repeat with ti from 1 to (count tabs of w)' \
    -e 'if (URL of tab ti of w) is uact then return (wid as text) & " " & (ti as text)' \
    -e 'end repeat' \
    -e 'end if' \
    -e 'end try' \
    -e 'end repeat' \
    -e 'repeat with wi from 1 to (count windows)' \
    -e 'set w to window wi' \
    -e 'set wid to id of w' \
    -e 'repeat with ti from 1 to (count tabs of w)' \
    -e 'if (URL of tab ti of w) contains p then return (wid as text) & " " & (ti as text)' \
    -e 'end repeat' \
    -e 'end repeat' \
    -e 'return ""' \
    -e 'end tell'
)"

if [[ "$out" == "err" ]]; then
  echo "chrome_resolve_opentrain: empty pattern" >&2
  exit 2
fi
if [[ -z "$out" ]]; then
  echo "chrome_resolve_opentrain: no tab with URL containing: $PAT" >&2
  exit 1
fi
echo "$out"
