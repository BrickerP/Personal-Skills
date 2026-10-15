#!/usr/bin/env bash
# Restore a Chrome window to bounds saved before first conceal (Chrome bounds).
set -euo pipefail
wid="${1:?window_id}"
cache="/tmp/opentrain_chrome_bounds_${wid}.txt"
if [[ ! -f "$cache" ]]; then
  echo "no saved bounds at $cache" >&2
  exit 1
fi
IFS=',' read -r l t r b <<< "$(head -1 "$cache" | tr -d ' ')"
exec env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" CHROME_L="$l" CHROME_T="$t" CHROME_R="$r" CHROME_B="$b" osascript \
  -e 'tell application "Google Chrome"' \
  -e 'set widStr to system attribute "CHROME_WID"' \
  -e 'set l to (system attribute "CHROME_L") as number' \
  -e 'set t to (system attribute "CHROME_T") as number' \
  -e 'set r to (system attribute "CHROME_R") as number' \
  -e 'set b to (system attribute "CHROME_B") as number' \
  -e 'repeat with i from 1 to (count windows)' \
  -e 'set ww to window i' \
  -e 'if (id of ww) as text is widStr then' \
  -e 'set bounds of ww to {l, t, r, b}' \
  -e 'exit repeat' \
  -e 'end if' \
  -e 'end repeat' \
  -e 'end tell'
