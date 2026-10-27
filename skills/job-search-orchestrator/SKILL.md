---
name: job-search-orchestrator
description: Compatibility entry for the former job-search dashboard. Explicit legacy callers route to job-search Review; new job-search requests use job-search.
---

# Job-search dashboard compatibility entry

Use [job-search](../job-search/SKILL.md) as the lifecycle entry and load
[Review](../job-search/workflows/review.md) for a morning/evening check or status
question. Its [status reference](../job-search/references/status.md) contains
the current read-only evidence and routing rules.

This entry does not apply, send messages, rebuild PDFs, repair records or change
schedules. An explicit request to apply routes to the job-search Apply workflow
with the user's existing authorization; a dashboard request remains read-only.

Existing daily-50 callers can continue using their old names. Daily-50 is the
Apply preset, and LinkedIn Easy Apply remains frozen.
