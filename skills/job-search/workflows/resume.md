# Select or update a resume

Use for choosing a CV, reviewing its fit, updating experience evidence, or making
an expressly requested resume revision. This stage does not submit applications.

## Establish the requested change

Read [shared sources](../references/shared-state.md), the target posting if any,
and only the evidence relevant to the request. Distinguish three operations:

1. **Select an existing PDF:** the normal daily application path.
2. **Refresh experience evidence:** mine or reconcile facts without changing PDFs.
3. **Revise the curated resume:** change the generation source deliberately,
   render the resulting PDFs, verify them, and update the baseline through the
   established build workflow.

A request to search, apply, or prepare an interview does not implicitly request
a PDF rebuild. Prefer an existing suitable artifact for those tasks.

## Existing PDF selection

- Default outbound English applications use the curated AI Agent Engineer 1P EN
  PDF resolved through the profile's resume paths.
- Use 2P EN for explicit high-priority, referral, or manual-review applications
  where the additional detail is useful. Keep the user's requested variant.
- Resolve legacy AI Agent Infra / Backend Platform / General SWE aliases to the
  current 1P EN artifact rather than failing or generating replacements.
- Verify its hash against `pdf-hashes.txt` before application use. Drift needs
  investigation; never silently re-baseline a changed file to pass preflight.

## Evidence and curated edits

Use [gh-resume-builder](../../gh-resume-builder/SKILL.md) when the task actually
requires refreshing GitHub/PR evidence or a public proof package. It owns mined
Markdown, not recruiter-facing PDFs, and is not part of each nightly run.

Every experience claim, number, scope and date must trace to a reliable source
or a confirmed user fact. Preserve contributory versus ownership wording.
Apply the [outbound content policy](../../daily-job-apply/guards/stealth-rules.md).
Public portfolio work may reuse the evidence, but a resume request does not
authorize publishing a hire page or contacting anyone.

Recruiter-facing PDFs are generated only by `curated-script/build_resumes.py`.
For an authorized revision, edit that source through the established build flow;
do not patch PDFs or replace the builder with an ad hoc LaTeX/template pipeline.
Inspect rendered output and extractable text: contact details, reading order,
garbled glyphs, page count and target keywords must remain sensible. Keywords
without supporting experience remain gaps, not additions to make a check pass.

## Output and handoff

Report the selected file, or the evidence/source changes made and how the
resulting PDFs were verified. Keep a readable account of the actual change.
Do not rewrite previous submission snapshots with the new version.

Use [materials](materials.md) for a cover letter or application questions.
Continue to [apply](apply.md) only when application submission is authorized;
resume preparation alone never counts as a submitted application.
