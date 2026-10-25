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
  shasum -a 256 Resume_*_1P_EN.pdf Resume_*_1P_ZH.pdf Resume_*_2P_EN.pdf Resume_*_2P_ZH.pdf 2>/dev/null | sort
  diff <(shasum -a 256 Resume_*_1P_EN.pdf Resume_*_1P_ZH.pdf Resume_*_2P_EN.pdf Resume_*_2P_ZH.pdf 2>/dev/null | sort) \
       <(sort pdf-hashes.txt)
) || { echo "STOP: PDF hash drift — confirm with user before applying."; exit 2; }
```

On drift: **STOP**. Do not auto-re-baseline.

### 2. chrome-use（真实 Chrome 连接）

浏览器操作用 `chrome-use`，它连接用户已登录的真实 Chrome（profile: `Lu` / `yplmicro@gmail.com`）。投递统一用命名 session `jobapply2`。**Never grant chrome-use `auth always`.**

```bash
chrome-use browsers                                                          # profile `Lu` must show CONNECTED
chrome-use --session jobapply2 --browser yplmicro@gmail.com tab list --full   # starts the session and prints the `profile:` line
```

If that session sticky-hangs (commands freeze, extension silent), do not thrash it. Open a **new** session name (for example `jobapply3`) with the same `--browser yplmicro@gmail.com`, and record the rename in the run notes. The retired name `jobapply` is not reused. Benign warning `close incomplete: untracked tab` — ignore. After any navigation, refs and the viewport are stale: `snapshot -i` again before the next click or fill.

### 3. Profile check（连接的 Chrome 身份校验）

Profile identity is checked **whenever a `profile:` line prints**, not once per run: closing a session's last tab ends the session, and the next command restarts it on whatever profile chrome-use picks. So pass `--browser yplmicro@gmail.com` on every command that can start the session (`tab list`, `tab new`, `open`). The line must read `Lu (Profile 2, yplmicro@gmail.com)`. Any other profile = **STOP** `wrong-profile` (cleanup: `END-OF-RUN.md` §5). Never submit from any other profile.

The old Gmail same-window pairing check no longer exists. The `yplmicro@gmail.com` Gmail tab is only needed to read Greenhouse email security codes (`END-OF-RUN.md` §3).

### Daily ~50 zero-gate preflight（每日约 50 条零门槛预检）

Run this on the wp Mac **before** a volume run. Target for the weekday routine is **~50 verified zero-gate Greenhouse** submits, not 200 the same night unless the user overrides. All twelve must pass before the first submit. Canonical copy (same list the Grok Bot routine uses):

1. Chrome-use probe: `chrome-use browsers` (Lu CONNECTED) and `chrome-use --session jobapply2 --browser yplmicro@gmail.com tab list --full` → `profile: Lu (Profile 2, yplmicro@gmail.com)`. Also run `TZ=Asia/Shanghai date`.
2. Reconnect or open a new session name if hung (same `--browser`; do not retry a dead session). Record the rename.
3. PDF hash vs `pdf-hashes.txt` (§1). STOP on drift. Confirm the resume PDF path exists.
4. Profile Lu confirmed whenever a `profile:` line prints. Anything else = STOP `wrong-profile`.
5. Blocked companies loaded from `data/blocked-companies.json`. Skip every listed key. **Twilio is listed** — Skip `company-blocked` even when the form looks clean. Do not delete it from the file. Confirm `JOB_APPLY_PHONE` exists in `~/.config/daily-job-apply/env` (never echo the number).
6. Dedupe by job-id path-form **before open**: grep the tracker for `(?:jobs/|token=)(\d{4,})`. `boards.greenhouse.io`, `job-boards.greenhouse.io`, and `embed/job_app?token=` are the same job.
7. Zero-gate Greenhouse queue only for this routine.
8. **≥90s** between verified submits on the same platform family (routine floor; the wider 90–180s band still applies).
9. Close the tab after each verified record. One active apply tab.
10. Stop early if ManualFinish / Blocked dominate the first ~10 probes. Report the four gates. Do not burn the hour.
11. Proof is only a URL containing `/confirmation`, or a security-code field. `bad:0` / `checkValidity()` pass is not a submit.
12. Deliver the run summary to the user in the Grok Bot chat (including a short status when nothing verifiable was submitted).

Visible CAPTCHA / hCaptcha / SMS stay user blockers → `ManualFinish`. Do not solve them.

Recorded bio facts a form may ask, and only these: date of birth `1999-08-03`; OSU graduation year `2021` (already in FROZEN education). Years floor stays **3** (numeric `3`, free text `3+ years`). Do not invent any other bio field.

### 4. Apply role by role（逐个岗位投递）

There is no batch command. `runtime/run-next.sh` is a retirement stub that exits 2, and the CDP/Playwright batch engine is retired (reference only under `archive/2026-10-cdp-retired/`). The agent applies one role at a time with `chrome-use`, following `workflows/04-universal-web-apply.md`: session `jobapply2`, tab labels `<platform>-<company>`, platform playbooks `ATS-GREENHOUSE.md` / `ATS-ASHBY.md`. Identity, contact, phone, work-authorization and every other standard answer come from the FROZEN section of that workflow.

**When the user says apply / go / 投递**: skip dry-run; run real final submit (unless a hard stop applies: CAPTCHA, hash drift, wrong profile, company-blocked).

## User intent: real apply vs dry-run

| User says | Behavior |
|-----------|----------|
| `apply`, `go`, `投递`, `no dry-run`, `direct` | **Real submit** after preflight passes |
| Default / triage / orchestrator only | Dry-run by default |

## LinkedIn freeze (2026-06-03)

Until the user says LinkedIn review is resolved: **no** LinkedIn Easy Apply, profile edits, saves, or messages. External ATS (Ashby/Greenhouse/Lever) via `workflows/04-universal-web-apply.md` — the former BJT 09:00–19:00 write ban was part of stealth and is **retired (2026-10-18)**; applications may run at any time.

> Canonical skill source: `github.com/BrickerP/Personal-Skills` — land changes via **commits**, then sync/install. Do not leave durable pitfalls only on the Mac.

## Canonical references（权威路径）

| Artifact | Path |
|----------|------|
| Skill root | `~/.codex/skills/daily-job-apply/` |
| Apply workflow (per-role procedure, FROZEN answers, pre-submit gate) | `~/.codex/skills/daily-job-apply/workflows/04-universal-web-apply.md` |
| Platform playbooks | `~/.codex/skills/daily-job-apply/ATS-GREENHOUSE.md`, `ATS-ASHBY.md`, `ATS-BLOCKERS.md` |
| Pre-submit gate | `~/.codex/skills/daily-job-apply/scripts/ats_pre_submit_gate.js` |
| Blocked companies | `~/.codex/skills/daily-job-apply/data/blocked-companies.json` |
| GH skip boards | `~/.codex/skills/daily-job-apply/data/gh-skip-boards.json` |
| GH embed skip domains | `~/.codex/skills/daily-job-apply/data/embed-career-domains.json` |
| Ashby skip slugs | `~/.codex/skills/daily-job-apply/data/ashby-skip-slugs.json` |
| Profile / PII | `~/.codex/skills/daily-job-apply/data/profile.json` |
| Tracker (default) | `~/.codex/skills/daily-job-apply/state/tracker.csv` |
| Env overrides | `~/.config/daily-job-apply/env` |
| End-of-run checklist | `~/.codex/skills/daily-job-apply/END-OF-RUN.md` |
| Full skill rules | `~/.codex/skills/daily-job-apply/SKILL.md` |

## After the run

Follow `END-OF-RUN.md`: tracker upsert, ledger append, archive emit, close Submitted tabs, print ManualFinish handoff.
