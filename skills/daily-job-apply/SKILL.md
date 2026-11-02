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
- Chrome account isolation: every start-capable `chrome-use` command pins
  `--browser yplmicro@gmail.com`, and that account must be CONNECTED. A
  `profile:` line passes when its account is `yplmicro@gmail.com`. On the wp
  Mac that is usually `Lu (Profile 2, yplmicro@gmail.com)` — prefer it when
  that profile exists. On a failover Mac, `您的 Chrome (Default,
  yplmicro@gmail.com)` or another display name for the same account still
  passes. Medo, cookiy, or any other account is STOP `wrong-profile`. Never
  grant chrome-use `auth always`.
- [workflow 04](workflows/04-universal-web-apply.md) owns FROZEN factual answers
  and the per-role procedure.
- [END-OF-RUN.md](END-OF-RUN.md) owns verified recording and cleanup.

This entry adds no runner or permission to submit. The agent follows Markdown,
reads the current page, decides, acts once and reads back the result.
