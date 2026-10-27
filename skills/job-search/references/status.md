# Read-only job-search review

Use from [Review](../workflows/review.md). This reference replaces the old
orchestrator's always-run shell dashboard. Inspect only the sources needed for
the requested answer; do not turn this review into an application run.

## Resolve state

Use [Shared state](shared-state.md) and existing configured paths. Candidate
profile data stays local; never print private phone values or copy a profile
into a report. Distinguish a missing source from an empty pipeline.

For a broad morning/evening check, inspect:

1. Curated PDF presence and hash baseline, without rebuilding or rebaselining.
2. Today's verified applications, outstanding ManualFinish items and records
   that disagree across tracker, append-only ledger and Vault archives.
3. Job-mail status signals and scheduled interview preparation when those
   sources are available and relevant to the request.
4. Evidence freshness only when a resume update would help the requested task.

The old BJT 09:00–19:00 write ban is retired. The routine's 21:00
Asia/Shanghai clock and target of about 50 verified Greenhouse applications
are a scheduling preset, not a ban on other hours. Do not reschedule anything
or revive Easy Apply. Zero earlier in the day alone is not an emergency.

## Count what is supported

- Parse the CSV with a CSV parser, not a comma split: Role and Notes can contain
  commas. Read actual headers and preserve the existing schema and vocabulary.
- Count distinct submitted requisitions using the existing platform/job ID
  normalization. Greenhouse job and embed URLs may refer to the same job.
- Distinguish attempted/touched, drafted, ManualFinish, Blocked and confirmed
  submissions. An email security-code field means verification is pending.
  A passed validity check, a click, a copied file or a folder is not proof.
- Read both archive layouts: `<channel>-batch-YYYY-MM-DD.md` tables and promoted
  per-role files beneath `<channel>-batch-YYYY-MM-DD/`. Only explicit submitted
  evidence counts. A promoted file without a Status header is **unknown**;
  never fall back to counting every file as submitted.
- Do not add tracker, ledger and archive counts together: they are views of the
  same applications. Report discrepancies, matching by job ID/URL and evidence,
  rather than choosing the larger number or silently overwriting a source.
- Compare ledger ↔ archive, tracker ↔ archive and ledger ↔ tracker separately.
  Identify the exact missing role when possible. The existing `job_archive.py`
  helper can propose an archival backfill, but this read-only review does not
  execute it or repair tracker state.

## Job mail

Prefer the existing local Gmail worker via the `gmail-ai-daily-ops` skill.
Check its identity before reading messages: only `yplmicro@gmail.com` is the
job-search mailbox. If the worker is unavailable and a connector is considered,
verify its account first; another mailbox is not a fallback. Missing access is
reported as unavailable, not zero unread or zero replies.

Classify relevant messages from their content, not merely sender domain:
acknowledgement, rejection, assessment, interview, offer or unrelated mail.
Link the supporting message to the existing role. Ambiguous company/role matches
remain unresolved; an offer is not acceptance or a hired outcome. Do not send,
reply, archive, mark read or change application status during a read-only review.
The Review workflow explains how an explicit record-update request is handled
separately from this read-only review.

LinkedIn mail can be read in the authorized mailbox; inspecting LinkedIn itself
still requires the user's explicit request while the freeze is active.

## Interviews and evidence

Read both `Interviews/<Company>.md` and `Interviews/<Company>/` layouts.
Look for the actual interview date, stage, JD, submitted materials, preparation
and prior-round feedback. Do not infer an appointment solely from file mtime.

- Interview within two days with no JD: surface the missing context first.
- Interview within seven days with no prep: route to Interview.
- Multi-round cases can use the existing promoted directory layout; recommend
  promotion rather than creating files as part of a status check.
- A meaningful new project or evidence theme can justify Resume. Commit count
  or an arbitrary weekly timer alone does not justify regenerating PDFs.

## Output

Answer the user's question first, then show a compact snapshot with source and
time scope. Separate facts, missing inputs and proposed actions. Report only
material blockers (for example hash drift, a missing interview JD, wrong account
or record disagreement) and at most three actions in priority order. Finish
with one concrete next action routed to the lifecycle stage. No automatic
application, external message, PDF edit, link repair or scheduler change follows.
