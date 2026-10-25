---
name: job-apply-automation
description: How to actually drive one job application end to end in a real browser — Ashby and Greenhouse, including the emailed security code — by reading the page and deciding, not by running fixed scripts. Use when applying to many roles, when a form asks for the 8-character security code, when a board looks blocked, or when the tracker and Gmail need reconciling into a real funnel.
---

# Applying to jobs, agent-driven

There are **no scripts** for this. You read the page with `chrome-use`, decide
what each field wants, fill it, check it, submit it, and record it. Fixed
scripts break the moment a board changes one question — judgement does not.

Policy (frozen answers, what must be skipped, ManualFinish rules) lives in the
`daily-job-apply` skill. This skill is the operating loop and the traps.

## Pre-flight (30 seconds, every session)

1. `TZ=Asia/Shanghai date` — know the clock.
2. Submitted count from `~/job-hunt/tracker.csv` (statuses Submitted/Ack/Rejected/DuplicateSubmitted).
3. `chrome-use --session jobapply --browser yplmicro@gmail.com tab list` — the
   printed `profile:` line must say **Lu (Profile 2, yplmicro@gmail.com)**.
   If it says anything else, stop; you are about to fill forms as the wrong person.
4. Confirm the resume PDF exists
   (`~/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`)
   and `~/.config/daily-job-apply/env` holds `JOB_APPLY_PHONE`.
5. The pre-submit gate lives at
   `~/.codex/skills/daily-job-apply/scripts/ats_pre_submit_gate.js`
   (`chrome-use eval --stdin < that-file`).

## The loop, one role at a time

1. Pick a role that is not already in the tracker (same company + title).
2. Open the application URL in a new labelled tab. Ashby:
   `https://jobs.ashbyhq.com/<slug>/<uuid>/application`. Greenhouse:
   `https://job-boards.greenhouse.io/embed/job_app?for=<board>&token=<id>`.
3. `wait --fn` for the first name field, then `snapshot -i -c`.
4. **Read every visible question before typing anything.** If a required field
   wants an essay, a numeric salary, a portfolio, a phonetic name, a street
   address, a citizenship attestation or an AI-usage disclosure — close the tab
   and record ManualFinish. Do not improvise.
5. Fill: text by snapshot ref, then autocompletes, then radios / Yes-No, then
   one option in each required checkbox group.
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
10. Verify `/confirmation` in the URL, or "thank you / received" in the body.
    Only then record with
    `python3 ~/job-hunt/record-application.py --status Submitted …`
    and close the tab. The recorder now **refuses** to overwrite a requisition
    that is already recorded as applied (exit code 2, `DUPLICATE SKIPPED`);
    it compares `gh:<job id>` / `ashby:<uuid>` keys, so the `/jobs/<id>` and
    `/embed/job_app?token=<id>` shapes of the same job collide correctly.
    Treat that refusal as a stop: you are about to re-apply to a job you have
    already submitted. `--force` exists only for a knowing second submission.

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
