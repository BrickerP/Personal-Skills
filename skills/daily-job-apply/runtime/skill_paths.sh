#!/usr/bin/env bash
# Source from any daily-job-apply bash script: source "$SKILL_ROOT/runtime/skill_paths.sh"
# Detects SKILL_ROOT from this file's location; loads optional ~/.config/daily-job-apply/env

if [[ -z "${SKILL_ROOT:-}" ]]; then
  _SP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SKILL_ROOT="$(cd "$_SP_DIR/.." && pwd)"
  unset _SP_DIR
fi

export SKILL_ROOT
export RUNTIME_ROOT="$SKILL_ROOT/runtime"
export ADAPTERS_DIR="$SKILL_ROOT/adapters"
export JOB_HUNT_DATA="$SKILL_ROOT/data"
export SCRIPTS_DIR="$SKILL_ROOT/scripts"
export STATE_DIR="$SKILL_ROOT/state"
export BIN_DIR="$SKILL_ROOT/bin"
export MANIFEST_PATH="$SKILL_ROOT/ROUND-MANIFEST.yaml"

_CONFIG_ENV="${HOME}/.config/daily-job-apply/env"
if [[ -f "$_CONFIG_ENV" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$_CONFIG_ENV"
  set +a
fi

export DAILY_JOB_APPLY_WORK_DIR="${DAILY_JOB_APPLY_WORK_DIR:-${HOME}/job-hunt}"
export WORK_DIR="$DAILY_JOB_APPLY_WORK_DIR"
export JOB_HUNT="$WORK_DIR"
export CANDIDATE_POOLS_DIR="$WORK_DIR/candidate-pools"

if [[ -n "${DAILY_JOB_APPLY_TRACKER:-}" ]]; then
  export TRACKER_CSV="$DAILY_JOB_APPLY_TRACKER"
elif [[ -f "$WORK_DIR/tracker.csv" ]] && [[ $(wc -l < "$WORK_DIR/tracker.csv" | tr -d ' ') -gt 1 ]] \
     && [[ ! -f "$STATE_DIR/tracker.csv" || $(wc -l < "$STATE_DIR/tracker.csv" | tr -d ' ') -le 1 ]]; then
  export TRACKER_CSV="$WORK_DIR/tracker.csv"
else
  export TRACKER_CSV="$STATE_DIR/tracker.csv"
fi

if [[ -z "${DAILY_JOB_APPLY_PDF_DIR:-}" ]]; then
  _PDF_DIR_FROM_PROFILE="$(
    python3 - "$JOB_HUNT_DATA/profile.json" <<'PY' 2>/dev/null
import json
import sys
from pathlib import Path

profile_path = Path(sys.argv[1])
if profile_path.exists():
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    resume_paths = profile.get("resume_paths") or {}
    for key in ("ai_agent_1p_en", "default_en", "default_1p_en", "ai_agent", "backend_platform", "general_swe"):
        value = resume_paths.get(key)
        if value:
            print(Path(value).expanduser().parent)
            break
PY
  )"
  export DAILY_JOB_APPLY_PDF_DIR="${_PDF_DIR_FROM_PROFILE:-${HOME}/Documents/resumes}"
  unset _PDF_DIR_FROM_PROFILE
fi
export PDF_DIR="$DAILY_JOB_APPLY_PDF_DIR"
export CHROME_PROFILE="${CHROME_PROFILE:-${CHROME_DEBUG_PROFILE_DIR:-Profile 2}}"
export GMAIL_PROFILE="${GMAIL_PROFILE:-$CHROME_PROFILE}"
export CHROME_USE_BIN="${CHROME_USE_BIN:-chrome-use}"
export NODE_PATH="${NODE_PATH:-$ADAPTERS_DIR/node_modules}"

mkdir -p "$STATE_DIR" "$CANDIDATE_POOLS_DIR" "$ADAPTERS_DIR"
