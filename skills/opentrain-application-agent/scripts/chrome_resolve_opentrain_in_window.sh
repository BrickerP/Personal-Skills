#!/usr/bin/env bash
# Print: "<window_id> <tab_index>" for Google Chrome tabs in a FIXED window whose
# URL contains PATTERN (default app.opentrain.ai).
# Use when chrome_resolve_opentrain.sh picks the wrong window among several OpenTrain windows.
#
# Usage: chrome_resolve_opentrain_in_window.sh <window_id> [url_substring]

set -euo pipefail

if [[ ${1:-} == "" ]]; then
  echo "usage: $0 <chrome_window_id> [url_contains]" >&2
  exit 2
fi

WID_FIXED="$1"
PAT="${2:-app.opentrain.ai}"

out="$(
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_RESOLVE_PAT="$PAT" CHROME_WID_FIXED="$WID_FIXED" osascript \
    -e 'tell application "Google Chrome"' \
    -e 'set p to (system attribute "CHROME_RESOLVE_PAT")' \
    -e 'set want to (system attribute "CHROME_WID_FIXED")' \
    -e 'repeat with wi from 1 to (count windows)' \
    -e 'set w to window wi' \
    -e 'if (id of w) as text is want then' \
    -e 'try' \
    -e 'set uact to URL of active tab of w' \
    -e 'if uact contains p then' \
    -e 'set wid to id of w' \
    -e 'repeat with ti from 1 to (count tabs of w)' \
    -e 'if (URL of tab ti of w) is uact then return (wid as text) & " " & (ti as text)' \
    -e 'end repeat' \
    -e 'end if' \
    -e 'end try' \
    -e 'set wid to id of w' \
    -e 'repeat with ti from 1 to (count tabs of w)' \
    -e 'if (URL of tab ti of w) contains p then return (wid as text) & " " & (ti as text)' \
    -e 'end repeat' \
    -e 'return ""' \
    -e 'end if' \
    -e 'end repeat' \
    -e 'return ""' \
    -e 'end tell'
)"

if [[ -z "$out" ]]; then
  echo "chrome_resolve_opentrain_in_window: no tab with URL containing '$PAT' in window id $WID_FIXED" >&2
  exit 1
fi
echo "$out"
