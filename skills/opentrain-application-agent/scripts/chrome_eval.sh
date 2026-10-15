#!/usr/bin/env bash
# Run JavaScript in a specific Chrome window/tab via AppleScript.
#
# Target Chrome windows by matching (id of window i) as text — large numeric
# window ids break "window id 1745…" in AppleScript (IEEE float / -10006).
#
# By default this does NOT call `activate` or reorder windows. Use
# CHROME_EVAL_ACTIVATE=1 to raise Chrome.
#
# Conceal: restore saved bounds before each JS (Chrome occludes off-screen
# tabs), then move off-screen after. Cache: /tmp/opentrain_chrome_bounds_<id>.txt
# CHROME_EVAL_CONCEAL=0 disables conceal.
set -euo pipefail

if [[ $# -ne 2 && $# -ne 3 ]]; then
  echo "usage: $0 <window_id> <js_file> [tab_index]" >&2
  exit 2
fi

window_id="$1"
js_file="$2"
tab_index="${3:-}"

if [[ ! -f "$js_file" ]]; then
  echo "js file not found: $js_file" >&2
  exit 2
fi

raise_if_requested() {
  local wid="$1"
  [[ -n "${CHROME_EVAL_ACTIVATE:-}" ]] || return 0
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" osascript \
    -e 'tell application "Google Chrome" to activate' \
    -e 'tell application "Google Chrome"' \
    -e 'set widStr to system attribute "CHROME_WID"' \
    -e 'repeat with i from 1 to (count windows)' \
    -e 'set w to window i' \
    -e 'if (id of w) as text is widStr then' \
    -e 'set index of w to 1' \
    -e 'exit repeat' \
    -e 'end if' \
    -e 'end repeat' \
    -e 'end tell'
}

chrome_window_index_for_id() {
  local wid="$1"
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" osascript \
    -e 'tell application "Google Chrome"' \
    -e 'set widStr to system attribute "CHROME_WID"' \
    -e 'repeat with i from 1 to (count windows)' \
    -e 'if (id of window i) as text is widStr then return i as text' \
    -e 'end repeat' \
    -e 'return "0"' \
    -e 'end tell'
}

# Restore on-screen layout before JS so Chrome paints the tab (occlusion fix).
restore_before_js_if_needed() {
  local wid="$1"
  case "${CHROME_EVAL_CONCEAL:-}" in
    0 | false | no | off | "") return 0 ;;
  esac
  local cache="/tmp/opentrain_chrome_bounds_${wid}.txt"
  [[ -f "$cache" ]] || return 0
  local l t r b
  IFS=',' read -r l t r b <<< "$(head -1 "$cache" | tr -d ' ')"
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" CHROME_L="$l" CHROME_T="$t" CHROME_R="$r" CHROME_B="$b" osascript \
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
    -e 'end tell' 2>/dev/null || true
  sleep 0.5
}

# Save Chrome bounds once, then move window off-screen via System Events.
conceal_after_js_if_requested() {
  local wid="$1"
  case "${CHROME_EVAL_CONCEAL:-}" in
    0 | false | no | off | "") return 0 ;;
  esac

  local idx cache bb
  cache="/tmp/opentrain_chrome_bounds_${wid}.txt"
  if [[ ! -f "$cache" ]]; then
    bb="$(
      env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" osascript \
        -e 'tell application "Google Chrome"' \
        -e 'set widStr to system attribute "CHROME_WID"' \
        -e 'repeat with i from 1 to (count windows)' \
        -e 'set ww to window i' \
        -e 'if (id of ww) as text is widStr then' \
        -e 'set {l, t, r, b} to bounds of ww' \
        -e 'return (l as text) & ", " & (t as text) & ", " & (r as text) & ", " & (b as text)' \
        -e 'end if' \
        -e 'end repeat' \
        -e 'return ""' \
        -e 'end tell' 2>/dev/null || true
    )"
    [[ -n "$bb" ]] && printf '%s\n' "$bb" > "$cache"
  fi

  idx="$(chrome_window_index_for_id "$wid")"
  if [[ "$idx" == "0" ]]; then
    echo "chrome_eval: conceal skipped — window id $wid not found" >&2
    return 0
  fi

  if ! env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin osascript \
    -e 'tell application "System Events"' \
    -e "tell process \"Google Chrome\"" \
    -e "set s to size of window $idx" \
    -e "set position of window $idx to {-3600, 60}" \
    -e "set size of window $idx to s" \
    -e 'end tell' \
    -e 'end tell' 2>/dev/null; then
    echo "chrome_eval: conceal move failed (try Accessibility for System Events → Chrome)" >&2
  fi
}

verify_chrome_target_url() {
  local wid="$1"
  [[ -n "${CHROME_EVAL_URL_MUST_CONTAIN:-}" ]] || return 0
  local url=""
  local a
  for a in 1 2 3 4 5; do
    url="$(
      env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$wid" osascript \
        -e 'tell application "Google Chrome"' \
        -e 'set widStr to system attribute "CHROME_WID"' \
        -e 'repeat with i from 1 to (count windows)' \
        -e 'set ww to window i' \
        -e 'if (id of ww) as text is widStr then return URL of active tab of ww' \
        -e 'end repeat' \
        -e 'return ""' \
        -e 'end tell' 2>/dev/null || true
    )"
    [[ -n "$url" ]] && break
    sleep 1
  done
  if [[ -z "$url" ]]; then
    echo "chrome_eval: cannot read URL for window id $wid (wrong id or Chrome unavailable)" >&2
    exit 3
  fi
  if [[ "$url" != *"$CHROME_EVAL_URL_MUST_CONTAIN"* ]]; then
    echo "chrome_eval: refusing JS: window $wid tab URL must contain '${CHROME_EVAL_URL_MUST_CONTAIN}', got: $url" >&2
    exit 3
  fi
}

run_js_in_window() {
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$window_id" osascript \
    -e "set jsPath to \"$js_file\"" \
    -e 'set jsText to do shell script "cat " & quoted form of jsPath' \
    -e 'tell application "Google Chrome"' \
    -e 'set widStr to system attribute "CHROME_WID"' \
    -e 'repeat with i from 1 to (count windows)' \
    -e 'set ww to window i' \
    -e 'if (id of ww) as text is widStr then return execute active tab of ww javascript jsText' \
    -e 'end repeat' \
    -e 'end tell'
}

if [[ -n "$tab_index" ]]; then
  raise_if_requested "$window_id"
  restore_before_js_if_needed "$window_id"
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin CHROME_WID="$window_id" CHROME_TAB="$tab_index" osascript \
    -e 'tell application "Google Chrome"' \
    -e 'set widStr to system attribute "CHROME_WID"' \
    -e 'set tabN to (system attribute "CHROME_TAB") as integer' \
    -e 'repeat with i from 1 to (count windows)' \
    -e 'set ww to window i' \
    -e 'if (id of ww) as text is widStr then' \
    -e 'set active tab index of ww to tabN' \
    -e 'exit repeat' \
    -e 'end if' \
    -e 'end repeat' \
    -e 'end tell'
  verify_chrome_target_url "$window_id"
  run_js_in_window
  conceal_after_js_if_requested "$window_id"
else
  raise_if_requested "$window_id"
  restore_before_js_if_needed "$window_id"
  verify_chrome_target_url "$window_id"
  run_js_in_window
  conceal_after_js_if_requested "$window_id"
fi
