#!/usr/bin/env bash
# Select active tab in a Chrome window. Does NOT activate Chrome unless
# CHROME_SELECT_TAB_FOCUS=1 (so you can keep working in other apps).
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <window_id> <tab_index>" >&2
  exit 2
fi

window_id="$1"
tab_index="$2"

if [[ -n "${CHROME_SELECT_TAB_FOCUS:-}" ]]; then
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript \
    -e 'tell application "Google Chrome"' \
    -e "set active tab index of window id $window_id to $tab_index" \
    -e "set index of window id $window_id to 1" \
    -e 'activate' \
    -e "return (URL of active tab of window id $window_id) & \"\\n\" & (title of active tab of window id $window_id)" \
    -e 'end tell'
else
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript \
    -e 'tell application "Google Chrome"' \
    -e "set active tab index of window id $window_id to $tab_index" \
    -e "return (URL of active tab of window id $window_id) & \"\\n\" & (title of active tab of window id $window_id)" \
    -e 'end tell'
fi
