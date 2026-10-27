---
name: daily-job-apply
description: Compatibility entry for existing daily-50 prompts. Read job-search's apply workflow; application policy and ATS resources remain here. New job-search requests use job-search.
metadata:
  opencode/autoinvoke: false
---

# Daily Job Apply — compatibility entry

Use [job-search](../job-search/SKILL.md) for lifecycle routing. Existing prompts
that explicitly invoke this name continue through
[the apply workflow](../job-search/workflows/apply.md).

- [POLICY.md](POLICY.md) owns application constraints and allowed helper boundaries.
- [COLD-START.md](COLD-START.md) owns preflight and the daily-50 preset.
- [workflow 04](workflows/04-universal-web-apply.md) owns FROZEN factual answers
  and the per-role procedure.
- [END-OF-RUN.md](END-OF-RUN.md) owns verified recording and cleanup.

This entry adds no runner or permission to submit. The agent follows Markdown,
reads the current page, decides, acts once and reads back the result.
