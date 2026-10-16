# Channel 2: LinkedIn Easy Apply workflow

Use for bounded LinkedIn Easy Apply batches after the profile/resume/contact defaults are verified.

## Best window

- Preferred: Tue-Thu 06:00-10:00 Pacific Time.
- Never write to LinkedIn during BJT 09:00-19:00.
- Daily cap: 25 Easy Apply submissions.

## Preparation

1. Read `guards/stealth-rules.md` and `data/profile.json`.
2. Take over the LinkedIn tab via `chrome-use`: `chrome-use --session linkedin --browser yplmicro@gmail.com tab adopt linkedin.com` (`tab select` is refused for tabs the session did not create or adopt, and an adopted tab cannot be closed by the session). Read the `profile:` line it prints.
3. Confirm `Share profile updates with your network` is OFF before any profile change.
4. Use the current curated English PDF unless the user requests a specific PDF:
   - Default / high-volume Easy Apply -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`.
   - Explicit high-priority, referral, or manual-review application -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf`.
   - Older buckets (`AI Agent Infra`, `Backend Platform`, `General SWE`) must resolve to the 1P English PDF unless the user explicitly asks for 2P.
5. For JD-specific resumes beyond these three variants, exact keyword match should cover at least 75% of the JD's core keywords; output a dry-run match summary first.

## Mechanical helper (retired)

`linkedin-application-agent/scripts/easy_apply_batch.cjs` drove the removed Debug Chrome (port 9222) through the removed `chrome-read-write` skill, so it cannot start today, and LinkedIn applications are frozen (`COLD-START.md`, "LinkedIn freeze"). No chrome-use port exists: do not run the old command from earlier notes. If LinkedIn is ever unfrozen, drive Easy Apply by hand with chrome-use (`snapshot -i`, `fill`, `pick`, `upload`) under the field policy below.

A run must still report same-day cap accounting, the profile preflight result, resume variant counts, and the tracker/ledger paths. Phone fields follow the FROZEN rules in `04-universal-web-apply.md` (US number from `~/.config/daily-job-apply/env`, never typed into a command or reply); the old "no phone while the US number is inactive" stop is retired.

## Conservative field policy

- Authorized to work in the US: Yes.
- Needs sponsorship now/future: No.
- U.S. citizen: No.
- U.S. permanent resident / green card / protected individual: Yes.
- Demographics/veteran/disability: Prefer not to answer.
- Salary expectation: use a role-range-aware answer; if unknown, dry-run before submission.
- Exact location claims: do not claim a city/metro unless true or explicitly approved.
- Privacy/data-processing questions beyond normal LinkedIn boilerplate: stop and dry-run.

## Tracker

Upsert one row per touched JD in `~/job-hunt/tracker.csv`, including `Application_Submitted` = Yes/No and any review flags in Notes. Existing URLs must be updated when status/stage/notes change; do not skip a known URL if the current run reached a better state such as `Submitted`.

After the run, also append every touched job to `~/job-hunt/application-ledger.md` using one physical Markdown line per job:

```text
- <timestamp> | <status> | <company> — <role> | <JD_URL>
```

Replace `|` inside job titles with `/` so the line remains parseable.
