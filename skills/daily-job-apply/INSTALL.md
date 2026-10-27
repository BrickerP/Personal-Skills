# Install the job-search workflows

The public entry is [job-search](../job-search/SKILL.md). The
`daily-job-apply` directory holds application policy, FROZEN answers, platform
playbooks and deterministic helpers used by that entry. Install them together.

## Repository install

Clone `BrickerP/Personal-Skills` to the location you use as the canonical skill
source, then run its `scripts/install.sh`. It links the skills into Codex,
Claude Code, Cursor and the agents compatibility directory. Use
`scripts/install.sh --status` to inspect links. Do not replace an existing
checkout or real skill directory containing local changes; compare and back it
up before changing its link.

Old standalone zip packs which contain only `daily-job-apply` are incomplete for
this layout. Preserve their runtime data and install the current repository;
no application engine or data migration is required.

## Runtime prerequisites

- A running real Chrome with the intended profile, and the installed chrome-use
  CLI connected to it. Follow the chrome-use skill's current installation and
  connection guide. The runtime identity is checked by
  [COLD-START.md](COLD-START.md).
- Python 3.10+ for deterministic dedupe, public API sourcing, hash or archive
  helpers when needed. Browsing and application judgment remain in Markdown.
- Current approved resume PDFs and their baseline, plus local candidate facts.

There is no Node/Playwright adapter dependency for the active application
workflow. Do not install or run a headless sourcing browser, fixed form filler,
retired CDP engine or batch apply runner as an installation step.

## Local configuration

For a fresh installation, copy `data/profile.json.example` to
`data/profile.json` only if a local profile does not already exist. Fill it with
that person's facts and resume paths. Personal profile values do not belong in
a public repository. The shipped FROZEN table in
[04-universal-web-apply.md](workflows/04-universal-web-apply.md) contains the
original user's approved facts; a different user must supply their own facts
before an application is prepared.

Optional path overrides and phone variables live in
`~/.config/daily-job-apply/env`. Edit an existing file in place; never overwrite
it with an example. Phone digits are read from the environment by the browser
operation and must never be printed or committed.

Keep existing work directories, tracker, ledger and Vault archives in place.
Path resolution follows `runtime/skill_paths.sh` and
[job-search shared state](../job-search/references/shared-state.md). Reading a
status or searching does not require creating runtime directories.

## Verify without submitting

Check the skill links and read [job-search](../job-search/SKILL.md). For an
application request, continue to [Apply](../job-search/workflows/apply.md), which
loads the current preflight and platform playbook. A connection check uses the
named session `jobapply2`, pins the configured Chrome identity and performs no
application writes. No install or link check submits a form.

The existing `daily-job-apply`, `job-apply-automation` and
`job-search-orchestrator` names remain compatibility entries for old callers.
Codex disables their implicit invocation through `agents/openai.yaml`;
`job-search` is the normal discovery entry. LinkedIn remains frozen.

## Retired resources

Keep old runtime/adapters and `archive/2026-10-cdp-retired/` out of the active
route. `runtime/run-next.sh` is a retirement stub, not a job-search command.
Neither a fresh install nor a scheduler should execute an old round manifest,
Easy Apply runner, Playwright/CDP fill adapter or browser retry loop. Existing
platform experience lives in the maintained Markdown playbooks and FIELD-NOTES.
