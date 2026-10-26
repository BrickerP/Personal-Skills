---
name: job-apply-automation
description: How to actually drive one job application end to end in a real browser — Ashby and Greenhouse, including the emailed security code — by reading the page and deciding, not by running fixed scripts. Use when applying to many roles, when a form asks for the 8-character security code, when a board looks blocked, or when the tracker and Gmail need reconciling into a real funnel.
---

# Applying to jobs, agent-driven

There are **no scripts** for this. You read the page with `chrome-use`, decide
what each field wants, fill it, check it, submit it, and record it. Fixed
scripts break the moment a board changes one question — judgement does not.

Policy (frozen answers, the ManualFinish class taxonomy, board playbooks) lives in
`daily-job-apply`. This skill is the operating loop and the traps. **When the two
disagree, policy wins** — fix the policy file, don't encode a workaround here.

## Pre-flight (30 seconds, every session)

Run `daily-job-apply` `COLD-START.md` §1 and the daily ~50 preflight before volume. Short form:

1. `TZ=Asia/Shanghai date` — know the clock.
2. PDF hash vs `pdf-hashes.txt` (COLD-START §1). STOP on drift.
3. Submitted count from `~/job-hunt/tracker.csv` (statuses Submitted/Ack/Rejected/DuplicateSubmitted).
4. `chrome-use browsers`, then `chrome-use --session jobapply2 --browser yplmicro@gmail.com tab list --full` — the
   printed `profile:` line must say **Lu (Profile 2, yplmicro@gmail.com)**.
   If it says anything else, stop (`wrong-profile`).
5. If that session sticky-hangs, open a **new** session name with the same `--browser`. Do not thrash the dead one. Never grant chrome-use `auth always`. See Session hygiene below.
6. Confirm the resume PDF exists
   (`~/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`)
   and `~/.config/daily-job-apply/env` holds `JOB_APPLY_PHONE` (never echo it).
7. Load `data/blocked-companies.json`. Any listed key is a hard skip, including **twilio**, even when the form looks clean.
8. The pre-submit gate lives at
   `~/.codex/skills/daily-job-apply/scripts/ats_pre_submit_gate.js`
   (`chrome-use eval --stdin < that-file`).

## The loop, one role at a time

1. Pick a role that is not already in the tracker. Dedupe by `(?:jobs/|token=)(\d{4,})` before open. Skip blocked-company keys.
2. Open the application URL in **one** labelled tab. Ashby:
   `https://jobs.ashbyhq.com/<slug>/<uuid>/application`. Greenhouse:
   `https://job-boards.greenhouse.io/embed/job_app?for=<board>&token=<id>`.
3. `wait --fn` for the first name field, then `snapshot -i -c`. Navigation invalidates refs and the viewport — snapshot again before any click. Do not reuse refs from the previous page.
3.5. **Probe before fill.** Read every label and sweep `checkValidity`. If a required field is ManualFinish-class, record ManualFinish and close the tab. Do not fill first.
4. **Read every visible question before typing anything.** ManualFinish class includes essay, numeric salary, Discipline dropdown (no invented major), arbitration/NDA, street address, citizenship attestation, AI-usage disclosure, anti-AI challenge, visible CAPTCHA/SMS. A policy acknowledgement that does not ask about AI tools is **Tick / Yes** (policy A). Recorded bio facts only: DOB `1999-08-03` when asked, OSU graduation `2021`. Years floor stays `3`. Do not invent any other bio field.
5. Fill: autocompletes first, then text by snapshot ref, then radios / Yes-No, then
   one option in each required checkbox group. Re-snapshot after every navigation, upload, or combobox pick.
6. Telephones: pick the country toggle then `fill --from-env`, so the number
   never appears in the transcript.
7. Gate. Treat only two things as passable: `ok:true`, or a complaint set that
   is entirely "unchecked members of a checkbox group that already has one
   checked" (Greenhouse marks every box in such groups `required`).
8. Submit with `find role button click --name "Submit application"`.
9. If a security-code field appears: new tab → Gmail →
   `newer_than:1h "security code"` → **newest** message → read the 8 characters
   from the snippet → back to the tab → `#security-input-0..7` **in order** →
   submit again.
10. Record only after proof. The only two proofs are `/confirmation` in the URL, or the
    security-code field appearing (then finish step 9 and confirm). "thank you / received"
    alone is not proof. A green `bad:0` is not proof.
    Only then record with
    `python3 ~/job-hunt/record-application.py --status Submitted …`
    and **close the tab**. One active apply tab. Wait **≥90s** before the next
    verified submit on the same platform family.
    The recorder **refuses** to overwrite a requisition
    that is already recorded as applied (exit code 2, `DUPLICATE SKIPPED`);
    it compares `gh:<job id>` / `ashby:<uuid>` keys, so the `/jobs/<id>` and
    `/embed/job_app?token=<id>` shapes of the same job collide correctly.
    Treat that refusal as a stop: you are about to re-apply to a job you have
    already submitted. `--force` exists only for a knowing second submission.
    A probe-time ManualFinish is recorded and the tab is closed. CAPTCHA/SMS on an
    already-filled form is ManualFinish with `keep` (user blocker) — do not solve it.

## Verification: what actually counts as submitted

- **The only two proofs are** the URL containing `/confirmation`, or the
  security-code field appearing. A green `bad:0` / `checkValidity()` pass is
  **not** proof — Greenhouse will happily no-op a "valid" form.
- **Stale errors after a successful submit are normal.** `p[id$=-error]` keeps
  showing the pre-submit messages after the code step. Believe the URL.
- **A required field can appear only after the first submit** (Vercel's
  "Please double-check all the information provided above", Upstart's
  "Location Preference"). Submit → read errors *by label* → fill the new field →
  submit again.
- **Read errors by label, not by id.** `p[id$=-error]` → strip `-error` →
  `label[for=…]` gives the human question, which is what you need to decide.

## Traps that cost real submissions

- **React ignores synthetic clicks.** `element.click()` flips the CSS class but
  not the form state. Use real `chrome-use click @ref`. When a reCAPTCHA iframe
  covers the control, `click --allow-dom` is the only thing that lands.
- **Hidden required checkbox labelled only "Acknowledge/Confirm"** (Cloudflare,
  Everpure, Vercel, Starburst). It has no findable label text, and a plain click
  often no-ops; use `el.scrollIntoView({block:'center'})` then a real click.
  Find it with `document.querySelectorAll('input')` + `checkValidity()`.
- **React-controlled inputs reject `fill`.** The DOM value changes but React
  state does not, so validation never clears (Relativity start-date, Intercom
  location). Click the field and `keyboard type`; if it still fails, ManualFinish
  rather than burning turns.
- **Autocompletes wipe the form.** Choosing an option in a "Start typing…" field
  re-fetches the application and clears anything typed earlier. Do them first.
- **A failed submit resets everything** and leaves stale `aria-invalid`. After a
  failed submit, reload and refill; re-clicking the same button mostly just
  produces the same error.
- **Success wording varies** ("successfully submitted", "Thank you", "Awesome!").
  If you only look for one phrase you will re-submit a successful application.
- **Ashby custom question ids are per-render UUIDs.** Only
  `#_systemfield_name` / `#_systemfield_email` are stable — fill by ref.
- **Greenhouse checkbox groups** ("How did you hear about us?") mark every box
  required; browser validity never passes. Tick one and move on.
- **Two controls both named "Country".** The first is the phone dial code, the
  second is residence. Filling the wrong one leaves the real field empty.
- **`intl-tel-input` listbox swallows clicks.** If nothing lands, check
  `#iti-0__country-listbox` visibility, pick the country, then continue.
- **Location autocomplete that never commits is often harmless** (Brex,
  SingleStore): `#candidate-location` stays empty and the form still submits.
  Don't loop on it — submit and read the errors.
- **EEO selects differ by board.** Click, read the real options
  ("Decline To Self Identify" vs "I don't wish to answer" vs "US" vs
  "United States"), then pick. Never blind-pick.
- **Some boards are silent no-ops** (Reddit, and Ashby platform-wide at time of
  writing): button enabled, everything valid, click does nothing. Treat as
  blocked after one attempt.
- **Company caps are policy, not errors** — Linear 2/60d, Cognition 2,
  Sierra 2–3. The page says so; don't fight it.

## Session hygiene (sticky fails)

- Canonical session: `jobapply2` + `--browser yplmicro@gmail.com` on every start verb. Profile must be Lu (Profile 2). **Never grant chrome-use `auth always`.**
- If the session hangs (commands freeze, extension silent): open a NEW session name; do not keep retrying the dead one. The retired name `jobapply` is not reused. Benign warning: `close incomplete: untracked tab` — ignore.
- chrome-use version: if `upgrade` installed a newer binary but `doctor` still shows the old one, restart the Chrome extension / daemon before blaming the form. Do not mid-run upgrade without a user nod when other bots share the profile. Installed version ≠ active version until that restart.
- `pick` flaky / hidden-tab scroll noop (seen on 1.5.233): work around with `click @ref`, keyboard, or eval `scrollIntoView`. After navigation, refs and the viewport are stale — re-snapshot before the next click or fill. `href` null on a link → use `eval`, do not hammer `open` on a slow site. Never block the batch on building a Greenhouse site adapter.
- Visible CAPTCHA / hCaptcha / SMS stay user blockers → ManualFinish. Do not solve them.
- Before restarting Chrome, the open tabs may include a half-filled Greenhouse form. Close or `keep` those first; do not assume they survive a restart.

## Retry policy

| Situation | Action |
|---|---|
| `page-load-or-form-timeout` / embed slow | Retry once on the canonical job-boards or embed URL |
| `submit-unverified` / anti-bot text | ManualFinish; **no** same-run resubmit |
| `skip-email-verification` / code page | Solve via Gmail (newest body in that company's thread); if no mail after the wait → ManualFinish |
| `DUPLICATE SKIPPED` (exit 2) | Stop — already applied |
| React fill won't commit after keyboard type | ManualFinish — don't burn 10 turns |
| ManualFinish-dominated probe streak (first ~10) | Stop the run; ask the four gates |
| Company in `blocked-companies.json` / cap | Skip (`company-blocked`), including Twilio |
| Visible CAPTCHA / SMS | ManualFinish. Do not solve |

## The four policy gates dominate at scale

After ~1,200 submissions the unfilled pool is gated almost entirely by four
things, and all four are **user decisions**, not agent judgement:
essay / required free-text · numeric years of experience · numeric salary ·
education **Discipline**. When a run starts producing mostly ManualFinish rows,
stop applying and ask for those four answers — probing on produces zero
submissions per hour.

## Sourcing: change industry, not keyword

Form difficulty is inversely correlated with applicant volume. Consumer SaaS
filters hard (essay + salary + years); AI chips / robotics / space companies
barely filter at all. Slug-guessing new Greenhouse boards is **exhausted**
(161-domain probe → 6 candidates); the remaining yield is *software roles at
hardware companies* (Figure, Tenstorrent, SambaNova, Relativity).

HN "Who is hiring" still works, but Algolia returns HTML-escaped text
(`https:&#x2F;&#x2F;…`): `html.unescape()` before the regex or you get zero matches.

Board-by-board fingerprints, the full blocker table and the discovery status
live in `../daily-job-apply/FIELD-NOTES-1218.md` — read it before a run.

## Bookkeeping

- Record only after a confirmation page; one row per distinct requisition.
- Keep an eye on the running total so the count never drifts.
- **Duplicate audit after every batch**: pull `(?:jobs/|token=)(\d{4,})` out of
  `JD_URL` and count repeats. Target state is 0.
- Reconcile Gmail periodically: rejection and acknowledgement emails map back
  onto tracker rows by company + role tokens; one email → one row. This is what
  turns "500 green rows" into a real funnel.
- `ManualFinish` is debt, not failure. Keep the reason in `Notes` so a later
  session can group them and ask for the *one* answer that unlocks the group.
- A later ManualFinish upsert can overwrite a real submission. When a count looks
  wrong, grep the ledger for the company and repair the tracker row.
