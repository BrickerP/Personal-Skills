# Recon and evidence

Commands below were checked against `gh` 2.96 and git 2.55. OWNER/NAME is the resolved repo.

## Stage 0: recon

- Metadata: `gh repo view OWNER/NAME --json name,description,licenseInfo,primaryLanguage,languages,defaultBranchRef,pushedAt,isArchived,isFork,parent,diskUsage`. The default branch is not always `main` or `master`; use `defaultBranchRef`. For a fork look at `parent`; if the repo is archived, say so on the page.
- Clone: `git clone --filter=blob:none https://github.com/OWNER/NAME.git <tmpdir>`. This keeps full history and fetches file contents on demand. Never use `--depth`: a shallow clone loses the evolution you need. Resolve REF to a full sha and keep it as `meta.ref`.
- `gh` is rate-limited: take history from git and use `gh` only for what git lacks (PR descriptions, releases, language shares). Without `gh` or network, use the local clone only and put issues, PRs and releases into `coverage.not_read`.
- Structure: top-level directories; language shares (`gh api repos/OWNER/NAME/languages`); manifests (go.mod, package.json, pyproject.toml, Cargo.toml, pom.xml, ...); entry points (main, cmd, bin, app, server); tests and CI (`.github/workflows` shows how the project is built, tested and released, the most reliable "how to run" source); docs/, examples/, CHANGELOG, CONTRIBUTING, SECURITY, CODEOWNERS.
- Recon notes: type, entry points, trunk candidates, size, scope decision.

## Stage 2: evidence per node

Read entry and core files; write 3-6 facts per node, each with a tag and `path:line`; record the paths you read in `coverage.read`.

**History: find turning points, not a commit log.** Leads:

- `git log --no-merges --format='%h %cs %s' -- <path>`
- `git log --diff-filter=AD --name-status --format='%h %cs' -- <path>` for added or deleted files; use `--diff-filter=R` for renames
- `git log --shortstat` to spot large changes
- `gh release list -R OWNER/NAME`
- `gh pr list -R OWNER/NAME --state merged --limit 100 --json number,title,mergedAt,additions,deletions`; read a PR description with `gh pr view N -R OWNER/NAME --json title,body,files` to learn why it changed.

At most 8 events per node, each with a hash, PR number or tag. Take the date from the commit itself.

**Hotspots**: `git log --since=1.year --format= --name-only | sort | uniq -c | sort -rn | head -30`; then look for giant files and functions, TODO/FIXME clusters, and frequently changed areas with thin tests.

**Risks**: swallowed errors, network calls without timeouts, global mutable state, missing authentication, hard-coded credentials, commands or SQL built by string concatenation, outdated dependencies, clusters of bug issues (`gh issue list -R OWNER/NAME --state all --label bug --limit 50 --json number,title,createdAt`; label names vary by repo). Contribution concentration: `git shortlog -sn --no-merges HEAD` (the `HEAD` is required, otherwise git reads stdin when not on a terminal); report shares only, never names. Each risk gets evidence, a suggested action and a confidence; mark uncertain ones as unverified.

**Couplings**: things that must change or upgrade together: both ends of a protocol, schema and migrations, version numbers, config keys, generated code and its source.

**Docs vs code**: README or docs that disagree with the code, or describe features that are planned but not implemented, go into `docs_vs_code`.

**Release gap**: distance from the latest release or tag to the default branch, `git rev-list --count <tag>..<default-branch>`. If there is no release, write none.
