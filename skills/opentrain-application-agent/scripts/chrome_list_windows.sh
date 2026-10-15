#!/usr/bin/env bash
# List Chrome windows (id + tab count), then every tab whose URL matches OpenTrain.
# Use the printed window=… with chrome_eval.sh / mass_apply.py --window …
set -euo pipefail

env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript -e 'tell application "Google Chrome"
set out to ""
repeat with w in windows
set wi to id of w
set out to out & "window=" & wi & " tabs=" & (count of tabs of w) & return
end repeat
return out
end tell' 2>&1

echo "--- opentrain tabs ---"
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript -e 'tell application "Google Chrome"
repeat with w in windows
set wi to id of w
set idx to 1
repeat with t in tabs of w
set u to URL of t
if u contains "app.opentrain.ai" or (title of t) contains "OpenTrain" then
log ("window=" & wi & " tab=" & idx & " title=" & (title of t) & " url=" & u)
end if
set idx to idx + 1
end repeat
end repeat
end tell' 2>&1 | sed 's/^[^:]*: //' | grep -E '^window=' || true
