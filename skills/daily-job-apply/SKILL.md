---
name: daily-job-apply
description: Use when the user wants a daily workflow for US/Bay Area AI Infra, ML Systems, AI Platform, agent infrastructure, backend AI platform, or developer-tools job search. Covers resume/profile context, chrome-use LinkedIn preparation, referrals, Easy Apply batches, weekly LinkedIn maintenance, privacy guardrails, templates, and tracker updates. (Stealth retired 2026-10-18 — real names allowed; see guards/stealth-rules.md.)
---

# Daily Job Apply

Run a Bay Area-focused AI infrastructure job-search workflow for Yupeng Lu. This is the top-level workflow skill; `linkedin-application-agent` (the mechanical LinkedIn Easy Apply subroutine) is frozen and not runnable since 2026-10-15.

## Doc index

| Doc / path | Role |
|------------|------|
| [COLD-START.md](COLD-START.md) | Fixed agent startup: PDF hash → chrome-use profile check → `workflows/04-universal-web-apply.md` |
| [END-OF-RUN.md](END-OF-RUN.md) | Post-run: report, Greenhouse email-code flow, close Submitted tabs, wrong-profile cleanup, tracker/ledger/archive mapping |
| [INSTALL.md](INSTALL.md) | Fresh install + migration from old `~/job-hunt` / `~/.omx` layout |
| [README-FOR-FRIENDS.md](README-FOR-FRIENDS.md) | 3-step friend onboarding for FULL zip |
| [ATS-EVOLUTION.md](ATS-EVOLUTION.md) | Adapter/playbook registry, harvest and evolution loop |
| [workflows/04-universal-web-apply.md](workflows/04-universal-web-apply.md) | Per-role chrome-use procedure for external ATS + the **FROZEN standard answers** (single source of truth for identity, phone, location, work authorization, years, education, AI usage) |
| `ATS-GREENHOUSE.md` / `ATS-ASHBY.md` / `ATS-BLOCKERS.md` | Platform playbooks and how to read the old blocker log (Lever has no playbook: workflow 04 only) |
| `scripts/ats_pre_submit_gate.js` | Pre-submit gate: `chrome-use eval --stdin` right before the final Submit |
| `archive/2026-10-cdp-retired/` | Retired CDP / Playwright / AppleScript engine, reference only |
| [ROUND-MANIFEST.yaml](ROUND-MANIFEST.yaml) | **Orphaned**: batch rounds of the retired engine |
| `adapters/` | Sourcing helpers and **orphaned** batch runners (they call the archived adapters) |
| `runtime/` | Path helpers; `run-next.sh` is a retirement stub (exits 2); the round runners are **orphaned** |
| `data/blocked-companies.json` | Company keys hard-blocked by `job_dedupe_check.py` |
| `data/gh-skip-boards.json` / `data/gh-priority-boards.json` | Greenhouse board skip / priority lists (reference for the agent) |
| `data/ashby-skip-slugs.json` | Ashby slug skip list |
| `data/embed-career-domains.json` | GH embed career-site URL filter |
| `data/profile.json.example` | Template profile; copy to `data/profile.json` |
| `state/tracker.csv` | Default tracker (override via env) |

**Canonical skill root**: `~/.codex/skills/daily-job-apply/` — all runtime paths are `$SKILL_ROOT`-relative. Optional overrides: `~/.config/daily-job-apply/env`.

## Cold-start migration

**No conversation context required.** Fresh agents: read [COLD-START.md](COLD-START.md) only — do not depend on chat history.

1. `COLD-START.md` — PDF hash → chrome-use profile check
2. `workflows/04-universal-web-apply.md` — per-role procedure and the FROZEN standard answers (single source of truth)
3. `data/*.json` — blocked companies, GH skip boards, embed domains, Ashby skip slugs
4. `END-OF-RUN.md` — post-run tracker/ledger/archive/tab cleanup

User says **apply / go / 投递** → real submit (no dry-run) after preflight passes.

## Non-negotiable defaults

- Target strategy: broad high-volume funnel across US/Bay Area/Remote software roles. Do not over-filter for precision; include general Backend / Full-stack / Platform / Infra / ML / AI roles. Mandatory seed lane every run: include the most relevant Agent / AI Infra / ML Systems roles first.
- Per-company cap: never submit more than 20 applications to the same company across all time. `Speechify` is hard-blocked because the historical tracker already has far more than the cap. Treat `company-blocked` and `company-cap-reached` from the dedupe guard as hard stops.
- Email (resume header AND form fields): `yplmicro@gmail.com`. Never use a company email. If multiple Gmail tabs/accounts are open, identify by visible title/account text and use only the `yplmicro@gmail.com` mailbox for verification codes and job-search email. Never read/use `yupeng@cookiy.com` for job applications. `yplmicro@outlook.com` exists but is NOT the active job-search address — gmail is the source of truth.
- Phone: the US number is filled into every phone field, optional or required (decision 2026-10-15; temporary). It lives only in `~/.config/daily-job-apply/env` as `JOB_APPLY_PHONE`; expand the variable in the shell and never type, print or commit the digits. The China number (`JOB_APPLY_PHONE_CN`) is never entered on a US application and the retired `+1-510` number is never used again. A form that rejects the US number or demands `+86` → `ManualFinish` with blocker `phone-rejected`. SMS-consent checkbox → No; an SMS/phone **verification** step → `ManualFinish`. Details: `workflows/04-universal-web-apply.md` → FROZEN → Phone.
- Work authorization string for resume / form fields: `US Permanent Resident — No sponsorship required, now or in the future`.
- Resume location string: `San Francisco Bay Area`. **Do NOT add "relocating from Beijing"** in resume header or in application form free-text fields (privacy decision; the curated PDFs deliberately omit it). Only mention current physical location when a recruiter directly asks.
- LinkedIn account: verify live; expected current profile is `https://www.linkedin.com/in/yupeng-lu-845a0b411/`. Source of truth is `data/profile.json`; do not infer the current URL from historical batch logs.
- Use `chrome-use` against the user's real, already-logged-in Chrome only for authenticated LinkedIn pages. Do not substitute sandbox browser state for LinkedIn/account-sensitive checks.
- LinkedIn application freeze (2026-06-03): until the user explicitly says the LinkedIn review/checkpoint is resolved, do not use LinkedIn Easy Apply, LinkedIn external-apply launch flows, LinkedIn profile edits, LinkedIn saves, LinkedIn messages, or LinkedIn recruiter actions. You may only read existing LinkedIn status if the user asks.
- Browser channel: all browser work runs through `chrome-use`, which drives the user's real, already-logged-in Chrome (profile: `Lu` / `yplmicro@gmail.com`) and connects to the running Chrome by itself.
- Chrome account isolation: every application tab must live in the connected profile `Lu` / `yplmicro@gmail.com`. Any chrome-use command that starts or restarts a session prints a `profile:` line (closing a session's last tab ends it, so this recurs mid-run); it must read `Lu (Profile 2, yplmicro@gmail.com)`, otherwise STOP (`wrong-profile`, `END-OF-RUN.md` §5). Open application tabs only with `chrome-use --session jobapply --browser yplmicro@gmail.com tab new --label <platform>-<company> "<url>"`, confirm them with `tab list --full`, and keep a `yplmicro@gmail.com` Gmail tab available for verification codes. Never submit from any other profile.
- External ATS safety mode: do not bulk-create application tabs. Open one at a time in the `jobapply` session, then re-check `chrome-use --session jobapply tab list --full`.
- Anti-bot posture: do not run high-speed script-only upload/fill/submit loops on Lever, Ashby, Greenhouse, Workday, or custom ATS pages. Use one page at a time, insert human-scale waits between upload/fill/final submit, read back required-field validity and page text, and stop on the first spam, CAPTCHA, verification, or unusual challenge signal. Do not retry the same final submit after an anti-bot warning.
- Resume selection default (path is absolute, curated, **never regenerated by this skill**):
  - Use `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf` for outbound English applications unless the user explicitly asks for a different generated variant.
  - Use `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf` only for explicit high-priority, referral, or manual-review applications where a denser two-page resume is worth the extra length.
  - The older automation aliases `Resume_YupengLu_AI_Agent_Infra.pdf`, `Resume_YupengLu_Backend_Platform.pdf`, and `Resume_YupengLu_General_SWE.pdf` may be absent. Resolve those legacy buckets to the 1P English AI Agent Engineer PDF instead of failing or regenerating PDFs.
  - If future variants are restored, prefer the most specific bucket in this order: AI Agent, Backend Platform, General SWE. Do not let broad "General SWE" win when the title/JD has AI/ML/LLM/agent signals.

## Curated PDF integrity (HARD RULE)

The current recruiter-facing application artifacts are generated by `curated-script/build_resumes.py` and must not be modified outside that script.

Before each run, verify hashes match the recorded baseline:

```bash
APP_DIR="/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent"
(
  cd "$APP_DIR"
  shasum -a 256 Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf \
                Resume_YupengLu_AI_Agent_Engineer_1P_ZH.pdf \
                Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf \
                Resume_YupengLu_AI_Agent_Engineer_2P_ZH.pdf
  diff <(shasum -a 256 Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf \
                       Resume_YupengLu_AI_Agent_Engineer_1P_ZH.pdf \
                       Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf \
                       Resume_YupengLu_AI_Agent_Engineer_2P_ZH.pdf | sort) \
       <(sort pdf-hashes.txt)
) || {
  echo "WARNING: curated PDF hashes differ from baseline. Stop and confirm with user."
  exit 2
}
```

If a hash differs from `pdf-hashes.txt`:
- STOP the run.
- Surface to the user: "PDF hash drift detected on `<filename>`. Likely cause: someone (skill or script) regenerated the PDF. Do you want to (a) re-baseline hashes and proceed, or (b) inspect what changed before continuing?"
- Never auto-re-baseline without user confirmation.

## Hard preflight before every run

1. Read `guards/stealth-rules.md`.
2. ~~Check Beijing time; BJT 09:00–19:00 makes LinkedIn read-only.~~ **Retired 2026-10-18** with stealth. LinkedIn writes remain frozen for unrelated reasons (`COLD-START.md` LinkedIn freeze); no other time-window restriction applies.
3. Verify chrome-use is connected to the real Chrome and the intended LinkedIn account is open/logged in:
   ```bash
   chrome-use browsers
   chrome-use tab list --full
   ```
   Browser work uses `chrome-use`, which drives the user's real, already-logged-in Chrome (profile: `Lu` / `yplmicro@gmail.com`).
4. Verify the yplmicro Chrome profile before any non-LinkedIn ATS write:
   - Before opening, filling, uploading, or submitting any ATS/company role, run the duplicate guard:
     ```bash
     python3 ~/.codex/skills/daily-job-apply/scripts/job_dedupe_check.py \
       --company "<Company>" \
       --role "<Role>" \
       --url "<canonical JD/application URL>" \
       --company-cap 20
     ```
     Exit code `20` / `duplicate-url`, `duplicate-role`, or `company-cap-reached` is a hard stop: do not reopen, refill, or resubmit the role. If the JSON reports same-company submitted matches under the cap, continue only when the URL is different and the role is intentionally distinct.
   - Check the `profile:` line whenever the `jobapply` session prints one (its first command, and again after the session ended because its last tab closed): it must read `Lu (Profile 2, yplmicro@gmail.com)`. Anything else = STOP (`wrong-profile`).
   - Open every application tab with `chrome-use --session jobapply --browser yplmicro@gmail.com tab new --label <platform>-<company> "<url>"` and confirm it with `tab list --full` before filling or submitting.
   - If an application page is open outside the `jobapply` session, reopen the URL with `tab new` in the session. Never close a tab you did not open.
   - Immediately before final submit, run:
     ```bash
     chrome-use --session jobapply eval --stdin < ~/.codex/skills/daily-job-apply/scripts/ats_pre_submit_gate.js
     ```
     The output starts with an upgrade-notice line and an `eval @ <url>` line, then the JSON verdict. Submit only when `ok` is `true`. Any blocker means do not submit; record `ManualFinish` or `Blocked` from the reported code (`workflows/04-universal-web-apply.md` → Pre-submit gate).
5. Before any LinkedIn profile write, confirm Settings → Visibility → `Share profile updates with your network` is OFF. During the 2026-06-03 LinkedIn freeze, skip LinkedIn writes entirely.
6. Load `data/profile.json` and use only redacted fields for outbound resume, cover letter, LinkedIn messages, profile text, and application answers.
7. Dry-run all private messages, applications, profile changes, and final submit/send/save actions by default. If the user explicitly says direct/go/no dry-run for the current run, proceed to final application submit/send steps except where strict stop conditions apply.
8. **Curated PDF hash preflight** (see "Curated PDF integrity" above). STOP on drift.

## Channels

### Channel 1: Referral workflow
Use `workflows/01-referral.md` when targeting a specific company or building a warm pipeline.

### Channel 2: Easy Apply workflow
Use `workflows/02-easy-apply.md` for bounded LinkedIn Easy Apply batches.

### Channel 3: Weekly LinkedIn maintenance
Use `workflows/03-weekly.md` once per week for recruiter-visible maintenance.

### Channel 4: Universal web / official ATS workflow
Use `workflows/04-universal-web-apply.md` for jobs reached from LinkedIn external apply, company career pages, Greenhouse, Lever, Ashby, Workday, or custom intermediate platforms.

### Greenhouse sourcing classifier

Before high-volume non-LinkedIn Greenhouse work, build a classified queue:

```bash
python3 /Users/yupeng/.codex/skills/daily-job-apply/scripts/greenhouse_sourcing.py
```

**Canonical layout** (all under skill root):

| Layer | Path | Role |
|-------|------|------|
| Sourcing / guards | `scripts/` | Classifiers, dedupe, archive, `ats_pre_submit_gate.js` |
| Applying | `workflows/04-universal-web-apply.md`, `ATS-*.md` | The agent applies role by role with `chrome-use`; there is no apply script |
| Retired engine | `archive/2026-10-cdp-retired/` | Reference only |

There is no single entry command any more: `runtime/run-next.sh` is a retirement stub (prints a notice, exits 2).

Use only `status=auto_candidate` rows for agent-run final submissions. Treat
`status=manual` rows as ManualFinish/review items unless the blocker is
explicitly resolved. The classifier rejects mandatory cover letter, explicit
anti-AI/challenge prompts, already-known tracker URLs, and non-engineering
titles before browser work begins. A mandatory phone question is only a
`phone-required` caution now, because the US number is always filled (FROZEN →
Phone). It also marks modern Greenhouse pages with any required React Select
mirror as manual, because filling only the DOM input leaves the React state
empty and the submit is rejected. By hand, open the dropdown and pick the option
(`pick @eN --option "<text>"`), then re-read the value (`ATS-GREENHOUSE.md`).

For Lever official boards, build a broad candidate queue before browser work:

```bash
python3 /Users/yupeng/.codex/skills/daily-job-apply/scripts/lever_sourcing.py
```

Lever rows are only sourcing candidates. Before opening/filling any row, still
run `job_dedupe_check.py`, inspect the live form, and stop on verification,
spam, CAPTCHA, a phone field that rejects the US number, or unknown required
questions. Lever has no playbook: follow `workflows/04-universal-web-apply.md`.

## External ATS playbooks

The batch playbooks of the retired engine (`round{N}-batch.sh`, `runtime/greenhouse/run_round18.py`, `manual-retry-runner.py`, the Ashby probe-first gate) are **orphaned**: they call the archived adapters and must not be run. Platform knowledge now lives in:

- Greenhouse → `ATS-GREENHOUSE.md`
- Ashby → `ATS-ASHBY.md`
- How to read the old failure labels → `ATS-BLOCKERS.md`
- Lever / Workday / custom forms → `workflows/04-universal-web-apply.md` (no playbook)

### Source order when Ashby is saturated

When tracker `exclude_known` (unique submitted URLs) **> 1500**, dict-only Ashby slug mining yields diminishing returns. Default order:

1. **Greenhouse** — `scripts/greenhouse_sourcing.py`
2. **Lever** — `scripts/lever_sourcing.py`, then apply by hand
3. **Ashby** — only when a fresh slug mine still returns rows

### Greenhouse notes

- **Embed skip** at sourcing: `adapters/greenhouse_embed_skip.py` drops embedded career sites (vectra.ai, zipline.com, sambanova.ai, `careers.*`); they time out.
- **Email verification** (`security-input-*` fields) is agent-solvable: read the code from the yplmicro Gmail tab and enter it (`END-OF-RUN.md` §3). The batch precheck that skipped these roles (`skip-email-verification`) is gone.

### ManualFinish

ManualFinish tabs are handed to the user with a bare `keep` (the tab leaves the `jobapply` session and stays open until the user closes it); print the handoff list in the terminal (`workflows/04-universal-web-apply.md` → ManualFinish handoff). The CSV queue and `manual-retry-runner.py` are retired.

## Target sourcing surfaces

Source broadly from LinkedIn Jobs, LinkedIn external apply, company career pages, Greenhouse, Lever, Ashby, Workday, YC/Wellfound/VC portfolio boards, recruiter-shared roles, staffing posts, startup job boards, and AI infra OSS/company networks. High-volume mode is allowed: do not discard reasonable general SWE/backend/full-stack/platform roles merely because they are not perfect matches. However, every batch must include an Agent / AI Infra / ML Systems seed lane so the best-fit roles are always represented.

## Sustainable operating cadence

Use this cadence unless the user gives a one-off override:

- **Daily application run**: outside BJT 09:00–19:00, run preflight (including curated PDF hash check), source roles, apply/prepare applications, update `~/job-hunt/application-ledger.md` and `~/job-hunt/tracker.csv`, print manual-finish tabs directly in the final response.
- **Daily response triage**: check job-search Gmail/LinkedIn replies, update tracker stages, identify interviews / rejections / recruiter follow-ups / manual-finish pages still open.
- **Referral lane**: 5–10 referral/HR contacts per active search day; never contact current-company employees or likely current-company alumni.
- **Weekly metrics review**: summarize submissions by channel, resume variant, role family, response rates, interview rates, rejection rates, manual-finish blockers, and CAPTCHA/platform issues. Use this to tune search keywords, resume variant priority, and application-channel mix.
- **Weekly evidence refresh** (separate skill): run `gh-resume-builder` to update `source-of-truth/resume_yupeng_{en,zh}.md`. That skill will surface "what's new and which of the 3 PDFs it likely belongs in" — review those suggestions, decide if any should land in the curated PDFs, then update `curated-script/build_resumes.py` accordingly and re-run it. **`gh-resume-builder` never touches the application PDFs.**
- **Curated PDF refresh** (manual / Mira-assisted, not automated): edit `curated-script/build_resumes.py`, run it, re-baseline hashes:
  ```bash
  cd /Users/yupeng/Documents/Obsidian\ Vault/Resume_YupengLu/application-ai-agent
  python3 ../curated-script/build_resumes.py
  shasum -a 256 Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf \
                Resume_YupengLu_AI_Agent_Engineer_1P_ZH.pdf \
                Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf \
                Resume_YupengLu_AI_Agent_Engineer_2P_ZH.pdf > pdf-hashes.txt
  ```
  Do NOT regenerate PDFs for every commit; refresh when the source ledger gains a new meaningful theme, before high-priority applications, or before interviews.
- **Interview-prep run**: when an interview is scheduled, build a company/JD-specific prep pack from the source ledger and proof package: JD keyword map, selected resume variant, 5 STAR stories, system-design deep dives, likely behavioral questions, compensation/authorization script, and disclosure-safe current-company wording.

## Vault application archive emission

`~/job-hunt/tracker.csv` and `~/job-hunt/application-ledger.md` are operational records. The Obsidian Vault `applications/` tree is the physical archive that `job-search-orchestrator` reconciles against.

After any **verified successful submission** outside the LinkedIn Easy Apply helper (Lever, Greenhouse, Ashby, Workday, direct/company ATS), update tracker/ledger and then emit one idempotent batch row:

```bash
python3 /Users/yupeng/.codex/skills/daily-job-apply/scripts/job_archive.py emit \
  --channel "<Channel from tracker, e.g. Lever official>" \
  --date "$(TZ=Asia/Shanghai date +%Y-%m-%d)" \
  --status Submitted \
  --company "<Company>" \
  --role "<Role>" \
  --jd-url "<JD_URL>"
```

Rules:
- Normalize channel names through the helper: `Lever official` -> `lever`, `Greenhouse official` -> `greenhouse`, `Ashby Direct` -> `ashby`, `Workday` -> `workday`, company/direct pages -> `direct`.
- The helper writes `applications/<channel>-batch-YYYY-MM-DD.md` with `| # | Status | Company | Role | JD_URL |`.
- The helper is idempotent using URL plus `(company, role)` keys; re-running it must not duplicate rows.
- LinkedIn Easy Apply already writes its own `linkedin-batch-YYYY-MM-DD.md`; do not double-emit LinkedIn rows unless repairing a known archive gap.
- `ManualFinish`, `Blocked`, and `Skipped` remain tracker/ledger records by default. Only archive them when explicitly doing evidence backfill.

## Monitoring dashboard fields

Track these fields in `tracker.csv`, `application-ledger.md`, and final reports:

- Channel: LinkedIn Easy Apply, LinkedIn external, Greenhouse, Lever, Ashby, Workday, company site, referral, HR/recruiter.
- Resume variant: AI Agent Infra, Backend Platform, General SWE, or manual override.
- Status: Submitted, ManualFinish, Blocked, Skipped, ReferralContacted, FollowUpDue, Interview, Rejected, Offer.
- Blocker type: platform-anti-bot, phone-rejected, skip-email-verification, invalid-required-fields, unsupported-required, login-required, manual-finish-needed (ManualFinish: the form is prepared, the final step is blocked); stale-job, form-not-loaded, submit-button-not-found, resume-upload-missing, account/platform-limit, network/page-load, unsafe-question (Blocked: the page could not be prepared or the role is unsafe); wrong-profile (stops the whole run, not a row).
- Follow-up date/window and next action.
- Reply source: Gmail, LinkedIn, ATS email, recruiter DM.
- Quality notes: JD fit, keywords missing, unusual required questions, compensation/range, location constraints.

## Manual-finish policy

Email verification codes are agent-solvable when the relevant mailbox is available/logged in (for this search, `yplmicro@gmail.com`). The agent should read Gmail, extract the code, enter it, and submit if all other fields are safe. The Greenhouse `security-input-*` flow is in `END-OF-RUN.md` §3.

If a page is fully or mostly filled but final submit is blocked by visible CAPTCHA/hCaptcha, SMS/phone verification, graphical anti-bot challenge, a phone field that rejects the US number or demands `+86` (`phone-rejected`), or an unknown final confirmation step that cannot be safely resolved from the provided profile, do not close the page. Hand the Chrome tab to the user with a bare `keep` (it leaves the session and stays open until the user closes it), record the role in `application-ledger.md` as `ManualFinish` in the `END-OF-RUN.md` §6 line format (blocker as `manual-finish-needed:<blocker>` in the notes), and print the manual handoff directly in the terminal/final response: company, role, URL, tab label if known, exact remaining human action, and whether fields appear filled. Do not maintain a separate manual-finish Markdown queue.

## Stop conditions and caps

Stop immediately on visible CAPTCHA/hCaptcha, graphical bot-check, SMS/phone verification, chrome-use not connected to the yplmicro profile, unexpected account mismatch, current-company employee/contact risk, legally sensitive uncertainty, **curated PDF hash drift**, or any final action lacking user confirmation when the current run has not explicitly allowed direct submission. Do not stop merely for ordinary email verification or invisible reCAPTCHA token generation.

Stop immediately for the current platform and record `ManualFinish` (blocker `platform-anti-bot`) when the page says any of: `possible spam`, `error verifying your application`, `verify your application`, `unusual traffic`, `automated`, `bot`, `too many attempts`, or equivalent. Do not retry the same submit in the same run; repeated retries are account-risk behavior.

The pre-submit gate (`scripts/ats_pre_submit_gate.js`) is authoritative for external ATS pages. If it returns `ok: false` (`danger-text`, `invalid-required-fields`, `aria-invalid-fields`, `no-form-fields`), do not click Submit. Fix only safe field omissions; never bypass `danger-text` in the same run. A wrong `profile:` line stops the whole run (`wrong-profile`).

Daily caps:
- LinkedIn connection requests: 10/day.
- Referral messages: 5–10/day.
- LinkedIn Easy Apply submissions: 25/day.
- Profile views: 200/day.
- InMail: Premium Career quota, usually 5/month.

External ATS cadence and caps:
- Default steady-state target is **up to 20 verified submissions/hour**, not a burst target.
- Do not attempt 200 same-night submissions unless the user explicitly accepts the account/platform risk after seeing a safety warning. Prefer 20-40 high-confidence external submissions/night while LinkedIn is under review.
- Use one active final-submit page at a time. Source/filtering can happen in parallel, but upload/fill/submit must be sequential and slow.
- Leave 90-180 seconds between successful external ATS submissions on the same platform family, and longer after any verification warning.
- Favor company-owned direct forms, recruiter email/referral, Simplify-compatible pages, and Greenhouse/Lever pages with no challenge. Treat Ashby final submit as high-risk after one possible-spam warning unless completed manually.

Warn at 70% of any cap, and stop at 100%.

## Output template

At the end of every run, report:

- Date and time window.
- Channels used.
- Companies/roles touched.
- Submitted/sent/saved/dry-run counts.
- Resume variant counts and any suspicious resume-selector mismatch, especially obvious AI/ML/LLM/agent titles that received General SWE.
- **Curated PDF hash check result**: pass / drift.
- Tracker path and rows appended.
- Markdown application ledger path and rows appended: `~/job-hunt/application-ledger.md`.
- Blocks, review flags, failure classification (`skill-gap`, `platform-anti-bot`, `phone-rejected`, `skip-email-verification`, `invalid-required-fields`, `unsupported-required`, `login-required`, `stale-job`, `form-not-loaded`, `submit-button-not-found`, `resume-upload-missing`, `account/platform-limit`, `network/page-load`, `unsafe-question`, `manual-finish-needed`, `wrong-profile`), manual-finish tabs handed to the user printed directly in terminal/final response, and next recommended step.

Then upsert `~/job-hunt/tracker.csv` for every company/role touched, and append to `~/job-hunt/application-ledger.md` as `timestamp | status | name | url` (escape `|` inside job names).

When an application reaches a verified confirmation page or confirmation email, update tracker/ledger first, emit the Vault application archive row with `scripts/job_archive.py emit` for non-LinkedIn channels, then close that completed application tab. Hand a tab to the user (bare `keep`) only for ManualFinish pages.

Do not create or update `~/job-hunt/manual-finish.md`. Track delayed referral/recruiter replies as compact ledger rows such as `ReferralFollowUp | <contact> — <company> follow-up after <date/window> | <LinkedIn URL>`.

## Current-machine notes (2026-06-02)

- Curated PDF directory: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/`
- Curated PDF script: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/curated-script/build_resumes.py`
- Mined source-of-truth: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/source-of-truth/resume_yupeng_{en,zh}.md`
- The 3 PDFs share: 2-page Letter, ATS-friendly single-column, header email `yplmicro@gmail.com`, GitHub accounts (`BrickerP` on older builds; `yupeng-dev` + `BrickerP` on the Oct-2026 build), location `San Francisco Bay Area`, no phone number, contains live demo links (Quant dashboard + GetDateLove), Target Roles subtitle per variant, structured Skills section, embedded PDF metadata (title/subject/keywords) for ATS.
