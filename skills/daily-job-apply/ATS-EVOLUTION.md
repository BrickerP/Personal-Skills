# ATS playbook maintenance

Internal reference for maintaining the Markdown application workflow. Live work
uses [job-search / apply](../job-search/workflows/apply.md),
[POLICY](POLICY.md), and the current platform playbook. Platform knowledge lives
in Markdown; the agent reads the current page and decides each action.

## Existing records

| Artifact | Purpose |
|---|---|
| `data/ats-adapter-registry.json` | Domain classification and playbook references |
| `~/job-hunt/ats-adapter-registry.json` | Existing mirror |
| `~/job-hunt/ats-evolution-log.jsonl` | Append-only attempt/failure evidence |
| `data/ats-evolution-log.jsonl` | Existing mirror |
| `~/job-hunt/ATS-EVOLUTION.md` | Machine-local field observations, if present |

The registry keeps legacy names for compatibility. `playbook` identifies the
Markdown reference used by the agent (Greenhouse, Ashby, Lever's workflow 04).
`experimental` means there is no reviewed platform playbook. `unsupported-direct`
marks an intermediary that should be resolved to an official posting or skipped.
Old `production` / `adapter_script` fields are historical, not authorization to
run browser scripts. A classifier's `apply_allowed` result is a routing hint,
not proof that the live form is safe or that submission is authorized.

The CDP/Playwright/AppleScript adapters and batch runners remain retired. No
promotion threshold or past success count re-enables them. Extend a Markdown
playbook instead of building another fill/upload/submit adapter.

## Learn from one observed failure

1. Read the live page's label, visible error and resulting state. Keep personal
   values out of logs. Record whether there was actual final confirmation;
   inspection/validity and email-code pages are not successful submissions.
2. Use the existing failure vocabulary in [workflow 04](workflows/04-universal-web-apply.md).
   When useful, append the observed event with the deterministic logging helper:

   ```bash
   python3 ~/.codex/skills/daily-job-apply/scripts/ats_evolution_log.py \
     --platform greenhouse --url '<official-job-url>' --status Blocked --blocker form-not-loaded
   ```

   This helper records evidence; it does not touch the browser. Active MD work
   does not log automatically through the retired adapters, so do not claim
   these counters measure all current applications.
3. Add the narrow lesson to the relevant playbook/FIELD-NOTES, identifying the
   observed board and date. Keep FROZEN factual answers in workflow 04. A UI
   workaround never overrides policy or authorizes an unknown answer.
4. For a newly supported platform, inspect an actual form and write its Markdown
   playbook. Then update the registry's domain and playbook reference. Do not
   mark a platform verified based on synthetic DOM or an API-only classifier.
5. Review and commit the documents, then sync/install. Test a browser procedure
   only within a separately authorized application/QA task; this maintenance
   document grants no application permission.

## Sourcing boundary

API-only/offline source lists, URL normalization and dedupe helpers may prepare
candidates. Apply remains an agent-driven, one-role-at-a-time Markdown process.
The retired `linkedin_external_harvest.py` browser automation is not an active
route: do not run it, even for read-only discovery. LinkedIn launch flows remain
frozen under POLICY; use official ATS sources or user-provided external URLs.

Legacy harvest CSVs may still be read as historical candidate lists; reclassify
an external URL, dedupe it and inspect its current page before any action.
Embedded Greenhouse URLs must resolve to the actual official job ID; unresolved
entries stay unresolved rather than being guessed into an application URL.

For statistics from retired-engine logs, read [ATS-BLOCKERS](ATS-BLOCKERS.md).
Its old row counts are failure evidence, never a current success rate.
