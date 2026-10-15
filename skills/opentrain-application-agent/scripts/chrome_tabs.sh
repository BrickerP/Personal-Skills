#!/usr/bin/env bash
set -euo pipefail

pattern="${1:-app.opentrain.ai}"

env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript -e 'tell application "Google Chrome" to repeat with w in windows
set wi to id of w
set idx to 1
repeat with t in tabs of w
log ("window=" & wi & " tab=" & idx & " title=" & (title of t) & " url=" & (URL of t))
set idx to idx + 1
end repeat
end repeat' 2>&1 \
  | sed 's/^[^:]*: //' \
  | grep -F "$pattern" || true
