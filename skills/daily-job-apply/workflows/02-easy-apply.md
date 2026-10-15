# Channel 2: LinkedIn Easy Apply workflow

Use for bounded LinkedIn Easy Apply batches after the profile/resume/contact defaults are verified.

## Best window

- Preferred: Tue-Thu 06:00-10:00 Pacific Time.
- Never write to LinkedIn during BJT 09:00-19:00.
- Daily cap: 25 Easy Apply submissions.

## Preparation

1. Read `guards/stealth-rules.md` and `data/profile.json`.
2. Verify Chrome Debug and LinkedIn tab via `chrome-read-write`.
3. Confirm `Share profile updates with your network` is OFF before any profile change.
4. Use the current curated English PDF unless the user requests a specific PDF:
   - Default / high-volume Easy Apply -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`.
   - Explicit high-priority, referral, or manual-review application -> `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf`.
   - Older buckets (`AI Agent Infra`, `Backend Platform`, `General SWE`) must resolve to the 1P English PDF unless the user explicitly asks for 2P.
5. For JD-specific resumes beyond these three variants, exact keyword match should cover at least 75% of the JD's core keywords; output a dry-run match summary first.

## Mechanical helper

Use the existing sub-skill only for the browser mechanics:

```bash
LINKEDIN_SUBMIT=1 LINKEDIN_TARGET_NEW=25 LINKEDIN_EMAIL='yplmicro@gmail.com' LINKEDIN_PHONE='' LINKEDIN_PROFILE='https://www.linkedin.com/in/yupeng-lu-845a0b411/' LINKEDIN_EXPECTED_PROFILE='https://www.linkedin.com/in/yupeng-lu-845a0b411/' LINKEDIN_RESUME_STRATEGY='auto' node /Users/yupeng/.codex/skills/linkedin-application-agent/scripts/easy_apply_batch.cjs
```

Use `LINKEDIN_DRY_RUN=1` when preparing or validating without final submissions.
The helper must print same-day cap accounting, profile preflight result, resume variant counts, and the tracker/ledger paths.
Do not provide a phone number while the user's US phone is inactive; if LinkedIn requires one, stop instead of submitting.

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
