#!/usr/bin/env bash
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_SCRIPT_DIR/../skill_paths.sh"

# Round 110: dict200 batch-BR + gh10 + repos@1500 + probe-first + aggressive metadata (no-title-filter ALL verified slugs).
# submitted_before_today=24 (round110 start from r108 end verified=582).
# Never abort on mine=0 — always run ALL gh slices (novel Ashby GH queries rotate@110) + repos@1500.
# Only abort if pool=0 after ALL supply stages.
# GH rotate@110 slice1 R105 remote SWE; slice2 R106 staff engineer; slice3 R107 AI engineer.
# SKIP primeintellect langdock kiso-technology + R107 stars.
# Apply max 25, same-slug max 3, min-success-gap=180. Single-instance flock + lockdir.
set -euo pipefail

LOG=$WORK_DIR/round110.log
DATE=$(TZ=Asia/Shanghai date +%Y-%m-%d)
POOL_DIR=$WORK_DIR/candidate-pools
NEW_SLUGS="$POOL_DIR/ashby-round110-new-slugs.txt"
FILTERED_SLUGS="$POOL_DIR/ashby-round110-new-slugs-filtered.txt"
FORM_HIT_SLUGS="$POOL_DIR/ashby-round110-form-hit-slugs.txt"
PROBE_CSV="$POOL_DIR/ashby-round110-probe-${DATE}.csv"
SOURCED="$POOL_DIR/ashby-round110-sourced-${DATE}.csv"
GATE_JSON="$POOL_DIR/ashby-round110-gate-${DATE}.json"
MERGED="$POOL_DIR/ashby-round110-pool-${DATE}.csv"
DEDUPED="$POOL_DIR/ashby-round110-deduped-${DATE}.csv"
MINE_JSON="$POOL_DIR/ashby-round110-mine-result.json"
SAVED_NEW_SLUGS="$POOL_DIR/ashby-round110-new-slugs-saved.txt"
SAVED_DEDUPED="$POOL_DIR/ashby-round110-deduped-saved.csv"
USE_SAVED_DEDUPED=0
OMX=$ADAPTERS_DIR
DEDUPE=$SKILL_ROOT/scripts/job_dedupe_check.py
BATCH="$OMX/ashby_apply_batch.py"
DEDUPE_POOL="$OMX/ashby_pool_dedupe.py"
MINE=$WORK_DIR/scripts/ashby_mine_round110_sources.py
REPO_MINE=$WORK_DIR/scripts/ashby_mine_github_repos.py
PROBE_HELPER=$WORK_DIR/scripts/ashby_form_probe_gate.py
PROBE_FIRST_GATE=$WORK_DIR/scripts/round80_probe_first_gate.py
PROBE_MISS_SLUGS="$POOL_DIR/ashby-round110-probe-miss-slugs.txt"
SOURCED_NOTITLE="$POOL_DIR/ashby-round110-sourced-notitle-${DATE}.csv"

MAX_ATTEMPTS=25
MAX_POSTINGS=1000
PROBE_POSTINGS=40
EXCLUDE_SLUGS="beacons numeric parspec"
STAR_SLUGS="fonoa amo aptura Lido.fi modus hanover-park nectar-social nelo homevision Perk americanoperator amplo"
ASHBY_SKIP_SLUGS_JSON="$SKILL_ROOT/data/ashby-skip-slugs.json"
METADATA_ONLY_FALLBACK=0
SOURCE_PATH="probe"
MINE_SOURCE="dict"

LOCKDIR=$WORK_DIR/.round110-batch.lockdir
APPLY_LOCKDIR=$WORK_DIR/.ashby-apply.lockdir
if LOCKDIR="$LOCKDIR" python3 - <<'PY'
import os, sys
from pathlib import Path
lock = Path(os.environ["LOCKDIR"])
lock.mkdir(exist_ok=False)
(lock / "pid").write_text(str(os.getpid()))
PY
then
  :
else
  OLD_PID=$(cat "$LOCKDIR/pid" 2>/dev/null || echo "")
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[ROUND110 ABORT] another round110-batch running pid=$OLD_PID holds $LOCKDIR" | tee -a "$LOG"
    exit 1
  fi
  rm -rf "$LOCKDIR"
  if ! LOCKDIR="$LOCKDIR" python3 - <<'PY'
import os
from pathlib import Path
lock = Path(os.environ["LOCKDIR"])
lock.mkdir(exist_ok=False)
(lock / "pid").write_text(str(os.getpid()))
PY
  then
    echo "[ROUND110 ABORT] could not acquire $LOCKDIR after stale cleanup" | tee -a "$LOG"
    exit 1
  fi
fi
if [[ -d "$APPLY_LOCKDIR" ]]; then
  APPLY_PID=$(cat "$APPLY_LOCKDIR/pid" 2>/dev/null || echo "")
  if [[ -n "$APPLY_PID" ]] && kill -0 "$APPLY_PID" 2>/dev/null; then
    echo "[ROUND110 ABORT] concurrent Chrome apply running pid=$APPLY_PID holds $APPLY_LOCKDIR" | tee -a "$LOG"
    rm -rf "$LOCKDIR" 2>/dev/null || true
    exit 1
  fi
  rm -rf "$APPLY_LOCKDIR" 2>/dev/null || true
fi
if ! mkdir "$APPLY_LOCKDIR" 2>/dev/null; then
  echo "[ROUND110 ABORT] concurrent Chrome apply blocked — $APPLY_LOCKDIR held" | tee -a "$LOG"
  rm -rf "$LOCKDIR" 2>/dev/null || true
  exit 1
fi
echo $$ > "$APPLY_LOCKDIR/pid"

GLOBAL_LOCK=$WORK_DIR/.round110-global.lock
OTHER_PIDS=$(pgrep -f "round110-batch\\.sh" 2>/dev/null | grep -v "^$$$" || true)
if [[ -n "$OTHER_PIDS" ]]; then
  for op in $OTHER_PIDS; do
    if [[ "$op" != "$$" ]] && kill -0 "$op" 2>/dev/null; then
      echo "[ROUND110 ABORT] another round110-batch.sh pid=$op running" | tee -a "$LOG"
      rm -rf "$LOCKDIR" 2>/dev/null || true
      rm -rf "$APPLY_LOCKDIR" 2>/dev/null || true
      exit 1
    fi
  done
fi

if [[ -f "$GLOBAL_LOCK" ]]; then
  GLPID=$(cat "$GLOBAL_LOCK" 2>/dev/null || echo "")
  if [[ -n "$GLPID" ]] && kill -0 "$GLPID" 2>/dev/null; then
    echo "[ROUND110 ABORT] global lock held by pid=$GLPID ($GLOBAL_LOCK)" | tee -a "$LOG"
    exit 1
  fi
  rm -f "$GLOBAL_LOCK"
fi
echo $$ > "$GLOBAL_LOCK"
trap 'rm -f "$GLOBAL_LOCK" 2>/dev/null || true; rm -rf "$APPLY_LOCKDIR" 2>/dev/null || true; rm -rf "$LOCKDIR" 2>/dev/null || true' EXIT


count_submitted() {
  python3 - <<PY
import csv
from pathlib import Path
date = "$DATE"
rows=list(csv.DictReader(Path.home().joinpath('job-hunt/tracker.csv').open()))
print(sum(1 for r in rows if (r.get('Date') or '').startswith(date) and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted')))
PY
}

count_verified() {
  python3 - <<PY
import csv
from pathlib import Path
rows=list(csv.DictReader(Path.home().joinpath('job-hunt/tracker.csv').open()))
c12=sum(1 for r in rows if (r.get('Date') or '').startswith('2026-06-12') and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted'))
c13=sum(1 for r in rows if (r.get('Date') or '').startswith('2026-06-13') and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted'))
c14=sum(1 for r in rows if (r.get('Date') or '').startswith('2026-06-14') and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted'))
c15=sum(1 for r in rows if (r.get('Date') or '').startswith('2026-06-15') and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted'))
c16=sum(1 for r in rows if (r.get('Date') or '').startswith('2026-06-16') and r.get('Application_Submitted')=='Yes' and r.get('Response_Status') in ('Submitted','DuplicateSubmitted'))
print(f"{c12}+{c13}+{c14}+{c15}+{c16}={c12+c13+c14+c15+c16}")
PY
}

auto_count() {
  python3 - <<PY
import csv
from pathlib import Path
p=Path("$1")
rows=[r for r in csv.DictReader(p.open()) if r.get('status')=='auto_candidate'] if p.exists() and p.stat().st_size>0 else []
print(len(rows))
PY
}

count_lines() {
  python3 - <<PY
from pathlib import Path
p=Path("$1")
if not p.exists():
    print(0)
else:
    print(sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")))
PY
}

yield_abort() {
  local blocker="$1"
  python3 - <<PY | tee -a "$LOG"
import json
from pathlib import Path
ns = Path("$NEW_SLUGS")
slugs = [l.strip() for l in ns.read_text().splitlines() if l.strip() and not l.startswith("#")] if ns.exists() else []
mine = json.loads(Path("$MINE_JSON").read_text()) if Path("$MINE_JSON").exists() else {}
before = $(count_submitted)
verified = "$(count_verified)"
print("=== yield summary ===")
print(f"round110 pool_auto=0 max_attempts=0 exclude_slugs=$EXCLUDE_SLUGS")
print(f"round110 apply_attempts=0 yield=0/0")
print(f"round110 delta_today=+0 ({before}->{before})")
print(f"round110 verified={verified} (baseline 582 -> +0)")
print(f"round110 probe_fix=classify_form(detail['posting']) confirmed in $PROBE_HELPER")
print(f"round110 gate_dual=0 gate_metadata_only=0 source_path=$SOURCE_PATH metadata_fallback=$METADATA_ONLY_FALLBACK")
print(f"round110 mine_source=$MINE_SOURCE mine_new_slug_count={mine.get('new_slug_count', mine.get('verified', 0))} posting_api_verified={mine.get('repo_hits', {}).get('posting_api_verified', 0)}")
print(f"round110 new_slugs={','.join(slugs[:80])}")
print(f"round110 blocker=$blocker")
PY
  echo "=== round110 end $(TZ=Asia/Shanghai date) verified=$(count_verified) ===" | tee -a "$LOG"
}

{
  echo "=== round110 start $(TZ=Asia/Shanghai date) ==="
  echo "baseline_verified=$(count_verified) strategy=dict200-batchBR+gh10+repos@1500+always-ALL-gh-rotate@110-novel-slice1+2+3+probe-first+no-mine-zero-abort+skip-primeintellect-langdock-kiso-technology-stars+aggressive-notitle-ALL-slugs max_postings=$MAX_POSTINGS max_attempts=$MAX_ATTEMPTS exclude=$EXCLUDE_SLUGS min-success-gap=180 serialize_apply=1"
  echo "submitted_before_today=$(count_submitted)"
  echo "probe_fix=classify_form(detail['posting']) via $PROBE_HELPER"
  echo "no_stale_sourced_csv=1 apply_fresh_auto_only=1 no_test_slugs_in_new_slugs=1"
} | tee "$LOG"

echo "[ROUND110 PREFLIGHT] rotate@110 batch dict + gh-fallback" | tee -a "$LOG"
python3 "$MINE" --output "$POOL_DIR/ashby-round110-preflight-dict.txt" --max-verify 5 > "$POOL_DIR/ashby-round110-preflight-dict.json" 2>&1
python3 "$MINE" --output "$POOL_DIR/ashby-round110-preflight-gh110.txt" --gh-global-fallback --gh-global-rotate 110 --gh-rotate-slice 1 --max-verify 10 --gh-max-queries 12 > "$POOL_DIR/ashby-round110-preflight-gh110.json" 2>&1
cat "$POOL_DIR/ashby-round110-preflight-dict.json" | tee -a "$LOG"
cat "$POOL_DIR/ashby-round110-preflight-gh110.json" | tee -a "$LOG"
PF_DICT=$(python3 -c "import json;print(json.load(open('$POOL_DIR/ashby-round110-preflight-dict.json')).get('verified',0))" 2>/dev/null || echo 0)
PF_GH=$(python3 -c "import json;c=json.load(open('$POOL_DIR/ashby-round110-preflight-gh110.json'));print(c.get('verified',0))" 2>/dev/null || echo 0)
echo "[ROUND110 PREFLIGHT] dict_verified=$PF_DICT gh_rotate@110_verified=$PF_GH" | tee -a "$LOG"


rm -f "$SOURCED" "$MERGED" "$DEDUPED" "$PROBE_CSV" "$GATE_JSON"
rm -f "$NEW_SLUGS" "$FILTERED_SLUGS" "$MINE_JSON"

echo "[ROUND110 MINE] dict200 batch-BR (after batch-BP→next200) + gh10 novel-ashby-series-startup-MTS-infra posting-api verify" | tee -a "$LOG"
python3 "$MINE" --output "$NEW_SLUGS" --max-verify 220 --gh-max-queries 10 > "$MINE_JSON" 2>&1
cat "$MINE_JSON" | tee -a "$LOG"

MINE_COUNT=$(python3 - <<PY
import json
from pathlib import Path
p=Path("$MINE_JSON")
if not p.exists():
    print(0)
else:
    data=json.loads(p.read_text())
    print(data.get("new_slug_count", 0))
PY
)

echo "[ROUND110 MINE] new_slug_count=$MINE_COUNT posting_api_verified=$(python3 -c "import json;print(json.load(open('$MINE_JSON')).get('repo_hits',{}).get('posting_api_verified',0))" 2>/dev/null || echo 0) mine_source=$MINE_SOURCE" | tee -a "$LOG"

DICT_VERIFIED=$(python3 - <<PY
import json
from pathlib import Path
data=json.loads(Path("$MINE_JSON").read_text()) if Path("$MINE_JSON").exists() else {}
print(data.get("verified") or data.get("new_slug_count") or 0)
PY
)
echo "[ROUND110 MINE] dict_verified=$DICT_VERIFIED (early-repo-boost if <5 after gate)" | tee -a "$LOG"

if [[ "$MINE_COUNT" -lt 1 ]]; then
  echo "[ROUND110 FALLBACK] live mine=0 -> ashby_mine_github_repos.py FIRST" | tee -a "$LOG"
  python3 "$REPO_MINE" --offset 1500 --output "$NEW_SLUGS" --min-slugs 30 > "$MINE_JSON" 2>&1
  cat "$MINE_JSON" | tee -a "$LOG"
  MINE_COUNT=$(python3 - <<PY
import json
from pathlib import Path
data=json.loads(Path("$MINE_JSON").read_text())
print(data.get("new_slug_count") or data.get("verified") or 0)
PY
)
  if [[ "$MINE_COUNT" -ge 1 ]]; then
    MINE_SOURCE="github_repos"
    echo "[ROUND110 FALLBACK] github_repos unblocked mine count=$MINE_COUNT source=$MINE_SOURCE" | tee -a "$LOG"
  fi
fi

if [[ "$MINE_COUNT" -lt 1 ]]; then
  echo "[ROUND110 FALLBACK] mine still=0 -> gh-global rotate@110" | tee -a "$LOG"
  python3 "$MINE" --output "$NEW_SLUGS" --gh-global-fallback --gh-global-rotate 110 --gh-rotate-slice 1 --max-verify 220 --gh-max-queries 12 > "$MINE_JSON" 2>&1
  cat "$MINE_JSON" | tee -a "$LOG"
  MINE_COUNT=$(python3 - <<PY
import json
from pathlib import Path
data=json.loads(Path("$MINE_JSON").read_text())
print(data.get("new_slug_count") or data.get("verified") or 0)
PY
)
  if [[ "$MINE_COUNT" -ge 1 ]]; then
    MINE_SOURCE="gh_global"
    echo "[ROUND110 FALLBACK] gh-global rotate@110 unblocked mine count=$MINE_COUNT source=$MINE_SOURCE" | tee -a "$LOG"
  fi
fi

if [[ "$MINE_COUNT" -lt 1 ]]; then
  SAVED_LINES=$(count_lines "$SAVED_NEW_SLUGS")
  SAVED_AUTO=$(auto_count "$SAVED_DEDUPED")
  if [[ "$SAVED_LINES" -ge 1 ]]; then
    echo "[ROUND110 GUARD] mine=0 using saved batch-BR new-slugs count=$SAVED_LINES path=$SAVED_NEW_SLUGS" | tee -a "$LOG"
    cp "$SAVED_NEW_SLUGS" "$NEW_SLUGS"
    MINE_COUNT=$SAVED_LINES
    MINE_SOURCE="saved_slugs"
  elif [[ "$SAVED_AUTO" -ge 1 ]]; then
    echo "[ROUND110 GUARD] mine=0 using saved batch-BR deduped CSV auto=$SAVED_AUTO path=$SAVED_DEDUPED" | tee -a "$LOG"
    USE_SAVED_DEDUPED=1
    MINE_SOURCE="saved_deduped"
  else
    echo "[ROUND110 MINE] mine=0 after dict+github_repos+gh-global@110 — continue to probe-first + ALL gh slices (no early abort)" | tee -a "$LOG"
    : > "$NEW_SLUGS"
    MINE_SOURCE="mine_zero_continue"
  fi
else
  cp "$NEW_SLUGS" "$SAVED_NEW_SLUGS"
  echo "[ROUND110 MINE] saved batch-BR new-slugs count=$MINE_COUNT path=$SAVED_NEW_SLUGS mine_source=$MINE_SOURCE" | tee -a "$LOG"
fi

if [[ "$USE_SAVED_DEDUPED" -eq 1 ]]; then
  cp "$SAVED_DEDUPED" "$DEDUPED"
  AUTO_COUNT=$(auto_count "$DEDUPED")
  APPLY_CAP=$MAX_ATTEMPTS
  [[ "$AUTO_COUNT" -lt "$MAX_ATTEMPTS" ]] && APPLY_CAP=$AUTO_COUNT
  echo "[ROUND110 APPLY] saved-deduped queue_rows=$AUTO_COUNT max_attempts=$APPLY_CAP" | tee -a "$LOG"
  BEFORE=$(count_submitted)
  python3 -u "$BATCH"     --csv "$DEDUPED"     --count-date "$DATE"     --target-submitted 999     --max-attempts "$APPLY_CAP"     --max-attempts-per-slug 3     --min-success-gap 180     --allow-manual-retry 2>&1 | tee -a "$LOG"
  AFTER=$(count_submitted)
  DELTA=$((AFTER - BEFORE))
  VERIFIED=$(count_verified)
  echo "=== round110 end $(TZ=Asia/Shanghai date) saved-deduped final_today=$AFTER delta=+${DELTA} verified=$VERIFIED ===" | tee -a "$LOG"
  exit 0
fi

python3 - <<PY 2>&1 | tee -a "$LOG"
from pathlib import Path
import json
import re
skip_data = json.loads(Path("$ASHBY_SKIP_SLUGS_JSON").read_text(encoding="utf-8"))
skip = {re.sub(r"[^a-z0-9]+", "", s.casefold()) for s in skip_data.get("slugs", [])}
src = Path("$NEW_SLUGS")
out = Path("$FILTERED_SLUGS")
lines = []
dropped_skip = 0
for line in src.read_text().splitlines():
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    key = re.sub(r"[^a-z0-9]+", "", s.casefold())
    if key in skip:
        dropped_skip += 1
        continue
    lines.append(s)
out.write_text("\n".join(lines) + ("\n" if lines else ""))
print(f"[ROUND110 MINE] filtered_slugs={len(lines)} dropped_skip={dropped_skip} path={out}")
PY

SLUG_COUNT=$(count_lines "$FILTERED_SLUGS")
if [[ "$SLUG_COUNT" -lt 1 ]]; then
  echo "[ROUND110 MINE] no dict slugs after skip filter (mine=$MINE_COUNT) — skip initial probe; continue to supply chain" | tee -a "$LOG"
  : > "$PROBE_CSV"
  : > "$FORM_HIT_SLUGS"
  : > "$SOURCED"
  : > "$MERGED"
  echo '{"probe_pass":0,"dual_pass":0,"metadata_only":0}' > "$GATE_JSON"
  FORM_HIT_COUNT=0
  METADATA_AUTO=0
  AUTO_RAW=0
  SOURCE_PATH="mine_zero_skip_probe"
else
echo "[ROUND110 PROBE] force-probe ALL slug_count=$SLUG_COUNT max_postings_per_slug=$PROBE_POSTINGS" | tee -a "$LOG"
python3 "$PROBE_HELPER" \
  --slugs-file "$FILTERED_SLUGS" \
  --probe-csv "$PROBE_CSV" \
  --form-hit-slugs "$FORM_HIT_SLUGS" \
  --max-postings-per-slug "$PROBE_POSTINGS" \
  --pool-source round110-probe 2>&1 | tee -a "$LOG"

FORM_HIT_COUNT=$(count_lines "$FORM_HIT_SLUGS")
echo "[ROUND110 PROBE] form_hit_slugs=$FORM_HIT_COUNT path=$FORM_HIT_SLUGS" | tee -a "$LOG"

python3 - <<PY 2>&1 | tee -a "$LOG"
from pathlib import Path
filtered = [l.strip() for l in Path("$FILTERED_SLUGS").read_text().splitlines() if l.strip() and not l.startswith("#")]
hits = {l.strip() for l in Path("$FORM_HIT_SLUGS").read_text().splitlines() if l.strip()}
miss = [s for s in filtered if s not in hits]
Path("$PROBE_MISS_SLUGS").write_text("\n".join(miss) + ("\n" if miss else ""))
print(f"[ROUND110 PROBE] probe_hits={len(hits)} probe_miss={len(miss)} skip_metadata_for_probe_hits=1")
PY

PROBE_MISS_COUNT=$(count_lines "$PROBE_MISS_SLUGS")
SOURCE_PATH="probe_first"
if [[ "$SLUG_COUNT" -ge 1 ]]; then
  SOURCE_ARGS=()
  while IFS= read -r slug; do
    [[ -z "$slug" ]] && continue
    SOURCE_ARGS+=("--extra-slug" "$slug")
  done < "$FILTERED_SLUGS"
  echo "[ROUND110 SOURCE] aggressive metadata --no-title-filter on ALL verified slugs count=$SLUG_COUNT (probe_miss=$PROBE_MISS_COUNT)" | tee -a "$LOG"
  python3 "$OMX/ashby_sourcing.py" \
    --metadata-only \
    --no-title-filter \
    --max-postings "$MAX_POSTINGS" \
    --output "$SOURCED" \
    "${SOURCE_ARGS[@]}" \
    --only-extra 2>&1 | tee -a "$LOG"
  METADATA_AUTO=$(auto_count "$SOURCED")
  METADATA_ONLY_FALLBACK=1
  SOURCE_PATH="probe_first_aggressive_notitle"
else
  : > "$SOURCED"
  METADATA_AUTO=0
  echo "[ROUND110 SOURCE] no verified slugs; skip metadata-only" | tee -a "$LOG"
fi
echo "[ROUND110 SOURCE] metadata_auto=$METADATA_AUTO sourced=$SOURCED source_path=$SOURCE_PATH" | tee -a "$LOG"

echo "[ROUND110 GATE] probe-first: probe auto rows enter pool; metadata supplements probe-miss" | tee -a "$LOG"
python3 "$PROBE_FIRST_GATE" \
  --probe-csv "$PROBE_CSV" \
  --sourced-csv "$SOURCED" \
  --fresh-slugs "$FILTERED_SLUGS" \
  --merged-out "$MERGED" \
  --gate-json "$GATE_JSON" \
  --exclude-slugs "$EXCLUDE_SLUGS" \
  --source-path "$SOURCE_PATH" 2>&1 | tee -a "$LOG"

AUTO_RAW=$(auto_count "$MERGED")
echo "[ROUND110 POOL] fresh_auto_candidate=$AUTO_RAW probe-first gate source_path=$SOURCE_PATH probe_hits=$FORM_HIT_COUNT metadata_auto=$METADATA_AUTO" | tee -a "$LOG"
fi

# Round74 earlier supply boost: github_repos when dict verified<5 OR metadata auto=0 after gate (even mine>0)
if [[ "$DICT_VERIFIED" -lt 5 || "$AUTO_RAW" -lt 1 || "$METADATA_AUTO" -lt 1 ]]; then
  echo "[ROUND110 FALLBACK] early-repo-boost dict_verified=$DICT_VERIFIED metadata_auto=$METADATA_AUTO pool_auto=$AUTO_RAW -> github_repos BEFORE gh-rotate (mine=$MINE_COUNT)" | tee -a "$LOG"
  python3 "$REPO_MINE" --offset 1500 --output "$POOL_DIR/ashby-round110-early-repo-new-slugs.txt" --min-slugs 30 > "$POOL_DIR/ashby-round110-early-repo-mine.json" 2>&1
  cat "$POOL_DIR/ashby-round110-early-repo-mine.json" | tee -a "$LOG"
  EARLY_REPO_SLUGS="$POOL_DIR/ashby-round110-early-repo-new-slugs.txt"
  EARLY_REPO_FILTERED="$POOL_DIR/ashby-round110-early-repo-filtered.txt"
  EARLY_REPO_PROBE="$POOL_DIR/ashby-round110-early-repo-probe.csv"
  EARLY_REPO_FORM="$POOL_DIR/ashby-round110-early-repo-form-hit-slugs.txt"
  EARLY_REPO_SOURCED="$POOL_DIR/ashby-round110-early-repo-sourced.csv"
  python3 - <<PY 2>&1 | tee -a "$LOG"
from pathlib import Path
import re
skip = {re.sub(r"[^a-z0-9]+", "", s.casefold()) for s in """$SKIP_SLUGS""".split()}
src = Path("$EARLY_REPO_SLUGS")
out = Path("$EARLY_REPO_FILTERED")
lines = []
for line in src.read_text().splitlines() if src.exists() else []:
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    key = re.sub(r"[^a-z0-9]+", "", s.casefold())
    if key in skip:
        continue
    lines.append(s)
out.write_text("\n".join(lines) + ("\n" if lines else ""))
print(f"[ROUND110 FALLBACK] early-repo filtered_slugs={len(lines)}")
PY
  EARLY_REPO_COUNT=$(count_lines "$EARLY_REPO_FILTERED")
  if [[ "$EARLY_REPO_COUNT" -ge 1 ]]; then
    echo "[ROUND110 FALLBACK PROBE] early-repo slug_count=$EARLY_REPO_COUNT" | tee -a "$LOG"
    python3 "$PROBE_HELPER" \
      --slugs-file "$EARLY_REPO_FILTERED" \
      --probe-csv "$EARLY_REPO_PROBE" \
      --form-hit-slugs "$EARLY_REPO_FORM" \
      --max-postings-per-slug "$PROBE_POSTINGS" \
      --pool-source "round110-early-repo-probe" 2>&1 | tee -a "$LOG"
    EARLY_REPO_MISS="$POOL_DIR/ashby-round110-early-repo-probe-miss-slugs.txt"
    EARLY_REPO_SOURCED_NOTITLE="$POOL_DIR/ashby-round110-early-repo-sourced-notitle.csv"
    python3 - <<PY 2>&1 | tee -a "$LOG"
from pathlib import Path
filtered = [l.strip() for l in Path("$EARLY_REPO_FILTERED").read_text().splitlines() if l.strip() and not l.startswith("#")]
hits = {l.strip() for l in Path("$EARLY_REPO_FORM").read_text().splitlines() if l.strip()}
miss = [s for s in filtered if s not in hits]
Path("$EARLY_REPO_MISS").write_text("\n".join(miss) + ("\n" if miss else ""))
print(f"[ROUND110 FALLBACK] early-repo probe_hits={len(hits)} probe_miss={len(miss)}")
PY
    if [[ "$EARLY_REPO_COUNT" -ge 1 ]]; then
      EARLY_REPO_ARGS=()
      while IFS= read -r slug; do
        [[ -z "$slug" ]] && continue
        EARLY_REPO_ARGS+=("--extra-slug" "$slug")
      done < "$EARLY_REPO_FILTERED"
      echo "[ROUND110 FALLBACK] early-repo aggressive --no-title-filter on ALL slugs count=$EARLY_REPO_COUNT" | tee -a "$LOG"
      python3 "$OMX/ashby_sourcing.py" \
        --metadata-only \
        --no-title-filter \
        --max-postings "$MAX_POSTINGS" \
        --output "$EARLY_REPO_SOURCED" \
        "${EARLY_REPO_ARGS[@]}" \
        --only-extra 2>&1 | tee -a "$LOG"
    else
      : > "$EARLY_REPO_SOURCED"
    fi
    python3 $WORK_DIR/scripts/round80_fallback_merge.py \
      "$MERGED" "$GATE_JSON" "$EARLY_REPO_PROBE" "$EARLY_REPO_SOURCED" \
      "$EARLY_REPO_FILTERED" "$EXCLUDE_SLUGS" 2>&1 | tee -a "$LOG"
    AUTO_RAW=$(auto_count "$MERGED")
    echo "[ROUND110 FALLBACK] early-repo merged_auto=$AUTO_RAW" | tee -a "$LOG"
  fi
fi

source $WORK_DIR/scripts/round110-gh-fallback.sh

if [[ "$AUTO_RAW" -lt 1 ]]; then
  echo "[ROUND110 FALLBACK] pool=0 after gh rotate@110 -> ashby_mine_github_repos.py (post-gate)" | tee -a "$LOG"
  python3 "$REPO_MINE" --offset 1500 --output "$POOL_DIR/ashby-round110-postgate-repo-new-slugs.txt" --min-slugs 30 > "$POOL_DIR/ashby-round110-postgate-repo-mine.json" 2>&1
  cat "$POOL_DIR/ashby-round110-postgate-repo-mine.json" | tee -a "$LOG"
  source $WORK_DIR/scripts/round110-repo-fallback.sh
  AUTO_RAW=$(auto_count "$MERGED")
fi

if [[ "$AUTO_RAW" -lt 1 ]]; then
  echo "[ROUND110 ABORT] no fresh auto_candidate rows after probe-first+post-gate-repo" | tee -a "$LOG"
  yield_abort "no-fresh-auto-after-dual-gate"
  exit 0
fi

python3 "$DEDUPE_POOL" \
  --input "$MERGED" \
  --output "$DEDUPED" \
  --dedupe-script "$DEDUPE" 2>&1 | tee -a "$LOG"

cp "$DEDUPED" "$SAVED_DEDUPED"
echo "[ROUND110 POOL] saved deduped path=$SAVED_DEDUPED" | tee -a "$LOG"

AUTO_COUNT=$(auto_count "$DEDUPED")
APPLY_CAP=$MAX_ATTEMPTS
if [[ "$AUTO_COUNT" -lt "$MAX_ATTEMPTS" ]]; then
  APPLY_CAP=$AUTO_COUNT
fi
echo "queue_csv=$DEDUPED queue_rows=$AUTO_COUNT max_attempts=$APPLY_CAP fresh_auto_only=1" | tee -a "$LOG"

BEFORE=$(count_submitted)
python3 -u "$BATCH" \
  --csv "$DEDUPED" \
  --count-date "$DATE" \
  --target-submitted 999 \
  --max-attempts "$APPLY_CAP" \
  --max-attempts-per-slug 3 \
  --min-success-gap 180 \
  --allow-manual-retry 2>&1 | tee -a "$LOG"

AFTER=$(count_submitted)
DELTA=$((AFTER - BEFORE))
VERIFIED=$(count_verified)
echo "=== round110 end $(TZ=Asia/Shanghai date) final_today=$AFTER delta_today=+${DELTA} verified=$VERIFIED ===" | tee -a "$LOG"

python3 - <<PY | tee -a "$LOG"
import csv, json
from collections import Counter
from pathlib import Path

log = Path("$LOG").read_text(errors="ignore")
attempts = []
skip_slugs = []
for line in log.splitlines():
    if '"stage": "result"' in line:
        try:
            attempts.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    if '"stage": "skip-slug"' in line:
        try:
            skip_slugs.append(json.loads(line))
        except json.JSONDecodeError:
            pass

def submitted(a):
    return a.get("returncode") == 0 and a.get("submitted_count_after", 0) > a.get("submitted_count_before", 0)

success = sum(1 for a in attempts if submitted(a))
gate = json.loads(Path("$GATE_JSON").read_text()) if Path("$GATE_JSON").exists() else {}
mine = json.loads(Path("$MINE_JSON").read_text()) if Path("$MINE_JSON").exists() else {}

deduped = Path("$DEDUPED")
pool_auto = sum(1 for r in csv.DictReader(deduped.open()) if r.get("status") == "auto_candidate") if deduped.exists() else 0

ns = Path("$NEW_SLUGS")
new_slugs = [l.strip() for l in ns.read_text().splitlines() if l.strip() and not l.startswith("#")] if ns.exists() else []

gate_rows = list(csv.DictReader(Path("$MERGED").open())) if Path("$MERGED").exists() else []
slug_auto = Counter(r.get("slug") for r in gate_rows)
gate_by_slug = Counter(r.get("gate") for r in gate_rows)

probe_rows = list(csv.DictReader(Path("$PROBE_CSV").open())) if Path("$PROBE_CSV").exists() else []
probe_auto = sum(1 for r in probe_rows if r.get("status") == "auto_candidate")
probe_rate = f"{probe_auto}/{len(probe_rows)}" if probe_rows else "n/a"
mine_count = mine.get("new_slug_count") or mine.get("verified") or 0

print("=== yield summary ===")
print(f"round110 pool_auto={pool_auto} max_attempts=$APPLY_CAP exclude_slugs=$EXCLUDE_SLUGS")
print(f"round110 apply_attempts={len(attempts)} yield={success}/{len(attempts) or 0}")
print(f"round110 skip_slug_events={len(skip_slugs)} slugs={[s.get('slug') for s in skip_slugs]}")
print(f"round110 delta_today=+${DELTA} ($BEFORE->$AFTER)")
print(f"round110 verified=$VERIFIED (baseline 582 -> +${DELTA})")
print(f"round110 probe_fix=classify_form(detail['posting']) confirmed in $PROBE_HELPER")
print(f"round110 form_hit_count=$FORM_HIT_COUNT probe_rate={probe_rate} mine=$MINE_COUNT mine_source=$MINE_SOURCE source_path=$SOURCE_PATH metadata_fallback=$METADATA_ONLY_FALLBACK")
print(f"round110 gate_probe_pass={gate.get('probe_pass', 0)} gate_dual={gate.get('dual_pass', 0)} gate_metadata_only={gate.get('metadata_only', 0)} gate_breakdown={dict(gate_by_slug)}")
print(f"round110 mine_new_slug_count={mine_count} posting_api_verified={mine.get('repo_hits', {}).get('posting_api_verified', 0)} exclude_known={mine.get('exclude_known', 0)}")
print(f"round110 new_slugs={','.join(new_slugs[:80])}")
print(f"round110 new_slugs_auto_gt0={','.join(s for s,n in slug_auto.items() if n>0) if slug_auto else 'none'}")
if slug_auto:
    print(f"round110 top_auto_slugs={','.join(f'{s}:{n}' for s,n in slug_auto.most_common(10))}")
else:
    print("round110 top_auto_slugs=none")
print(f"round110 supply_chain=dict_batchBQ+gh10+probe_first+early_repo+gh_rotate@110+postgate_repo+no_title mine_source=$MINE_SOURCE dict_verified=$DICT_VERIFIED metadata_auto=$METADATA_AUTO")
slices_used = "slice1"
for line in log.splitlines():
    if "gh_slices_used=" in line:
        slices_used = line.split("gh_slices_used=", 1)[-1].strip()
print(f"round110 gh_slices_used={slices_used}")
PY
echo "=== round110 end $(TZ=Asia/Shanghai date) verified=$(count_verified) ===" | tee -a "$LOG"
