---
name: job-search-orchestrator
description: Daily entry-point dashboard for Yupeng's US/Bay Area job search. Scans local state (curated PDFs, mined markdown, application ledger, Gmail, LinkedIn replies, GitHub commits) and produces a single triage report telling the user what to do next — refresh resume, run daily applications, triage Gmail, finish ManualFinish tabs, prep interviews, fix hash drift. Does NOT take any action itself; only routes to the right sub-skill (gh-resume-builder, daily-job-apply, etc.) and shows pending work. Use as the morning/evening "what should I do today" command.
---

# Job Search Orchestrator

The single daily entry point for Yupeng's job search. Read state, decide, route. **Never apply, never email, never edit resumes** — those are the job of sub-skills (`gh-resume-builder`, `daily-job-apply`).

**Standing override (2026-10-25).** LinkedIn Easy Apply is **FROZEN** — do not schedule it and do not route a batch to `linkedin-application-agent`. The weekday routine is **~50 verified zero-gate Greenhouse** submits via `daily-job-apply` + `job-apply-automation`, chrome-use session **`jobapply2`** (`--browser yplmicro@gmail.com`, Lu Profile 2). The old "weekly target 20" and "Easy Apply cap 25" lines below do not override that. The BJT 09:00–19:00 write ban was retired with stealth (2026-10-18); it must not block external ATS. The standing routine clock is still 21:00 Asia/Shanghai.

## Mental model

Think of this skill as a NOC dashboard, not a worker. Each run produces a 1-page triage report with:
- **System health**: hash drift, file presence, skill consistency
- **Pipeline status**: where things sit (applied / waiting / interview / ghosted)
- **Today's recommended actions** (ranked by impact × urgency)
- **Routing**: which sub-skill to invoke for each action

## When to use

- "What should I do today for my job search?"
- "Morning check / evening check"
- "Status of my job search"
- "Should I update my resume today?"
- "Anything I missed?"
- Default first action whenever the user opens a job-search conversation without a specific sub-task.

## When NOT to use

- ❌ "Apply to these jobs" → route to `daily-job-apply` (policy) then `job-apply-automation` (loop)
- ❌ "Update my resume from commits" → route to `gh-resume-builder`
- ❌ "Fill out this LinkedIn Easy Apply" → **do not run it**. Easy Apply is FROZEN (`daily-job-apply` COLD-START). Do not route a batch to `linkedin-application-agent`
- ❌ "Edit build_resumes.py" → just edit it directly

## Canonical paths (must match other skills)

```
RESUME_BASE="/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu"
SOURCE_OF_TRUTH="$RESUME_BASE/source-of-truth"             # mined markdown
CURATED_SCRIPT="$RESUME_BASE/curated-script"               # build_resumes.py
APP_PDFS="$RESUME_BASE/application-ai-agent"               # curated 1P/2P EN+ZH PDFs + pdf-hashes.txt

# Vault application archive tree (per-batch, per-company evidence)
APPLICATIONS="$RESUME_BASE/applications"                   # <channel>-batch-YYYY-MM-DD/<job>.md
INTERVIEWS="$RESUME_BASE/Interviews"                       # <Company>/{jd,prep,questions,feedback}.md
EVIDENCE="$RESUME_BASE/evidence"                           # raw artifacts (JD dumps, screenshots)
PROOF_PACKAGE="$RESUME_BASE/proof-package"                 # curated case studies (LinkedIn Featured)
RESUME_PROOF="$RESUME_BASE/resume-proof"                   # gh-resume-builder proof mode output

# Operational ledger (lightweight, append-only)
JOB_HUNT="$HOME/job-hunt"                                  # tracker.csv + application-ledger.md
PROFILE_JSON="$HOME/job-hunt/data/profile.json"            # redacted PII source of truth

GMAIL_ACCOUNT="yplmicro@gmail.com"
LINKEDIN_PROFILE="https://www.linkedin.com/in/yupeng-lu-845a0b411/"
GH_PERSONAL="BrickerP"
GH_WORK="yupeng-dev"
```

### Vault archive schema (orchestrator assumes this layout)

```
applications/                                      # promotion ladder: single-file → directory
  <channel>-batch-YYYY-MM-DD.md                    # DEFAULT — markdown table, one row per job
                                                   #   columns: | # | Status | Company | Role | ...
                                                   #   Status ∈ {Submitted, Skipped, ManualFinish, Blocked}
  <channel>-batch-YYYY-MM-DD/<company>--<role>.md  # PROMOTED — when a job needs JD/screenshot/notes
                                                   #   optional `Status: Submitted` header line

  channel ∈ {linkedin, greenhouse, lever, ashby, workday, direct, referral}

Interviews/                                        # same promotion ladder
  <Company>.md                                     # DEFAULT — single file with Date: + prep notes inline
  <Company>/                                       # PROMOTED — active multi-round process
    jd.md          # JD snapshot
    prep.md        # STAR stories + system-design talking points + behavioral
    questions.md   # interviewer-asked questions, post-mortem
    feedback.md    # debrief notes, next-round signals
    meta.yaml      # optional: {next_date: YYYY-MM-DD, round: N, stage: phone|onsite|...}

evidence/        # freeform artifacts (screenshots, full JD html, recruiter email exports)
proof-package/   # curated <topic>.md for public-facing case studies
resume-proof/    # gh-resume-builder proof-mode output, off-limits to this skill
```

**Promotion principle**: cold applies stay single-file; only "graduated" entries (interviews
scheduled, recruiter contact, case-study material) get promoted to a directory. Orchestrator
does NOT enforce — it reads both layouts and *recommends* promotion when it detects momentum.
Never auto-create files in these dirs.

## Run order (each invocation does all 11 checks)

### 1. Time-window gate

```bash
BJT=$(TZ=Asia/Shanghai date +%H)
if [ "$BJT" -ge 9 ] && [ "$BJT" -lt 19 ]; then
  echo "BJT $BJT:xx — LinkedIn write-actions BLOCKED. Read-only mode."
  WRITE_OK=false
else
  WRITE_OK=true
fi
```

Surface this at the very top of the dashboard. All later "ACTION" recommendations must respect it.

### 2. Curated PDF hash drift check

```bash
cd "$APP_PDFS"
ACTUAL=$(shasum -a 256 *.pdf | sort)
EXPECTED=$(sort pdf-hashes.txt)
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "❌ HASH DRIFT detected. Investigate before applying."
  diff <(echo "$ACTUAL") <(echo "$EXPECTED")
fi
```

If drift: dashboard MUST surface as P0. Recommended action: "Investigate — has someone regenerated PDFs without re-baselining?"

### 3. Skill consistency check

Verify the same skill content exists in all known skill dirs:

```bash
for s in gh-resume-builder daily-job-apply job-search-orchestrator; do
  for d in ~/.codex/skills ~/.agents/skills ~/.claude/skills; do
    f="$d/$s/SKILL.md"
    [ -f "$f" ] && shasum -a 256 "$f" | awk '{print $1}'
  done
done
```

If hashes diverge across dirs for the same skill → surface as P1 ("skills out of sync — last edit may not be active").

### 4. File presence sanity

Check that critical files exist and are non-empty:
- `$SOURCE_OF_TRUTH/resume_yupeng_en.md`
- `$SOURCE_OF_TRUTH/resume_yupeng_zh.md`
- `$CURATED_SCRIPT/build_resumes.py`
- `$APP_PDFS/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`
- `$APP_PDFS/Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf`
- `$APP_PDFS/pdf-hashes.txt` (baseline covers 1P/2P EN+ZH quartet)
- `$JOB_HUNT/tracker.csv`
- `$JOB_HUNT/application-ledger.md`
- `$PROFILE_JSON` (if missing → P1; orchestrator + daily-job-apply both depend on it)

Also check the **Vault archive directories exist** (but contents may be empty):
- `$APPLICATIONS/`
- `$INTERVIEWS/`
- `$EVIDENCE/`

Any critical file missing → P0. Vault dir missing → P1 (likely fresh machine / unsynced Obsidian Vault).

### 5. Resume freshness check ("worth refreshing?")

```bash
# Last mined markdown update
LAST_MINED=$(stat -f %m "$SOURCE_OF_TRUTH/resume_yupeng_en.md" 2>/dev/null || stat -c %Y "$SOURCE_OF_TRUTH/resume_yupeng_en.md")
NOW=$(date +%s)
DAYS_SINCE_MINED=$(( (NOW - LAST_MINED) / 86400 ))

# Snapshot cutoff inside the markdown
CUTOFF=$(grep -oE 'Resume snapshot cutoff: [0-9]{4}-[0-9]{2}-[0-9]{2}' "$SOURCE_OF_TRUTH/resume_yupeng_en.md" | head -1 | awk '{print $NF}')

# Count PRs merged since cutoff (work account)
gh auth switch --user yupeng-dev 2>/dev/null
NEW_PRS=$(gh search prs --author=yupeng-dev --owner=cookiy-ai --state=closed \
  --merged-at=">=$CUTOFF" --limit 1000 \
  --json number 2>/dev/null | jq 'length')

# Decision rules
if [ "$DAYS_SINCE_MINED" -ge 7 ] || [ "$NEW_PRS" -ge 20 ]; then
  echo "📝 RECOMMEND: refresh source-of-truth markdown (last update ${DAYS_SINCE_MINED}d ago, $NEW_PRS new PRs since cutoff)"
  echo "   → Run: gh-resume-builder skill"
fi
```

Thresholds (tunable):
- `DAYS_SINCE_MINED >= 7` → suggest markdown refresh
- `NEW_PRS >= 20` → suggest markdown refresh (regardless of days)
- `NEW_PRS >= 50` OR `new public artifact detected` → also suggest PDF refresh

Detecting "new public artifact":
```bash
# new npm package version published since last week, new public repo, new release tag, new pinned repo
# (only if local cache available; otherwise skip)
```

### 6. Application pipeline status (ledger-side)

Parse `~/job-hunt/application-ledger.md` (format `timestamp | status | name | url`):

```bash
LEDGER="$JOB_HUNT/application-ledger.md"
TODAY=$(date +%Y-%m-%d)
WEEK_AGO=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d)

# Ledger rows may be bullet-prefixed (`- 2026-...`) or raw (`2026-...`).
# Extract the first YYYY-MM-DD anywhere on the row; do not rely on `$1`.
TODAY_SUBMITTED=$(awk -v d="$TODAY" '
  match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/) {
    row_date=substr($0, RSTART, RLENGTH)
    if (row_date == d && $0 ~ /\| Submitted \|/) n++
  }
  END{print n+0}
' "$LEDGER")
TODAY_MANUAL=$(awk -v d="$TODAY" '
  match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/) {
    row_date=substr($0, RSTART, RLENGTH)
    if (row_date == d && $0 ~ /\| ManualFinish \|/) n++
  }
  END{print n+0}
' "$LEDGER")

# This week
WEEK_SUBMITTED=$(awk -v cutoff="$WEEK_AGO" '
  match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/) {
    row_date=substr($0, RSTART, RLENGTH)
    if (row_date >= cutoff && $0 ~ /\| Submitted \|/) n++
  }
  END{print n+0}
' "$LEDGER")

# Open manual-finish tabs (any time, not just today)
OPEN_MANUAL=$(awk '$0 ~ /\| ManualFinish \|/ {n++} END{print n+0}' "$LEDGER")

# Referral follow-ups due. Lines usually contain "after YYYY-MM-DD HH:MM BJT".
FOLLOWUPS_DUE=$(awk -v today="$TODAY" '
  /\| ReferralFollowUp \|/ && match($0, /after [0-9]{4}-[0-9]{2}-[0-9]{2}/) {
    due=substr($0, RSTART + 6, 10)
    if (due <= today) n++
  }
  END{print n+0}
' "$LEDGER")
```

Decision rules:
- `TODAY_SUBMITTED == 0` → "📮 No verified submits today. Run `daily-job-apply` zero-gate Greenhouse on session `jobapply2`." The retired BJT write ban does not block this. Do not schedule Easy Apply.
- `OPEN_MANUAL >= 3` → "⚠️ $OPEN_MANUAL manual-finish tabs piling up. Triage before opening new ones."
- Weekday evening with no verified zero-gate Greenhouse submits → "📮 Run `daily-job-apply` on session `jobapply2` (routine ~50). Do not schedule Easy Apply." The old weekly floor of 20 does not replace that routine.
- `FOLLOWUPS_DUE > 0` → "🔁 $FOLLOWUPS_DUE referral follow-ups due."

### 6.5. Vault application archive scan (ledger ↔ vault reconciliation)

The ledger is self-reported; the Vault `applications/` tree is the **physical evidence** of what
got touched. Always cross-check — drift signals lost data.

**Two layouts supported** (the user's vault uses BOTH):

| Layout | Path | Use | Counting |
|---|---|---|---|
| **Single-file batch** (legacy / default) | `applications/<channel>-batch-YYYY-MM-DD.md` | Cold-apply evidence; one Markdown table per batch | `awk` table rows |
| **Per-job directory** (promoted) | `applications/<channel>-batch-YYYY-MM-DD/<job>.md` | Jobs that "graduated" — got JD attached, screenshot, recruiter contact | `find -name '*.md'` |

Single-file batch schema (must be a GFM table with at least these columns in order):

```text
| # | Status | Company | Role | ... |
|---|---|---|---|---|
| 1 | Skipped | Dexian | Generative AI Engineer | ... |
| 2 | Submitted | TRADEBE | AI Solutions Engineer | ... |
```

The orchestrator counts a row as a "job" only if column 2 is a bare integer (filters out header
divider rows). `Submitted` in column 3 means it actually went out; `Skipped/ManualFinish/Blocked`
counts as "touched" but not "submitted".

```bash
# Bash 3.2-compatible (macOS): use tmp files instead of declare -A
TMP_DAY=$(mktemp)            # lines: "YYYY-MM-DD<TAB>touched<TAB>submitted"
TMP_CHANNEL=$(mktemp)        # lines: "channel<TAB>touched<TAB>submitted"
trap 'rm -f "$TMP_DAY" "$TMP_CHANNEL"' EXIT

# A1. Legacy single-file batches: applications/<channel>-batch-YYYY-MM-DD.md
for f in "$APPLICATIONS"/*-batch-*.md; do
  [ -f "$f" ] || continue
  base=$(basename "$f" .md)
  date_part=$(echo "$base" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  channel=$(echo "$base" | sed -E 's/-batch-[0-9-]+$//')
  [ -z "$date_part" ] && continue
  [ "$date_part" \< "$WEEK_AGO" ] && continue

  touched=$(awk -F'|' 'NR>2 && $2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ {n++} END{print n+0}' "$f")
  submitted=$(awk -F'|' 'NR>2 && $2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $3 ~ /Submitted/ {n++} END{print n+0}' "$f")

  printf '%s\t%d\t%d\n' "$date_part" "$touched" "$submitted" >> "$TMP_DAY"
  printf '%s\t%d\t%d\n' "$channel"   "$touched" "$submitted" >> "$TMP_CHANNEL"
done

# A2. Promoted per-job directories: applications/<channel>-batch-YYYY-MM-DD/<job>.md
for batch in "$APPLICATIONS"/*-batch-*/; do
  [ -d "$batch" ] || continue
  name=$(basename "$batch")
  date_part=$(echo "$name" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  channel=$(echo "$name" | sed -E 's/-batch-[0-9-]+$//')
  [ -z "$date_part" ] && continue
  [ "$date_part" \< "$WEEK_AGO" ] && continue

  touched=$(find "$batch" -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
  # promoted dirs are treated as "submitted by default" unless a per-file Status: Skipped is present
  submitted=$(grep -lE '^Status:[[:space:]]*Submitted' "$batch"/*.md 2>/dev/null | wc -l | tr -d ' ')
  # if no per-file Status header found, fall back to "all touched = all submitted"
  [ "$submitted" -eq 0 ] && submitted="$touched"

  printf '%s\t%d\t%d\n' "$date_part" "$touched" "$submitted" >> "$TMP_DAY"
  printf '%s\t%d\t%d\n' "$channel"   "$touched" "$submitted" >> "$TMP_CHANNEL"
done

# B. Aggregate per-day
VAULT_TODAY_TOUCHED=$(awk -F'\t' -v d="$TODAY" '$1==d {t+=$2} END{print t+0}' "$TMP_DAY")
VAULT_TODAY_SUBMIT=$(awk -F'\t' -v d="$TODAY" '$1==d {s+=$3} END{print s+0}' "$TMP_DAY")
VAULT_WEEK_TOUCHED=$(awk -F'\t' '{t+=$2} END{print t+0}' "$TMP_DAY")
VAULT_WEEK_SUBMIT=$(awk -F'\t' '{s+=$3} END{print s+0}' "$TMP_DAY")

# C. Channel distribution (vault-side, more reliable than parsing ledger notes)
awk -F'\t' '{t[$1]+=$2; s[$1]+=$3} END{for(c in t) printf "%s\t%d\t%d\n", c, t[c], s[c]}' \
  "$TMP_CHANNEL" | sort -k3 -rn

# D. Ledger ↔ Vault drift (compare SUBMITTED only — touched != submitted by design)
diff_today=$(( TODAY_SUBMITTED - VAULT_TODAY_SUBMIT ))
diff_week=$((  WEEK_SUBMITTED  - VAULT_WEEK_SUBMIT  ))
[ "${diff_today#-}" -ge 3 ] && echo "⚠️ DRIFT today: ledger=$TODAY_SUBMITTED vs vault=$VAULT_TODAY_SUBMIT (Δ=$diff_today)"
[ "${diff_week#-}"  -ge 3 ] && echo "⚠️ DRIFT week:  ledger=$WEEK_SUBMITTED  vs vault=$VAULT_WEEK_SUBMIT  (Δ=$diff_week)"
```

Decision rules:
- `abs(ledger_submit - vault_submit) >= 3` on today OR week → **P1 DATA DRIFT** — reconcile.
  Common causes: ledger written but Status column in vault still says Skipped; new batch file
  created without ledger append; ledger row added without batch file.
- `VAULT_TODAY_SUBMIT > 0 AND TODAY_SUBMITTED == 0` → **downgrade Step 6's "no applications today"
  from P1 to INFO** + recommend ledger backfill.
- `VAULT_TODAY_SUBMIT == 0 AND TODAY_SUBMITTED > 0` → **P1**: ledger lies, or batch filename
  doesn't match `<channel>-batch-YYYY-MM-DD(.md|/)`.
- `VAULT_TODAY_TOUCHED > VAULT_TODAY_SUBMIT * 3` → **INFO**: low submit rate this batch
  (many Skipped); JD-quality filter may be too loose, or batch had a bad source list.
- Single-channel dominance (vault SUBMIT-side): any channel ≥ 70% of `VAULT_WEEK_SUBMIT` →
  recommend diversification (overrides Step 9's ledger-based check).

Prefer vault-side numbers over ledger-side in the dashboard's pipeline snapshot when they
disagree, but **always surface both** (touched / submitted / ledger) so the user knows which
to fix.

### 6.6. Tracker triangle consistency (ledger ↔ vault ↔ tracker)

Do not collapse all data drift into one bucket. Each pair has a different likely root cause:

| Pair | Compare | Likely root cause when drift exists |
|---|---|---|
| `ledger ↔ vault` | submitted rows | archive schema gap or missing batch emission |
| `tracker ↔ vault` | submitted rows by channel/date | tracker channel missing from archive or archive extra rows |
| `ledger ↔ tracker` | submitted URLs | tracker upsert race / ledger append race |

Use Python `csv` for tracker parsing. Do **not** use `awk -F','`; `Role` and `Notes` can contain commas.

```bash
python3 - <<'PY'
import csv, re
from pathlib import Path
TRACKER = Path.home() / "job-hunt" / "tracker.csv"
with TRACKER.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def norm_channel(raw):
    text = (raw or "").lower()
    if "linkedin" in text: return "linkedin"
    if "greenhouse" in text: return "greenhouse"
    if "lever" in text: return "lever"
    if "ashby" in text: return "ashby"
    if "workday" in text: return "workday"
    if "direct" in text or "company" in text: return "direct"
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "unknown"

def is_submitted(r):
    text = " ".join([r.get("Application_Submitted",""), r.get("Response_Status",""), r.get("Stage","")])
    return bool(re.search(r"\\bYes\\b|Submitted|Applied", text, re.I))

# Agent should then build:
# - TRACKER_WEEK_SUBMIT
# - TRACKER_CHANNEL_SUBMIT[channel]
# - submitted URL sets for tracker and ledger
PY
```

Decision rules:
- `ledger ↔ vault` drift ≥ 3 → **P1 DATA DRIFT / ARCHIVE GAP**. If tracker channels explain the
  gap, print a one-command repair suggestion:
  `python3 ~/.codex/skills/daily-job-apply/scripts/job_archive.py backfill --date YYYY-MM-DD --channels lever greenhouse`.
- `tracker ↔ vault` drift ≥ 3 → **P1 TRACKER/Vault mismatch**. Check channel normalization and
  whether external ATS submissions emitted batch rows.
- `ledger ↔ tracker` drift ≥ 1 → **P2 unless it hides an active interview or reply**. List the
  exact missing URL/company; likely cause is tracker upsert race after ledger append.

### 7. Gmail / LinkedIn reply triage

Use the local Gmail worker first, not the generic Gmail connector. The generic
MCP Gmail connector may be authenticated as a non-job-search account; if it is
used as a fallback, first run `get_profile` and require exactly
`yplmicro@gmail.com`. If the profile is anything else, skip it and report
`wrong Gmail connector account`.

```bash
GMAIL_WORKER="$HOME/.codex/gmail-ai-daily-ops/gmail-ai-worker"
GMAIL_PY="$GMAIL_WORKER/.venv/bin/python"
GMAIL_MAILBOX="yplmicro-gmail-com"

cd "$GMAIL_WORKER"

# Hard account guard. This must report profile=yplmicro@gmail.com.
echo '{"op":"ping","mailbox":"yplmicro-gmail-com"}' |
  "$GMAIL_PY" scripts/gmail_call.py

# Last-24h job-search unread candidate threads.
JOB_QUERY='newer_than:1d is:unread (from:ashbyhq.com OR from:greenhouse.io OR from:lever.co OR from:linkedin.com OR from:workday.com OR subject:application OR subject:interview OR subject:recruiter)'
printf '{"op":"threads_list","mailbox":"%s","query":%s,"max_results":50}\n' \
  "$GMAIL_MAILBOX" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$JOB_QUERY")" |
  "$GMAIL_PY" scripts/gmail_call.py

# If important direct-human or interview-like threads appear, fetch details with:
# echo '{"op":"snapshot_bundle","mailbox":"yplmicro-gmail-com","query":"<query>","max_threads":10,"messages_per_thread":3,"excerpt_chars":1200}' |
#   "$GMAIL_PY" scripts/gmail_call.py
```

Decision:
- `unread_job_emails > 0` → "📧 $N new job-related emails. Triage: identify interviews / rejections / next-step CTAs."
- `linkedin_recruiter_messages > 0` → "💬 LinkedIn recruiter DMs unread."
- Gmail worker missing, ping fails, or connector profile is not `yplmicro@gmail.com` → **P1**:
  "Fix job-mail access before relying on inbox metrics."

Categorize each unread by sender pattern:
- `*@ashbyhq.com` / `*@greenhouse.io` / `*@lever.co` → ATS status
- `*@linkedin.com` → LinkedIn (could be recruiter, could be platform spam)
- Direct human sender → likely recruiter, P0

### 8. Interview backlog check (vault-side, tracker is fallback)

Primary signal = `$INTERVIEWS/<Company>/` directories OR `$INTERVIEWS/<Company>.md` single files.
Tracker.csv `Status=Interview` rows are a fallback when neither exists yet.

**Two layouts supported** — same promotion pattern as `applications/`:

| Layout | Path | When to use |
|---|---|---|
| **Single file** (initial) | `Interviews/<Company>.md` | A recruiter reached out, you scheduled a call, you're still figuring out which round |
| **Directory** (promoted) | `Interviews/<Company>/{jd,prep,questions,feedback}.md` + optional `meta.yaml` | Active multi-round process; you want JD / prep / debrief separately versioned |

```bash
TODAY_TS=$(date +%s)

# (a) Directory-form companies
for company_dir in "$INTERVIEWS"/*/; do
  [ -d "$company_dir" ] || continue
  company=$(basename "$company_dir")

  next_date=""
  if [ -f "$company_dir/meta.yaml" ]; then
    next_date=$(grep -E '^next_date:' "$company_dir/meta.yaml" | awk '{print $2}' | tr -d '"')
  fi
  if [ -z "$next_date" ]; then
    next_date=$(grep -hoE '(Date|next_date|Scheduled): *[0-9]{4}-[0-9]{2}-[0-9]{2}' \
                "$company_dir"/*.md 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | tail -1)
  fi

  has_prep=$([ -f "$company_dir/prep.md" ] && echo yes || echo no)
  has_jd=$([ -f "$company_dir/jd.md" ] && echo yes || echo no)
  layout=dir

  emit_interview "$company" "$next_date" "$has_prep" "$has_jd" "$layout"
done

# (b) Single-file companies
for company_file in "$INTERVIEWS"/*.md; do
  [ -f "$company_file" ] || continue
  company=$(basename "$company_file" .md)

  # parse any common date label inside the single file
  next_date=$(grep -hoE '(Date|next_date|Scheduled|Interview Date|时间|面试时间): *[0-9]{4}-[0-9]{2}-[0-9]{2}' \
              "$company_file" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | tail -1)
  stage=$(grep -hoE '^Stage: *[A-Za-z0-9_-]+' "$company_file" 2>/dev/null | awk '{print $2}' | tail -1)

  # Detect prep/JD content heuristically inside the same file.
  # Support numbered headings like "## 1) JD keyword map" and "### STAR 1".
  has_prep=$(grep -qiE '^(##+ *)?([0-9]+[.)：:-]? *)?(prep|preparation|准备|STAR)' "$company_file" && echo yes || echo no)
  has_jd=$(grep -qiE   '^(##+ *)?([0-9]+[.)：:-]? *)?(jd|job description|职位摘要|岗位描述|职责)' "$company_file" && echo yes || echo no)
  layout=file

  emit_interview "$company" "$next_date" "$has_prep" "$has_jd" "$layout" "$stage"
done

# Helper (define once at top of step):
emit_interview() {
  local company=$1 next_date=$2 has_prep=$3 has_jd=$4 layout=$5 stage=${6:-unknown}
  if [ -n "$next_date" ]; then
    next_ts=$(date -j -f %Y-%m-%d "$next_date" +%s 2>/dev/null || date -d "$next_date" +%s)
    days_to=$(( (next_ts - TODAY_TS) / 86400 ))
    echo "$company | layout=$layout | next=$next_date (T-${days_to}d) | prep=$has_prep | jd=$has_jd | stage=$stage"
  else
    echo "$company | layout=$layout | next=UNKNOWN | prep=$has_prep | jd=$has_jd | stage=$stage"
  fi
}

# Tracker fallback — flag interviews in tracker that have NEITHER dir NOR file
INTERVIEWS_IN_TRACKER=$(grep -c ',Interview,' "$JOB_HUNT/tracker.csv" 2>/dev/null || echo 0)
```

Decision rules:
- Any interview with `days_to <= 7 AND has_prep == no` → **P1**:
  "🎯 Interview with $COMPANY in $days_to days, no prep section. Run interview-prep flow."
- Any interview with `days_to <= 2 AND has_jd == no` → **P0**:
  "🚨 Interview with $COMPANY in $days_to days but JD not captured. Capture JD now."
- `layout=file AND next_date present AND in future` → **P1 PROMOTE**:
  "📂 $COMPANY is an active single-file interview ($next_date). Promote to
  `Interviews/$COMPANY/` and split into jd/prep/questions/feedback + meta.yaml."
- `layout=file AND next_date UNKNOWN AND Stage: recruiter-screen|screen|intro|active` → **INFO**:
  "$COMPANY is active but not scheduled yet. Add `Date: YYYY-MM-DD` when the call is booked."
- `layout=file AND next_date UNKNOWN AND mtime > 14 days` → **P2**:
  "🧹 $COMPANY single-file interview untouched 14d+, no date. Archive or update?"
- `layout=file AND next_date UNKNOWN AND mtime <= 14 days AND no active Stage` → **P1 (low)**:
  "❓ $COMPANY interview file is recent but has no scheduled date. Add `Date: YYYY-MM-DD` line."
- Tracker shows `Interview` but no matching dir OR file → **P1**:
  "📁 Tracker says interview with $X but no vault dir/file. Create `$INTERVIEWS/$X.md` and stash JD."
- Dir-form vault entry with `next_date` UNKNOWN AND mtime > 14 days → **P2**:
  "🧹 $COMPANY interview folder stale (no date, untouched 14d+). Archive or update?"

### 8.5. Evidence / proof-package freshness (gh-resume-builder feeder)

These dirs are signals that new artifacts exist that the mined source-of-truth may not yet reflect.

```bash
NEW_EVIDENCE=$(find "$EVIDENCE" -type f -mtime -7 2>/dev/null | wc -l | tr -d ' ')
NEW_PROOF=$(find "$PROOF_PACKAGE" -type f -mtime -7 2>/dev/null | wc -l | tr -d ' ')
```

Decision rules:
- `NEW_EVIDENCE >= 5` AND `DAYS_SINCE_MINED >= 3` → **P2**:
  "📥 $NEW_EVIDENCE new evidence files this week, mined md is ${DAYS_SINCE_MINED}d stale.
  Consider running `gh-resume-builder` to fold them in."
- `NEW_PROOF > 0` → **INFO**: "📤 New proof-package material exists; consider LinkedIn Featured update."

### 9. Platform diversification check

**Preferred source: `$TMP_CHANNEL` from Step 6.5** (channel parsed directly from batch filename —
no notes-field heuristics, Bash-3.2-compatible). Ledger-side parsing is fallback only.

```bash
# Aggregate channel SUBMIT totals (col 3 = submitted, col 2 = touched)
awk -F'\t' '
  {s[$1]+=$3; t[$1]+=$2; total_s+=$3}
  END{
    for(c in s) {
      pct = total_s > 0 ? (100 * s[c] / total_s) : 0
      printf "%s\t%d submitted (%d touched, %.0f%%)\n", c, s[c], t[c], pct
    }
  }' "$TMP_CHANNEL" | sort -k2 -rn
```

Rules:
- Any single channel > 70% of weekly SUBMIT volume → "Diversify — try the underrepresented channels today."
- LinkedIn Easy Apply is FROZEN, so the old 25/day Easy Apply cap is not a live channel. External ATS uses the daily-50 zero-gate routine, not that cap.
- Only one channel used this week → upgrade diversification recommendation to **P1**.
- If `tracker.csv` shows channels (e.g., Lever, Greenhouse) that don't appear in `$TMP_CHANNEL` →
  **P1 SCHEMA GAP**: "Tracker has submissions on channels not archived in `applications/`.
  Either backfill batch files (`<channel>-batch-YYYY-MM-DD.md`) or update `daily-job-apply`
  to emit them automatically."

### 10. Privacy / opsec spot-check

- Verify Open-to-Work LinkedIn setting matches user's current stealth preference (read from `data/profile.json` or default to OFF for public, ON for recruiters-only).
- Verify `Share profile updates with your network` is OFF (only check, do not flip).
- Surface as INFO only unless mismatch.

## Output dashboard format

Always emit this structure (Markdown, no fluff):

```markdown
# Job Search Status — <YYYY-MM-DD HH:MM BJT>

## 🔴 P0 (blocks everything else)
- <hash drift / missing file / etc, or "None">

## 🟡 P1 (do today)
- <ranked action items with sub-skill to invoke>

## 🟢 P2 (nice to do this week)
- <ranked items>

## 📊 Pipeline snapshot
| Metric | Value |
|---|---|
| Today (ledger / vault submit / vault touched) | N / M / K |
| This week (ledger / vault submit / vault touched) | N / M / K (weekday routine: ~50 verified zero-gate Greenhouse; old weekly floor 20 is historical) |
| Open ManualFinish tabs | N |
| Interviews scheduled (≤7d, vault dir+file) | N (prep missing: M) |
| Unread job emails | N |
| Referral follow-ups due | N |
| Last markdown refresh | Nd ago (cutoff YYYY-MM-DD) |
| New PRs since cutoff | N |
| New evidence files (7d) | N |
| Channel distribution (vault submit, week) | linkedin N% · greenhouse N% · lever N% · ... |
| Tracker/vault channel gap | lever 16 · greenhouse 1 · ... |

## 🧮 Data consistency
| Pair | Drift | Likely root cause |
|---|---|---|
| ledger ↔ vault submit | Δ=N | archive schema gap / missing batch emission / consistent |
| tracker ↔ vault submit | Δ=N | channel normalization gap / archive extra rows / consistent |
| ledger ↔ tracker | Δ=N | tracker upsert race / ledger append race / consistent |

If a schema-gap repair is safe and purely archival, include the exact command:

```bash
python3 /Users/yupeng/.codex/skills/daily-job-apply/scripts/job_archive.py backfill --date YYYY-MM-DD --channels lever greenhouse
```

## 🛠 System health
- BJT window: <write-open / write-banned>
- PDF hash baseline: <pass / DRIFT>
- Skill sync (codex/agents/claude, inode/readlink): <consistent / divergent>
- File presence: <all OK / missing: ...>
- Data consistency: <all consistent / ledger-vault Δ=N / tracker-vault Δ=N / ledger-tracker Δ=N>
- Vault archive layout coverage: <all channels covered / schema gap: ...>

## 🚦 Recommended next action
> Single sentence telling the user *exactly* what to do next, naming the sub-skill.
> Example: "Run `daily-job-apply` for today's batch — 0 submitted, BJT 22:14 (write window open), 12 new gh-resume-builder PR signals not yet promoted to PDF (defer PDF refresh for now)."
```

## Decision routing matrix

| Signal | Recommended sub-skill | Priority |
|---|---|---|
| Hash drift | (no skill — investigate manually) | P0 |
| Missing critical file | (no skill — restore) | P0 |
| Interview ≤ 2d AND no jd.md | (capture JD now, manual) | P0 |
| `NEW_PRS >= 50` or new public artifact | `gh-resume-builder` + later `build_resumes.py` edit | P1 |
| `NEW_PRS >= 20` (but no new artifact) | `gh-resume-builder` (markdown only) | P2 |
| `TODAY_SUBMITTED == 0` AND `VAULT_TODAY == 0` AND BJT OK | `daily-job-apply` | P1 |
| `VAULT_TODAY > 0 AND TODAY_SUBMITTED == 0` | (ledger backfill, manual) | P1 |
| `abs(ledger - vault) >= 3` (submitted drift) | (repair archive or ledger; use `job_archive.py backfill` when tracker explains the gap) | P1 |
| `abs(tracker - vault) >= 3` (submitted drift) | (repair archive or tracker channel normalization) | P1 |
| `abs(ledger - tracker) >= 1` (submitted URL drift) | (inspect exact missing URL; likely tracker upsert race) | P2 |
| `OPEN_MANUAL >= 3` | (no skill — user finishes tabs manually) | P1 |
| Vault dir missing | (Obsidian Vault sync issue, manual) | P1 |
| `unread_job_emails > 0` | `daily-job-apply` triage mode (or just open Gmail) | P1 |
| `LinkedIn recruiter DM` | (no skill — user replies personally) | P1 |
| Interview ≤ 7d, no prep.md | (run interview-prep flow when defined) | P1 |
| Tracker says Interview but no vault dir/file | (create `Interviews/<Company>.md`, stash JD) | P1 |
| `layout=file` single-file interview with future date | (promote to `Interviews/<Company>/` dir, split jd/prep/questions/feedback + meta.yaml) | P1 |
| `layout=file` active `Stage:` but no date | (add `Date:` when scheduled; no promotion yet) | INFO |
| `layout=file` interview file recent (≤14d) but no `Date:` line | (add `Date: YYYY-MM-DD` line) | P1 |
| Tracker channels not in vault archive (e.g. Lever/Greenhouse missing batch file) | (backfill `<channel>-batch-DATE.md`, or fix `daily-job-apply` to emit) | P1 |
| Single channel > 70% of week (vault) | `daily-job-apply` with `--channel=external` hint | P2 |
| `NEW_EVIDENCE >= 5` AND `DAYS_SINCE_MINED >= 3` | `gh-resume-builder` | P2 |
| Stale interview dir (14d+, no date) | (archive or update, manual) | P2 |
| Referral follow-up due | `daily-job-apply` referral channel | P2 |

## Cadence-aware behavior

- **Morning (BJT 06:00–09:00, before write ban)**: focus dashboard on "what to prepare today" — highlight P1 actions queued for after BJT 19:00.
- **Daytime (BJT 09:00–19:00)**: LinkedIn writes stay frozen. External ATS is not under the retired stealth ban. The standing daily-50 routine is still 21:00 Asia/Shanghai. Allow Gmail triage, interview prep, and markdown refresh at any time.
- **Evening (BJT 19:00–00:00, write window open)**: show "act now" framing. If nothing submitted today, escalate to red.
- **Late night (BJT 00:00–06:00)**: same as evening but warn if velocity already met.

## Hard constraints

- ❌ Never run `python3 build_resumes.py` (PDF regeneration belongs to a deliberate human-triggered flow).
- ❌ Never write to `application-ai-agent/*.pdf`.
- ❌ Never apply, send, post, comment, connect, or message on the user's behalf. All "actions" recommended in the dashboard are pointers to other skills.
- ❌ Never call paid LLM APIs from inside this skill; all logic should be deterministic bash + jq + minimal Python.
- ❌ Never silently fix hash drift, skill divergence, or missing files — always surface to user first.
- ✅ ALWAYS finish with the "Recommended next action" single sentence so the user has zero ambiguity about what to do next.

## Anti-patterns

- ❌ Producing a 20-section "comprehensive" status report. The dashboard is a triage tool, not a journal — if a section is empty, omit it.
- ❌ Recommending more than 3 P1 actions per run. Pick the highest-leverage three.
- ❌ Re-running gh-resume-builder more often than weekly unless `NEW_PRS >= 50` or a new public artifact appeared.
- ❌ Scheduling LinkedIn Easy Apply. It is frozen. External ATS / the daily-50 routine is not under the retired BJT 09:00–19:00 stealth ban; the standing clock is still 21:00 Asia/Shanghai.
- ❌ Treating "0 today" at 09:00 BJT as an emergency. It only becomes urgent after 21:00 BJT.

## Current-machine notes (2026-06-02)

- Skills installed at:
  - `~/.codex/skills/{daily-job-apply,gh-resume-builder,job-search-orchestrator}/SKILL.md`
  - `~/.agents/skills/{...}/SKILL.md`
  - `~/.claude/skills/{...}/SKILL.md`
- Skill consistency check should warn if any of these diverge.
- Active gh accounts: `BrickerP` (personal) + `yupeng-dev` (Cookiy work). When checking PR velocity for resume refresh, use `yupeng-dev` (work account). When checking personal-repo activity (quant, AI usage report), use `BrickerP`.
- Historical note only: an older weekly combined target was 20 and an Easy Apply cap was 25. Both are superseded by the 2026-10-25 override (Easy Apply frozen; weekday routine ~50 verified zero-gate Greenhouse on `jobapply2`).
- Vault archive paths confirmed populated as of 2026-06-02:
  - `applications/linkedin-batch-2026-05-31.md` (single-file, table: 83 touched / 45 submitted)
  - `applications/linkedin-batch-2026-06-01.md` (single-file, table: 35 touched / 20 submitted)
  - `applications/lever-batch-2026-06-01.md` (backfilled single-file, table: 16 touched / 16 submitted)
  - `applications/greenhouse-batch-2026-06-01.md` (backfilled single-file, table: 1 touched / 1 submitted)
  - `Interviews/Strativ Group.md` (single-file, layout=file — promotion candidate)
  - `evidence/`, `proof-package/`, `resume-proof/` populated
- Non-LinkedIn archive emission helper: `~/.codex/skills/daily-job-apply/scripts/job_archive.py`.
- Snapshot cutoff format supported: `Resume snapshot cutoff: YYYY-MM-DD` AND `Snapshot: YYYY-MM-DD`.
- Skill consistency check uses inode/readlink — symlink-aware divergence detection (all 3 install dirs are symlinks to `~/.codex/skills/`).
- v4 data consistency splits drift into `ledger↔vault`, `tracker↔vault`, and `ledger↔tracker`.
- v4 ledger parsing supports both `^YYYY-...` and `^- YYYY-...` markdown bullet rows.
- v4 single-file interview parser supports numbered headings like `## 1) JD ...` and `### STAR 1`.
- v4 single-file interviews may use `Stage: recruiter-screen|screen|intro|active` to avoid false P1 when active but not scheduled.
- Bash 3.2 compatible: uses tmp files instead of `declare -A` for channel/day aggregation.
- Stealth defaults from `daily-job-apply`: never contact current-company employees, never use `yupeng@cookiy.com`, US phone `[ph_phone_number_2_ph]` currently inactive (do not submit), no `+86` on US apps, no "relocating from Beijing" in resume/forms.
