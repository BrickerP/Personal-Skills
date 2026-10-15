#!/usr/bin/env bash
# Single entry point for daily external ATS apply rounds.
# Reads active rounds from $SKILL_ROOT/ROUND-MANIFEST.yaml.
# Usage:
#   runtime/run-next.sh          # auto: GH when Ashby saturated, else Ashby batch
#   runtime/run-next.sh gh       # Greenhouse (manifest round)
#   runtime/run-next.sh ashby    # Ashby batch (manifest round, force)
#   runtime/run-next.sh manual   # ManualFinish retry queue
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skill_paths.sh
source "$_SCRIPT_DIR/skill_paths.sh"

MODE="${1:-auto}"

load_manifest() {
  python3 "$RUNTIME_ROOT/read_manifest.py"
}

count_exclude_known() {
  python3 - "$TRACKER_CSV" <<'PY'
import csv
import sys
from pathlib import Path

tracker = Path(sys.argv[1])
urls: set[str] = set()
if tracker.exists():
    for row in csv.DictReader(tracker.open(newline="", encoding="utf-8")):
        url = (row.get("JD_URL") or row.get("url") or "").strip().lower()
        if url:
            urls.add(url)
print(len(urls))
PY
}

latest_manual_queue() {
  python3 - "$CANDIDATE_POOLS_DIR" <<'PY'
import sys
from pathlib import Path

pool = Path(sys.argv[1])
candidates = sorted(pool.glob("manual-retry*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
print(candidates[0] if candidates else "")
PY
}

MANIFEST_JSON="$(load_manifest)"
SATURATION_THRESHOLD="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("saturation_threshold", 1500))' "$MANIFEST_JSON")"
ASHBY_SCRIPT="$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); print(m.get("ashby",{}).get("batch_script",""))' "$MANIFEST_JSON")"
GH_SCRIPT="$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); g=m.get("gh", m.get("greenhouse",{})); print(g.get("runner_script",""))' "$MANIFEST_JSON")"
MANUAL_SCRIPT="$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); print(m.get("manual",{}).get("runner_script",""))' "$MANIFEST_JSON")"
ASHBY_ROUND="$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); print(m.get("ashby",{}).get("active_round","?"))' "$MANIFEST_JSON")"
GH_ROUND="$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); g=m.get("gh", m.get("greenhouse",{})); print(g.get("active_round","?"))' "$MANIFEST_JSON")"

run_gh() {
  echo "[run-next] Greenhouse round${GH_ROUND} ($GH_SCRIPT)"
  exec python3 "$GH_SCRIPT"
}

run_ashby() {
  echo "[run-next] Ashby round${ASHBY_ROUND} ($ASHBY_SCRIPT)"
  exec bash "$ASHBY_SCRIPT"
}

run_manual() {
  queue="$(latest_manual_queue)"
  if [[ -z "$queue" || ! -f "$queue" ]]; then
    echo "[run-next] ERROR: no manual-retry queue CSV in $CANDIDATE_POOLS_DIR/" >&2
    exit 2
  fi
  echo "[run-next] ManualFinish retry queue=$queue ($MANUAL_SCRIPT)"
  exec python3 "$MANUAL_SCRIPT" --queue "$queue" --allow-manual-retry
}

case "$MODE" in
  gh|greenhouse)
    run_gh
    ;;
  ashby)
    run_ashby
    ;;
  manual|manualfinish)
    run_manual
    ;;
  auto|"")
    exclude_known="$(count_exclude_known)"
    echo "[run-next] exclude_known=$exclude_known (tracker URLs); saturation_threshold=$SATURATION_THRESHOLD"
    if [[ "$exclude_known" -gt "$SATURATION_THRESHOLD" ]]; then
      echo "[run-next] Ashby saturated (exclude_known > $SATURATION_THRESHOLD) -> GH round${GH_ROUND} first"
      run_gh
    else
      run_ashby
    fi
    ;;
  *)
    echo "Usage: $0 [auto|gh|ashby|manual]" >&2
    exit 2
    ;;
esac
