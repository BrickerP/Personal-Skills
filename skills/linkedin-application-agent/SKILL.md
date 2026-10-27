---
name: linkedin-application-agent
description: Frozen compatibility entry for the retired LinkedIn application engine. No runnable workflow; use job-search for supported job-search tasks.
metadata:
  opencode/autoinvoke: false
---

# Frozen LinkedIn application entry

Frozen since 2026-10-15. The old Debug Chrome / port 9222 engine and its batch
scripts are retired. This entry grants no permission to run them, port them,
inspect an account or submit an application.

Use [job-search](../job-search/SKILL.md) for current lifecycle tasks and
[Apply](../job-search/workflows/apply.md) for authorized official ATS applications.
LinkedIn Easy Apply, external-apply launch flows and LinkedIn account writes
remain frozen. Existing LinkedIn status is read only if the user asks for it.
No old salary, legal-status, phone or time-window defaults apply here: approved
facts live in [the current FROZEN table](../daily-job-apply/workflows/04-universal-web-apply.md).

Unfreezing an account would require an updated Markdown workflow under the
current policy; it does not make a retired browser script runnable.
