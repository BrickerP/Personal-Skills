# Shared facts and application records

Read only the sources needed for the current stage. These records support every
stage; establishing a profile is not a mandatory first step on every request.

## Resolve the current machine

- The runtime resources remain under `daily-job-apply/`; resolve that directory
  from the installed skill instead of assuming the repository checkout path.
- Read [skill_paths.sh](../../daily-job-apply/runtime/skill_paths.sh) for existing
  path resolution. Sourcing it loads optional `~/.config/daily-job-apply/env` and
  creates runtime directories, so do that only when runtime work is needed.
- `DAILY_JOB_APPLY_WORK_DIR` selects the work directory (default `~/job-hunt`).
  `DAILY_JOB_APPLY_TRACKER` overrides the tracker; otherwise the helper chooses
  between the populated work-directory tracker and `daily-job-apply/state/tracker.csv`.
- `DAILY_JOB_APPLY_PDF_DIR` overrides the PDF directory. Otherwise the helper
  derives it from `data/profile.json` → `resume_paths`, then falls back to
  `~/Documents/resumes`. Use the profile's selected PDF path when available.
- Do not print the environment, phone values, or the entire personal profile.

## Sources and ownership

| Source | Use |
|---|---|
| [profile.json](../../daily-job-apply/data/profile.json) | Existing personal facts, preferences, document paths |
| [FROZEN answers](../../daily-job-apply/workflows/04-universal-web-apply.md) | Approved form answers and unresolved-question boundaries |
| `source-of-truth/resume_yupeng_{en,zh}.md` in the resume base | Mined experience and project evidence |
| `curated-script/build_resumes.py` in the resume base | Owner of recruiter-facing PDF generation |
| `application-ai-agent/` in the resume base | Curated PDFs and `pdf-hashes.txt` baseline |
| Existing tracker and `application-ledger.md` | Operational application history |
| Vault `applications/` and `Interviews/` | Application evidence and interview preparation |

On this machine the resume base is
`/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu`; prefer an established
profile path or explicit user destination on another machine. Facts that conflict
across sources need clarification, not a guessed merge. Personal source material
and application artifacts belong in those private locations, not this public repo.

## Preserve the existing record contract

- Read headers and existing values before updating a tracker. Map columns by
  name using [END-OF-RUN](../../daily-job-apply/END-OF-RUN.md#6-tracker-upsert-field-mapping).
  Keep its existing vocabulary and normalized `JD_URL` upsert contract.
- Use the dedupe helper before application work. Canonical requisition IDs help
  associate URL variants; a company name alone cannot identify an application.
- The Vault's normal batch row contains status, company, role and URL. It is
  not proof that a full JD, submitted PDF, or screenshot was archived.
- When capturing an application snapshot, associate it with its job ID/URL,
  the actual submitted PDF path and hash, available answers, and submission
  evidence. Preserve earlier snapshots; never relabel a current PDF as an old
  submitted version. If an artifact is unavailable, state that explicitly.
- Material drafts do not mark an application `Submitted`. Record `Submitted`
  only after the apply workflow verifies completion, including any email-code step.
- No new tracker, status enumeration, or automatic state transition is introduced
  by these workflows. Helpers perform bounded checks or record operations; the
  agent remains responsible for interpreting evidence and reporting uncertainty.
