# Validation

Run every check and report each result with numbers in the final reply. A check that cannot run (no node or Chrome) is reported as not run.

1. `atlas.json` is internally consistent: every node id used in edges, flows, stops, events and risks exists, and counts are within the limits in `atlas-schema.md`.
2. Every hash resolves: `git cat-file -e <hash>^{commit}`. Every path exists at REF: `git ls-tree -r --name-only <ref>`. Every `path:line` range lies within the file. Every PR number exists: `gh pr view`, or fetch the whole set once with `gh pr list --state all --json number` and compare.
3. For events that carry a hash, the event date is within 3 days of the commit date.
4. Semantic sampling: pick at least 10 random facts or events, reread the code or diff, and confirm the text matches the evidence. Report sample size and matches; fix mismatches and resample.
5. Page: the inline scripts pass `node --check`; headless Chrome loads the page; the node count equals `nodes.length`; the console has no errors; there is no horizontal overflow at 390px; there are no external resource references except GitHub permalinks. Example (macOS, adjust the Chrome path for your OS): `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-first-run --user-data-dir=<tmp> --virtual-time-budget=5000 --enable-logging=stderr --v=0 --dump-dom "file://<abs path>/index.html" > dom.html 2> err.txt`, then `grep -c CONSOLE err.txt` should print 0.
6. No secret-shaped strings in the page.
7. Coverage numbers equal what `coverage` actually records.
8. If `machines` exist, also run the model health check and the reference checks in `lifecycle-layer.md`.

## Pitfalls that have bitten before

- `git log --since=2026-10-27` (a bare date) means that date at the current time of day, so earlier commits of that day are missed. Write `--since="2026-10-27 00:00:00"` or use a sha range.
- `:(glob)dir*` matches only top-level entries; to match files inside directories write `:(glob)dir*/**`.
- `git shortlog` needs an explicit `HEAD` when it is not on a terminal, otherwise it reads stdin.
- A shallow clone (`--depth`) silently drops history, so event dates and turning points come out wrong.
- When counting elements in a dumped DOM with `grep`, the handoff block is part of the dump. Write search patterns so that they do not match their own text, for example `class="nod[e] "`.
