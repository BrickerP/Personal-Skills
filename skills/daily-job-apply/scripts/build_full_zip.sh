#!/usr/bin/env bash
# Build FULL portable zip: daily-job-apply + chrome-read-write + job-search-orchestrator
set -euo pipefail

DATE="${1:-20260617}"
OUT_DIR="$HOME/job-hunt/exports"
STAGING="$OUT_DIR/.full-pack-staging-$$"
ZIP="$OUT_DIR/cookiy-job-apply-skill-FULL-${DATE}.zip"

rm -rf "$STAGING"
mkdir -p "$STAGING/skills"

SKILL_SRC="$HOME/.codex/skills/daily-job-apply"
for skill in daily-job-apply chrome-read-write job-search-orchestrator; do
  src="$HOME/.codex/skills/$skill"
  if [[ -d "$src" ]]; then
    rsync -a \
      --exclude '__pycache__' \
      --exclude '.DS_Store' \
      --exclude 'node_modules' \
      --exclude '_migrate_layout.py' \
      --exclude '_fix_migrated.py' \
      --exclude '_repatch_*.py' \
      --exclude 'data/profile.json' \
      --exclude 'data/ats-evolution-log.jsonl' \
      --exclude 'state/tracker.csv' \
      "$src/" "$STAGING/skills/$skill/"
  fi
done

# Ship empty tracker template + profile example
mkdir -p "$STAGING/skills/daily-job-apply/state"
echo "Date,Company,Role,JD_URL,Channel,Stage,Application_Submitted,Response_Status,Resume_Variant,Notes" \
  > "$STAGING/skills/daily-job-apply/state/tracker.csv"

cp "$SKILL_SRC/README-FOR-FRIENDS.md" "$STAGING/"
cp "$SKILL_SRC/INSTALL.md" "$STAGING/"

mkdir -p "$OUT_DIR"
rm -f "$ZIP"
(
  cd "$STAGING"
  zip -rq "$ZIP" .
)

rm -rf "$STAGING"
echo "Created: $ZIP"
ls -lh "$ZIP"
