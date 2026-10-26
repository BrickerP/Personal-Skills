# Browser operating reference

Read while executing [apply](../workflows/apply.md). Policy and facts remain in
[POLICY](../../daily-job-apply/POLICY.md) and
[workflow 04](../../daily-job-apply/workflows/04-universal-web-apply.md).

## Read → decide → act → verify

Use `chrome-use` in the real logged-in Chrome, following its installed core
guide for current commands. Use `jobapply2` and `--browser yplmicro@gmail.com`
on every command that may start a session. Every printed profile line must
identify Lu (Profile 2, yplmicro@gmail.com). Mismatch stops the run. Never grant
`auth always` or substitute an unrelated profile.

- Open one labelled application tab. Wait for visible form content rather than
  assuming load means hydration, then take a fresh interactive snapshot.
- Read all required labels; scroll to expose lazy-rendered fields. Classify the
  actual question against FROZEN and ManualFinish before typing. An unfamiliar
  required question is not a reason to write a new adapter.
- Use current snapshot labels/refs. Navigation invalidates refs; uploads and
  combobox picks may reset fields. Re-snapshot and recheck affected values.
- Old selector strings are diagnostic hints, not a fill map. Do not use fixed
  selector loops, injected setters, synthetic clicks or hidden-state writes.
- React Select/autocomplete requires choosing a real option. Read the options,
  choose the truthful one, then verify it stuck. A displayed DOM string may not
  be committed. Correct once deliberately; persistent failure is ManualFinish.
- Identify the actual resume attachment control, distinct from resume-autofill.
  Wait for the filename/upload-complete state and inspect autofilled data.
  Failed upload is not permission to loop upload/submit attempts.
- Fill phone last with the private env through workflow 04's `--from-env` and
  masking rules. Never place its digits in a form map or inspect its value.

The pre-submit helper only inspects DOM. A pass does not excuse an unanswered
question. Read errors by human label, not generated ID. Checkbox-group quirks
must be inspected under the documented gate result, not bypassed.

## Submit and email verification

After policy, factual answers and the gate pass, click the current Submit once.
Distinguish it from Upload, Replace, Save or Yes/No. Observe URL and page.
Validity, a disappearing button, generic “thank you”, a code field or a
code-delivery email is not final submission proof.

Ordinary email-code requests mean **verification pending**. Use only the
job-search mailbox and the newest matching company's message, not an old code
in a thread or another account. Return, re-snapshot and read current controls:
a single field takes the whole code; split controls take one character each by
real UI input. Do not assume zero-based IDs or inject native setters. Recheck the
step before its authorized confirmation action. Require the final success state
or a matching application-received receipt before recording Submitted.

CAPTCHA/hCaptcha, SMS and graphical challenges are human blockers. Do not solve
or use DOM clicks around overlays. Spam/bot/rate-limit warnings stop the role;
never repeat Submit or switch methods around the warning. Missing/unreadable
verification mail becomes ManualFinish.

## Uncertainty and session hygiene

- No final success: read exact errors and inspect records/matching receipt. Do
  not retry an unverified submit in the same run; record uncertainty and hand off.
- “Already applied” or recorder duplicate refusal stops this requisition. Never
  use `--force` to meet a run target.
- Stale validation after completed success does not authorize another submit.
- Record before closing success tabs. Close untouched probe-time ManualFinish;
  use bare `keep` for already-filled human-blocked pages. Kept tabs are the user's.
- If a session hangs, choose a fresh name with the same pinned browser and note
  it; do not hammer the dead session or reuse retired `jobapply`. Avoid runtime
  upgrades/restarts while another bot shares the profile. Resolve half-filled
  tab ownership before an approved restart.
- Leave 90–180 seconds between verified submits on the same platform family,
  with at least 90 seconds for daily-50 and the 20/hour ceiling. Stop early when
  blocked/manual probes dominate rather than writing a loop.

Record through [END-OF-RUN](../../daily-job-apply/END-OF-RUN.md), keeping the exact
blocker. This reference adds no runner or permission beyond the application task.
