# Cold-start — context-free agent entry | 冷启动（无需对话上下文）

Read this file first on a fresh machine or new agent session. **No prior conversation context required.**

**Skill home (canonical):** `~/.codex/skills/daily-job-apply/`

## Fixed execution order（固定顺序）

Run these steps **in order** before any application work:

### 1. Curated PDF hash check（简历 PDF 哈希校验）

Resolve `APP_DIR` from `data/profile.json` → `resume_paths`, or env `DAILY_JOB_APPLY_PDF_DIR`, or `~/Documents/resumes`.

```bash
source ~/.codex/skills/daily-job-apply/runtime/skill_paths.sh
APP_DIR="${DAILY_JOB_APPLY_PDF_DIR:-$PDF_DIR}"
(
  cd "$APP_DIR"
  shasum -a 256 Resume_*_1P_EN.pdf Resume_*_2P_EN.pdf 2>/dev/null | sort
  diff <(shasum -a 256 Resume_*_1P_EN.pdf Resume_*_2P_EN.pdf 2>/dev/null | sort) \
       <(sort pdf-hashes.txt)
) || { echo "STOP: PDF hash drift — confirm with user before applying."; exit 2; }
```

On drift: **STOP**. Do not auto-re-baseline.

### 2. Chrome Debug（Chrome 调试端口）

```bash
~/.codex/skills/daily-job-apply/bin/chrome-debug.sh
# or: ~/bin/chrome-debug.sh  (wrapper)
curl -s http://127.0.0.1:9222/json/version | head -c 120
```

`CHROME_PROFILE` defaults to `Profile 2` (override in `~/.config/daily-job-apply/env`).

### 3. yplmicro Gmail tab `windowId` gate（邮箱窗口校验）

**Prerequisite**: Chrome profile with a visible tab titled like `Inbox … yplmicro@gmail.com … Gmail`.

- Find the Gmail target whose title contains `Inbox` and your job-search email.
- Before any ATS fill/submit, call CDP `Browser.getWindowForTarget` on both the application tab and the Gmail tab — **`windowId` must match**.
- Never submit from a window that only shows a work/personal Gmail you are not applying with.

Helper:

```bash
SKILL=~/.codex/skills/chrome-read-write
"$SKILL/scripts/chrome_tabs.sh" mail.google.com
```

### 4. Run apply batch（执行投递）

```bash
~/.codex/skills/daily-job-apply/runtime/run-next.sh
```

Modes: `auto` (default) | `gh` | `ashby` | `manual` — see `$SKILL_ROOT/ROUND-MANIFEST.yaml`.

Legacy wrapper (same behavior): `~/job-hunt/run-next.sh`

**When the user says apply / go / 投递**: skip dry-run; run real final submit (unless a hard stop applies: CAPTCHA, hash drift, wrong window, company-blocked).

## User intent: real apply vs dry-run

| User says | Behavior |
|-----------|----------|
| `apply`, `go`, `投递`, `no dry-run`, `direct` | **Real submit** after preflight passes |
| Default / triage / orchestrator only | Dry-run by default |

## LinkedIn freeze (2026-06-03)

Until the user says LinkedIn review is resolved: **no** LinkedIn Easy Apply, profile edits, saves, or messages. External ATS (Ashby/Greenhouse/Lever) via `run-next.sh` is OK outside BJT 09:00–19:00 write ban.

## Canonical references（权威路径）

| Artifact | Path |
|----------|------|
| Skill root | `~/.codex/skills/daily-job-apply/` |
| Active rounds manifest | `~/.codex/skills/daily-job-apply/ROUND-MANIFEST.yaml` |
| Entry command | `~/.codex/skills/daily-job-apply/runtime/run-next.sh` |
| Adapters (Ashby/GH) | `~/.codex/skills/daily-job-apply/adapters/` |
| Blocked companies | `~/.codex/skills/daily-job-apply/data/blocked-companies.json` |
| GH skip boards | `~/.codex/skills/daily-job-apply/data/greenhouse-skip-boards.json` |
| GH embed skip domains | `~/.codex/skills/daily-job-apply/data/embed-career-domains.json` |
| Ashby skip slugs | `~/.codex/skills/daily-job-apply/data/ashby-skip-slugs.json` |
| Profile / PII | `~/.codex/skills/daily-job-apply/data/profile.json` |
| Tracker (default) | `~/.codex/skills/daily-job-apply/state/tracker.csv` |
| Env overrides | `~/.config/daily-job-apply/env` |
| End-of-run checklist | `~/.codex/skills/daily-job-apply/END-OF-RUN.md` |
| Full skill rules | `~/.codex/skills/daily-job-apply/SKILL.md` |

## One-liner cold start（一条命令链）

```bash
source ~/.codex/skills/daily-job-apply/runtime/skill_paths.sh && \
~/.codex/skills/daily-job-apply/bin/chrome-debug.sh && \
curl -sf http://127.0.0.1:9222/json/version >/dev/null && \
~/.codex/skills/daily-job-apply/runtime/run-next.sh
```

Run PDF hash check separately when curated baselines exist.

## After the batch

Follow `END-OF-RUN.md`: tracker upsert, ledger append, archive emit, close Submitted tabs, print ManualFinish handoff.
