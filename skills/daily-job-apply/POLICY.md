# Application policy

Internal application rules for [job-search](../job-search/SKILL.md). Read for
actual application work, not every search, resume or interview request.

## Authority and execution model

The user's current instructions govern the task. The **FROZEN section of
[workflow 04](workflows/04-universal-web-apply.md)** is the factual source for
identity, contact, location, work authorization, years, education and AI usage.
Platform notes describe UI behavior, never new approved answers. Generic
ManualFinish labels do not override FROZEN facts such as the years calculation,
recorded graduation years or the approved Discipline preference.

**The agent executes Markdown:** inspect the page, decide what the question
asks, take an atomic `chrome-use` action, and read back. Navigation, uploads and
custom-option picks require fresh snapshots. Do not turn this into a fixed
selector program or a browser loop that fills, uploads, submits or retries jobs.
Do not inject setters, synthetic clicks or hidden-state manipulation.

Allowed helpers: API-only/offline sourcing, classification, dedupe, hashes,
read-only DOM/validity inspection (`ats_pre_submit_gate.js`), tracker/ledger
recording and archive emission. Their output informs the agent; it does not
permit submission. Retired CDP/Playwright/AppleScript adapters, batch runners
and `run-next.sh` remain historical. No anti-bot evasion or CAPTCHA/SMS solving.

## References loaded as needed

| Reference | Purpose |
|---|---|
| [COLD-START](COLD-START.md) | Session preflight and daily-50 preset |
| [FIELD-NOTES](FIELD-NOTES-1218.md) | Before volume work; empirical UI behavior |
| [workflow 04](workflows/04-universal-web-apply.md) | FROZEN facts, per-role process and handoff |
| [Greenhouse](ATS-GREENHOUSE.md) / [Ashby](ATS-ASHBY.md) | Only the current platform |
| [END-OF-RUN](END-OF-RUN.md) | Email code, recording, cleanup and reporting |
| [ATS-EVOLUTION](ATS-EVOLUTION.md) | Playbook maintenance and failure evidence |
| [ATS-BLOCKERS](ATS-BLOCKERS.md) | Historical logs only |
| [Disclosure rules](guards/stealth-rules.md) | Outbound information boundaries |
| `~/job-hunt/HANDOFF.md` | Counts and unanswered user decisions, if present |

Runtime resources remain under `~/.codex/skills/daily-job-apply/`, with overrides
in `~/.config/daily-job-apply/env`. Reuse `data/profile.json` and private runtime
files; never copy personal data into new skill/workflow documents.

## Application defaults

- Broad US/Bay Area/remote software funnel: seed Agent / AI Infra / ML Systems
  roles, then reasonable Backend / Full-stack / Platform / Infra / ML / AI roles.
- Dedupe **before opening** a role. Duplicate, `company-blocked` and cap results
  are hard stops. Never exceed 20 applications/company across all time.
  The helper first reads `~/job-hunt/data/blocked-companies.json`, then falls
  back to the skill's `data/blocked-companies.json` when the first has no nonempty
  list. The effective list wins over clean-form notes, including Speechify and
  Twilio. Never remove a key or infer expiration from a file's age to proceed.
  This per-role check belongs to Apply, not an optional dashboard. Only exit 0
  with final `ok: true` allows continuation; failed or missing checks stop work.
- Browser: `chrome-use`, Lu / `yplmicro@gmail.com`, session `jobapply2`.
  Pin `--browser yplmicro@gmail.com` on every start-capable command. Every
  printed `profile:` line must match Lu (Profile 2, yplmicro@gmail.com).
  Mismatch stops the whole run. Never grant `auth always`.
- Only the job-search Gmail account may supply verification codes/job mail;
  never a company mailbox or another logged-in Gmail account.
- Phone comes only from private `JOB_APPLY_PHONE`, filled with `--from-env` last
  and masked as workflow 04 specifies. Never print, type into a command or commit
  digits. No CN/retired fallback. Rejection or +86 demand is ManualFinish
  (`phone-rejected`); SMS consent is No, SMS verification is human-only.
- Location and work authorization follow FROZEN. Never invent biography,
  credentials, dates, nationality, salary or clearance. Real employers may be
  named under current disclosure rules; confidential internal details stay out.
- LinkedIn Easy Apply, external-apply launch flows, profile edits, saves,
  messages and recruiter actions remain frozen until the user unfreezes them.
  Reading existing LinkedIn status requires the user's request.
- The retired BJT 09:00–19:00 stealth ban does not restrict external ATS work.
  The weekday daily-50 routine remains 21:00 Asia/Shanghai; these docs do not
  create or change schedules.

## Curated PDF boundary

Default is the curated **1P English AI Agent Engineer PDF**. Use 2P English for
explicit high-priority, referral or manual-review work. Legacy AI Agent Infra /
Backend Platform / General SWE aliases resolve to 1P rather than regeneration.
Resolve paths from the existing profile/runtime configuration. Verify hashes
against `pdf-hashes.txt` via COLD-START before application work.

Only `curated-script/build_resumes.py` owns application PDFs. Application runs,
email review and GitHub evidence mining do not rebuild them. Hash drift stops
the run; never silently re-baseline. Requested resume changes use the
[resume workflow](../job-search/workflows/resume.md).

## Authorization and daily-50

An explicit application request (`apply`, `go`, `投递`, `direct`, `no dry-run`)
authorizes real submission after checks. Triage, drafting materials or
reorganizing skills does not authorize submission or messaging. Referral,
email and LinkedIn sends require their own user authorization.

`daily-50` is a preset of [apply](../job-search/workflows/apply.md), about
**50 verified zero-gate Greenhouse submissions** per weekday evening, not a
runner or skill. Keep one active application tab; record and close confirmed
submissions before the next. Leave 90–180 seconds between successful submits on
the same platform family, at least **90 seconds** for daily-50. Retain the
steady-state ceiling of 20 verified submits/hour. Stop if ManualFinish/Blocked
dominate the first approximately 10 probes and report the unanswered classes.

## Required questions and human decisions

Read all required labels before filling. Use a truthful FROZEN answer only when
it covers the exact question. Otherwise ManualFinish rather than guessing.

| Question | Handling |
|---|---|
| Essay, motivation, company-specific free text | ManualFinish in daily-50; a materials draft does not change policy |
| Numeric salary / compensation | User decision; do not infer a number from a range |
| Years, education, GPA, Discipline or dates | Only what FROZEN explicitly supports; unknown detail/option is ManualFinish |
| Street address, nationality or unlisted bio field | ManualFinish |
| Arbitration, NDA, non-compete or unfamiliar legal status | ManualFinish |
| AI disclosure, AI-assistance attestation, anti-AI instruction/challenge | ManualFinish under policy A |
| Authenticity acknowledgement not asking about AI | Tick / Yes under FROZEN policy A |
| Ordinary privacy/data-processing acknowledgement | Follow its actual policy/playbook rule; never infer marketing/SMS consent |
| Company-specific hard skill gate with no truthful affirmative | ManualFinish / skill-gap under current policy; never inflate experience to pass |

The one approved ordinary “Do you use AI tools?” sentence lives in workflow 04;
it does not authorize a separate disclosure or employer prohibition.

## Stops, evidence and records

- Wrong profile, hash drift, missing PDF baseline or lost browser connection
  stops the run. Do not fix by silently changing identity or baseline.
- Visible CAPTCHA/hCaptcha, graphical bot checks, SMS, spam/anti-bot warnings,
  rate limits and unknown final steps stop that application. Never retry final
  Submit after a warning or use DOM workarounds around a challenge.
- The pre-submit JS helper is read-only. Submit only with `ok: true` after
  reviewing questions and warnings. Validity is not proof of submission. One
  deliberate correction of a safe omission is allowed; persistent invalid
  state is ManualFinish.
- A code field is **verification pending**, not Submitted. Finish ordinary
  email verification in the correct mailbox, then require a final success state
  or matching application-received email. Code-delivery mail is not a receipt.
  No final evidence means unverified, never guessed success or auto-resubmit.
- After proof: record existing tracker/ledger fields, emit the existing Vault
  row, then close the agent-owned tab. Never replace a known submission with a
  later probe failure or create a second tracker/schema.
- Probe-time ManualFinish closes untouched. Already-filled human-blocked pages
  use bare `keep`, with a blocker and printed handoff. Never close kept/user tabs.

[END-OF-RUN](END-OF-RUN.md) owns column mapping, archive commands and final counts.
Durable corrections belong in this repository via reviewable commits, then
sync/install. No browser runner is introduced by this policy.
