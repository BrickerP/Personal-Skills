# Apply to a job

Use for requested submissions or continuation of an authorized run. Preparing
materials ends at the materials stage and does not automatically enter this one.

## Inputs and references

Start with one selected role or the user's authorized volume preset. Reuse
profile, curated PDF and application records from
[shared state](../references/shared-state.md).

1. Read [application policy](../../daily-job-apply/POLICY.md) and
   [COLD-START](../../daily-job-apply/COLD-START.md). Complete hash, account,
   blocked-company and dedupe checks before opening a role.
2. Read [workflow 04](../../daily-job-apply/workflows/04-universal-web-apply.md)
   for FROZEN facts and only the current platform's playbook.
3. Consult [browser reference](../references/browser-apply.md) for session
   hygiene, rich controls, email verification and uncertain outcomes.

## Agent-driven work

The Markdown procedure guides the agent; it is not a browser program. Open one
application tab in the correct profile. Read the live snapshot and every required
label. Decide which questions have approved factual answers and which need
ManualFinish before typing.

Take `chrome-use` actions against current controls, one meaningful action at a
time. Re-snapshot after navigation, upload or custom-option pick; confirm the
value/attachment persisted. Do not inject state/setters, synthesize clicks,
replay selectors across jobs or use a looped fill/upload/submit runner.
Stop on CAPTCHA/SMS, anti-bot or rate-limit warnings.

When ready, run the read-only pre-submit gate, review its verdict and warnings,
and click Submit once only when authorized and allowed. If ordinary email
verification appears, finish it using
[END-OF-RUN §3](../../daily-job-apply/END-OF-RUN.md#3-greenhouse-email-verification-chain).
The code page is **verification pending**. Submitted requires a final success
page/state or matching application-received email; no proof means unverified,
never automatic resubmit.

## Completion

After proof, use the existing tracker/ledger recorder and Vault archive helper.
Associate the job ID, submission evidence and actual resume version when
available; never invent missing snapshots. Then close the agent-owned tab.

For a human gate, use workflow 04's handoff: close untouched probes; keep an
already-filled human-blocked tab for the user. Record the exact reason while
preserving any earlier confirmed submission. Follow
[END-OF-RUN](../../daily-job-apply/END-OF-RUN.md) for cleanup and final counts.

## daily-50 preset

An existing daily-50 request uses this same workflow for about 50 verified
zero-gate Greenhouse submissions. Read
[FIELD-NOTES](../../daily-job-apply/FIELD-NOTES-1218.md) and the current
`~/job-hunt/HANDOFF.md` **if present** (optional session context, as POLICY
describes). Retain the broad software funnel and AI/Agent seed lane, and use one
active application tab. Keep at least 90 seconds between verified submits on the same platform
family and the 20/hour ceiling. Stop if the first approximately 10 probes are
mostly blocked/manual; report what needs a user decision. The target never
overrides a stop or manufactures success.

This preset adds no runner, schedule or messaging permission. Use
[review](review.md) for replies/results and [interview](interview.md) when a role
advances.
