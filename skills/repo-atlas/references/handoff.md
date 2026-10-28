# Handoff block

Hide an update guide for the next agent inside the HTML, so that anyone holding the repo and the page knows how to update the map. The block is not rendered.

## Form

1. A short HTML comment inside `<head>`, a few lines, pointing at the block below ("generated file, do not edit; the full guide is in the script block with id agent-handoff"). Do not write a literal `<script ... id="agent-handoff">` tag inside the comment, or naive regex extraction of the block breaks.
2. A `<script type="text/markdown" id="agent-handoff">` element holding markdown. The text must not contain `</` or `<!--`; make the build fail if it does.

## Content

- What the page is and who it is for.
- Where the sources are (`atlas.json`, the generator script, the template) and the single command that rebuilds the page.
- Baseline: the sha in `meta.ref`, and the paths each node covers.
- How to update. After `git fetch`, list drift with `git log --no-merges <baseline-sha>..origin/<default-branch> -- <paths>`.
  - Do not use `--since=<date>`: without a time, git uses the current time of day and misses earlier commits of that day.
  - In pathspecs use directory prefixes. A glob must be written `:(glob)dir*/**`, because `:(glob)dir*` matches only top-level entries.
  - Sort every change into one of four kinds: unrelated; detail changed; structure changed (nodes or edges added or removed; read the diff); release state changed (a new release). State which `atlas.json` fields each kind edits.
- The validation checklist and the iron rules.
- What is not done and the known gaps.

Do not write secrets or machine-private paths into the block.
