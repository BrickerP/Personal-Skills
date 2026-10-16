---
name: linkedin-application-agent
description: FROZEN and not runnable since 2026-10-15. LinkedIn applications are frozen, and the Chrome Debug / port 9222 / chrome-read-write helpers this skill drove were retired with the Debug Chrome profile; no chrome-use port exists. Do not start LinkedIn Easy Apply runs with it; read it only as reference for a future port. Original purpose - prepare or run LinkedIn Easy Apply batches with approved resume/contact info and conservative truthful defaults.
---

# LinkedIn Application Agent

> **Status (2026-10-15): frozen, not runnable.** LinkedIn applications are frozen (`daily-job-apply/COLD-START.md`, "LinkedIn freeze"), and the Debug Chrome profile, `~/bin/chrome-debug.sh`, port 9222 and the `chrome-read-write` skill this chain drives were removed, so `scripts/easy_apply_batch.cjs` cannot start. No chrome-use port exists. The Chrome Debug sections below are reference for such a port; for live application work use `daily-job-apply/workflows/04-universal-web-apply.md`.

Automate **LinkedIn job preparation and Easy Apply batches** in the user's real **Chrome Debug** profile (retired, see the status note). Use this only when the user explicitly asks to apply, batch apply, continue LinkedIn applications, or turn a LinkedIn application run into a repeatable workflow.

For the user's full stealth job-search workflow (resume/profile context, privacy guardrails, referrals, weekly maintenance, and tracker discipline), use `daily-job-apply` first. This skill is the mechanical LinkedIn Easy Apply subroutine.

LinkedIn Easy Apply stays frozen and **deprioritized vs Greenhouse/Ashby external** official ATS applications unless the user explicitly unfreezes LinkedIn. The old no-US-phone policy is retired: phone fields follow the FROZEN rules in `daily-job-apply/workflows/04-universal-web-apply.md` (US number from `~/.config/daily-job-apply/env`).

## Hard boundaries

- If the run is part of the stealth Bay Area AI job search, first follow `/Users/yupeng/.codex/skills/daily-job-apply/guards/stealth-rules.md`.
- Do **not** emit current-employer legal names, internal project codenames, client names, revenue numbers, org/person names, private repo names, internal URLs, or non-public metrics in outbound application answers/materials.
- During Beijing time 09:00-19:00, do not perform LinkedIn write actions; read-only inspection is allowed.
- Do **not** enable public Open to Work, make posts, follow companies, message recruiters, or submit non-LinkedIn external applications unless the user explicitly asks.
- Do **not** invent credentials, citizenship, dates, employers, degrees, phone numbers, or sponsorship status.
- Do **not** bypass CAPTCHA/SMS/email verification. Stop and ask if a verification step appears.
- Default contact preference: **email**. Phone fields follow the FROZEN rules in `daily-job-apply/workflows/04-universal-web-apply.md` (US number from `~/.config/daily-job-apply/env`, never typed into a command or reply); the old "no active phone" stop is retired.
- For this user, current approved defaults:
  - Email: `yplmicro@gmail.com`
  - Phone: `$JOB_APPLY_PHONE` from `~/.config/daily-job-apply/env`; a form that rejects it or demands `+86` → stop with `phone-rejected`.
  - LinkedIn: `https://www.linkedin.com/in/yupeng-lu-845a0b411/`
  - Source of truth for this LinkedIn URL is `/Users/yupeng/.codex/skills/daily-job-apply/data/profile.json`; do not infer the current URL from historical batch logs.
  - Resume strategy: use the current curated English PDF artifacts:
    - Default / high-volume Easy Apply -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`
    - Explicit high-priority, referral, or manual-review application -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf`
    - Older buckets (`AI Agent Infra`, `Backend Platform`, `General SWE`) must resolve to the 1P English PDF unless the user explicitly asks for 2P.
  - Batch log directory: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/applications/`
  - Markdown application ledger: `/Users/yupeng/job-hunt/application-ledger.md`
  - Tracker CSV: `/Users/yupeng/job-hunt/tracker.csv`
- Work authorization truth table:
  - Authorized to work in the US: **Yes**
  - Needs sponsorship now/future: **No**
  - U.S. citizen: **No**
  - U.S. permanent resident / green card: **Yes**. Any "protected individual" or other legal-status wording outside the FROZEN table in `daily-job-apply/workflows/04-universal-web-apply.md`: stop (ManualFinish).
- Company cap: never submit more than 20 applications to one company across all time. `Speechify` is hard-blocked because the tracker already exceeds the cap.

## Conservative answer policy

Answer only when the answer is supported by the profile/resume/current user facts.

Safe defaults:
- Demographics / race / gender / veteran / disability: `Prefer not to answer` / `I do not want to answer`.
- Salary expectation: `160000` unless a role's range makes a higher/lower answer obvious.
- Years: follow the FROZEN years rule in `daily-job-apply/workflows/04-universal-web-apply.md` (derived from `professional_since`, 3 as of 2026-10; a skill never exceeds the total; never round up). The old per-skill figures (Python 5 and so on) are retired.
- Contact preference: `Email` when available.
- Company follow checkbox: uncheck.

Stop/skip instead of guessing on:
- CAPTCHA, SMS/email verification, or phone-call verification.
- Exact-location claims (e.g. “Are you located in San Diego?”) unless explicitly true or already approved.
- Privacy/data-processing consent questions that are not normal LinkedIn submission boilerplate.
- Complex date ranges, work-history reconstruction, or unexplained required selects.
- Anything that asks for security clearance, government citizenship-only eligibility, or legally sensitive attestations beyond the truth table above.

## Chrome Debug / chrome-read-write workflow (retired 2026-10-15, reference only)

Retired: the Debug Chrome profile, `~/bin/chrome-debug.sh`, port 9222 and the `chrome-read-write` skill no longer exist, so none of the commands below run. They are kept as the mechanics a future chrome-use port would have to cover.

Preflight:

```bash
~/bin/chrome-debug.sh
curl -s http://127.0.0.1:9222/json/version | head -c 120
SKILL=/Users/yupeng/.codex/skills/chrome-read-write
"$SKILL/scripts/chrome_tabs.sh" linkedin.com
```

Resolve the LinkedIn target id from `target=...`. Prefer a tab already on `linkedin.com/jobs`; otherwise open/navigate the profile tab.

Useful read/write primitives:

```bash
CHROME_EVAL_URL_MUST_CONTAIN=linkedin.com \
  "$SKILL/scripts/chrome_eval.sh" <target_id> "$SKILL/scripts/read_page.js"

CHROME_EVAL_URL_MUST_CONTAIN=linkedin.com \
  "$SKILL/scripts/click_text.py" <target_id> 'Easy Apply'

CHROME_EVAL_URL_MUST_CONTAIN=linkedin.com \
  "$SKILL/scripts/chrome_eval.sh" <target_id> 'JSON.stringify({title: document.title, url: location.href})'
```

For file uploads, use CDP `DOM.setFileInputFiles` (the batch script does this automatically). Do not use AppleScript or regular Chrome unless the user asks for a fallback.

## Batch workflow (reference only; LinkedIn is frozen and the runner cannot start)

1. Confirm Chrome Debug is logged into the intended LinkedIn account. The batch script now fails fast when the visible `/in/<slug>` does not match `LINKEDIN_EXPECTED_PROFILE` / `LINKEDIN_PROFILE`; do not bypass with `LINKEDIN_ALLOW_PROFILE_MISMATCH=1` unless the user explicitly approved the mismatch.
2. Confirm resume/contact defaults and target count.
3. Count same-day LinkedIn Easy Apply `Submitted` ledger rows before the run; reduce the target to the remaining `LINKEDIN_DAILY_CAP` capacity and stop at 0 remaining.
4. Search conservative targets first:
   - `AI Agent Engineer`, `AI Platform Engineer`, `Backend Engineer AI Platform`
   - `Developer Tools Engineer AI`, `Founding Engineer AI`, `Full Stack AI Engineer`
   - Locations: `United States`, `San Francisco Bay Area`, Remote/Hybrid when available.
5. Run Easy Apply with conservative submit mode.
6. Append every outcome to the markdown batch log.
7. Append every touched job to `/Users/yupeng/job-hunt/application-ledger.md` as one Markdown line: `timestamp | status | name | url`.
8. Upsert every touched job in `/Users/yupeng/job-hunt/tracker.csv`; if a URL already exists, update status/stage/notes instead of silently skipping it.
9. Final report: submitted count, skipped/blocked count, resume variant counts, log path, ledger path, tracker path, daily-cap count, and any review flags.

Canonical command (retired: it needs the removed Debug Chrome and `chrome-read-write`, so do not run it; kept as reference for a future chrome-use port):

```bash
LINKEDIN_SUBMIT=1 \
LINKEDIN_TARGET_NEW=30 \
LINKEDIN_EMAIL='yplmicro@gmail.com' \
LINKEDIN_PHONE='' \
LINKEDIN_PROFILE='https://www.linkedin.com/in/yupeng-lu-845a0b411/' \
LINKEDIN_EXPECTED_PROFILE='https://www.linkedin.com/in/yupeng-lu-845a0b411/' \
LINKEDIN_RESUME_STRATEGY='auto' \
node /Users/yupeng/.codex/skills/linkedin-application-agent/scripts/easy_apply_batch.cjs
```

Optional env:
- `LINKEDIN_TARGET_ID=<target>`: force one Chrome tab. If omitted, the script chooses a LinkedIn jobs/profile tab.
- `LINKEDIN_LOG_PATH=<path>`: custom markdown log path.
- `LINKEDIN_SEARCHES_JSON='[["AI Agent Engineer","United States"],["Backend Platform Engineer","San Francisco Bay Area"]]'`
- `LINKEDIN_RESUME=<pdf>`: override auto-selection with one explicit PDF for the entire run.
- `LINKEDIN_RESUME_STRATEGY=auto`: default; choose AI Agent / Backend Platform / General SWE by JD title/card text.
- `LINKEDIN_EXPECTED_PROFILE=<profile-url>`: required account guard; defaults to `LINKEDIN_PROFILE`.
- `LINKEDIN_ALLOW_PROFILE_MISMATCH=1`: emergency explicit override only, never use silently.
- `LINKEDIN_DAILY_CAP=25`: same-day LinkedIn Easy Apply submission cap.
- `JOB_TRACKER=/Users/yupeng/job-hunt/tracker.csv`: tracker CSV upsert path.
- `LINKEDIN_DRY_RUN=1`: navigate and log candidates without submitting.

## Verification

After the run:

```bash
python3 - <<'PY'
from pathlib import Path
p=Path('/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/applications/linkedin-batch-2026-05-31.md')
rows=[l for l in p.read_text().splitlines() if l.startswith('|') and l.split('|')[1].strip().isdigit()]
print('submitted', sum('| Submitted |' in r for r in rows))
print('blocked', sum('| Blocked |' in r for r in rows))
print('skipped', sum('| Skipped |' in r for r in rows))
print('ai-agent resumes', sum('resume uploaded:AI Agent:' in r or 'resume=AI Agent:' in r for r in rows))
print('backend resumes', sum('resume uploaded:Backend Platform:' in r or 'resume=Backend Platform:' in r for r in rows))
print('general resumes', sum('resume uploaded:General SWE:' in r or 'resume=General SWE:' in r for r in rows))
PY
```

If the user asks “最后有一个 save?”: LinkedIn Easy Apply's terminal action is usually **Submit application**, not Save. Save only bookmarks the job. Do not count a job as submitted unless the listing or log confirms `Applied`, `Application submitted`, or a successful post-submit state.
