---
name: gh-resume-builder
description: Mine a GitHub user's merged PRs across an org/repos and refresh the bilingual evidence-ledger Markdown (mined source-of-truth). DOES NOT regenerate recruiter-facing application PDFs — those are owned exclusively by build_resumes.py. Use when user asks "refresh resume markdown from my commits", "update mined evidence ledger", or "summarize what I shipped at <company>".
metadata:
  short-description: Mine GitHub PRs into bilingual evidence-ledger Markdown (Markdown-only)
---

# gh-resume-builder

## What it does

Turns a GitHub author's merged-PR history (within one org, or across specific repos) into a polished **bilingual evidence ledger** in Markdown. The mined Markdown files are the durable source-of-truth for commits and PR evidence.

**⚠️ This skill DOES NOT generate recruiter-facing application PDFs.** Those PDFs live at:

```
/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/
  Resume_YupengLu_AI_Agent_Infra.pdf
  Resume_YupengLu_Backend_Platform.pdf
  Resume_YupengLu_General_SWE.pdf
```

…and are generated **only** by:

```
/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/curated-script/build_resumes.py
```

This skill never touches those files. See the "Application PDF boundary" section below.

## When to use

- "Refresh / update my resume markdown" — re-run with the previous snapshot date as the floor.
- "Summarize what I shipped over the last N months at `<company>`."
- "Write my evidence ledger from my commits at `<org>`."
- "Build a proof-package / case study from my GitHub history."

## When NOT to use

- ❌ "Regenerate / rebuild my application PDF" — use `curated-script/build_resumes.py` instead.
- ❌ "Update the resume I send to recruiters" — that is a curated artifact; edit `build_resumes.py` then re-run it.
- ❌ "Make a PDF from the mined markdown" — application PDFs do not derive from mined markdown; they derive from `build_resumes.py`.

## Application PDF boundary (HARD RULE)

These three files are **off-limits to this skill**:

```
/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Infra.pdf
/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_Backend_Platform.pdf
/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_General_SWE.pdf
```

Before AND after any run, the agent MUST verify hashes have not changed:

```bash
APP_DIR="/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent"
(
  cd "$APP_DIR"
  shasum -a 256 Resume_YupengLu_AI_Agent_Infra.pdf \
                Resume_YupengLu_Backend_Platform.pdf \
                Resume_YupengLu_General_SWE.pdf
)
```

If any hash differs from `$APP_DIR/pdf-hashes.txt`, STOP and surface the discrepancy to the user — do not silently proceed.

## Prerequisites

1. `gh` authenticated as the **author whose PRs you are mining**. Verify with `gh auth status`.
2. `jq` available locally.
3. Confirm with the user up front:
   - **GitHub login** to mine (e.g. `yupeng-dev`)
   - **Target org or repo list** (e.g. `cookiy-ai`, or `owner/repo` pairs)
   - **Window** (default: from the previous snapshot date; or full history on first run)
   - **Output directory** (default: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/source-of-truth/`)

## File policy on this machine

| Path | Owner | Mutability |
|---|---|---|
| `source-of-truth/resume_yupeng_en.md` | gh-resume-builder | Append/update by this skill |
| `source-of-truth/resume_yupeng_zh.md` | gh-resume-builder | Append/update by this skill |
| `curated-script/build_resumes.py` | Human + Mira | Manual edit only; never auto-rewritten |
| `application-ai-agent/Resume_YupengLu_*.pdf` | build_resumes.py | **READ-ONLY for this skill** |
| `application-ai-agent/pdf-hashes.txt` | build_resumes.py wrapper | Updated by the rebuild wrapper, not this skill |
| `resume-proof/*.md` | Optional case-study mode | Append/update by this skill |

## Pipeline

### Step 1 — Pull all merged PRs

`gh search prs` requires separate calls per state. Run both in parallel:

```bash
WORK=/tmp/resume-$(date +%s)
mkdir -p "$WORK"

gh search prs --author=<LOGIN> --owner=<ORG> --limit 1000 --state=open \
  --json repository,number,title,createdAt,closedAt,isDraft \
  > "$WORK/prs_open.json"

gh search prs --author=<LOGIN> --owner=<ORG> --limit 1000 --state=closed \
  --json repository,number,title,createdAt,closedAt,isDraft \
  > "$WORK/prs_closed.json"
```

For incremental updates, append `--merged-at=">=YYYY-MM-DD"` (the previous snapshot date + 1 day).

> Notes
> - `gh search prs` does **not** accept `--state=all` and does **not** expose `mergedAt`. Use the two-state pattern above.
> - Each query caps at **1000 results**. Chunk by date range if needed.
> - For mining a specific repo list instead of a whole org, use `--repo owner/repo` (repeatable) instead of `--owner`.
> - Private repos that local git can reach but `gh` cannot: keep that evidence boundary explicit (note local-only counts; do not mix into GitHub PR totals).

### Step 2 — Normalize and inspect

```bash
jq -s '.[0] + .[1] | map({repo: .repository.name, n: .number, t: .title, d: .createdAt})' \
  "$WORK/prs_open.json" "$WORK/prs_closed.json" > "$WORK/prs_all.json"

# Per-repo distribution
jq -r '.[].repo' "$WORK/prs_all.json" | sort | uniq -c | sort -rn

# Activity by month
jq -r '.[].d[0:7]' "$WORK/prs_all.json" | sort | uniq -c

# Conventional-commit type distribution
jq -r '.[].t' "$WORK/prs_all.json" \
  | sed -E 's/^([a-z]+)(\([^)]+\))?:.*/\1/' \
  | grep -E '^(feat|fix|chore|refactor|docs|test|perf|style|build|ci|revert)$' \
  | sort | uniq -c | sort -rn

# Top scopes — these become section headers in the evidence ledger
jq -r '.[].t' "$WORK/prs_all.json" \
  | grep -oE '^[a-z]+\(([^)]+)\)' \
  | sort | uniq -c | sort -rn | head -15
```

### Step 3 — Cluster by scope, sample titles per cluster

For each top scope, sample ≥ 20 unique titles before claiming ownership:

```bash
for scope in mcp billing oauth cli v1 quant; do
  echo "=== $scope ==="
  jq -r ".[] | select(.t|test(\"^[a-z]+\\\\($scope\")) | .t" "$WORK/prs_all.json" \
    | sort -u | head -40
done
```

### Step 4 — Synthesize the evidence ledger (Markdown only)

For each cluster, write 3–6 bullets that:
- Lead with the artifact, not the activity
- Quote concrete identifiers from PR titles
- Bold the noun, not the verb
- One bullet = one capability

Overview block at the top:

| Metric | Value |
| --- | --- |
| Merged PRs | N |
| Top repo | M |
| Avg PRs / month | … (peak …) |
| Type distribution | fix X · feat Y · chore Z · refactor W |
| Top scopes | scope1 N · scope2 N · … |

### Step 5 — Stamp the snapshot

```markdown
> 📌 **Resume snapshot cutoff: YYYY-MM-DD**
> For the next update, only ingest commits / PRs from `YYYY-MM-DD+1` onward:
>
> ```bash
> gh search prs --author=<LOGIN> --owner=<ORG> --state=closed \
>   --merged-at=">=YYYY-MM-DD+1" --limit 1000 \
>   --json repository,number,title,createdAt
> ```
```

### Step 6 — Write the two mined-source Markdown files

- `source-of-truth/resume_yupeng_en.md`
- `source-of-truth/resume_yupeng_zh.md`

Structurally identical (same sections, same metric table, same snapshot stamp).

### Step 7 — Notify the user that PDFs are stale

After updating mined markdown, ALWAYS end the run with:

```markdown
✅ Mined markdown updated. New scopes / metrics worth promoting into the
recruiter-facing PDFs:
- <bullet 1 — what's new and which of the 3 PDFs it likely belongs in>
- <bullet 2>

⚠️ Application PDFs were NOT touched. If you want these changes reflected
on the application PDFs, edit:
  /Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/curated-script/build_resumes.py
and re-run:
  cd /Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/curated-script
  python3 build_resumes.py
  cp Resume_YupengLu_AI_Agent_Infra.pdf Resume_YupengLu_Backend_Platform.pdf Resume_YupengLu_General_SWE.pdf ../application-ai-agent/
  cd ../application-ai-agent
  shasum -a 256 *.pdf > pdf-hashes.txt
```

### Output skeleton (markdown only)

```markdown
# <Name> — Evidence Ledger

**GitHub**: github.com/<login>
**Window**: YYYY-MM-DD → YYYY-MM-DD (~N weeks across M repos)

> 📌 **Resume snapshot cutoff: YYYY-MM-DD**
> [incremental command block]

---

## Overview

| Metric | Value |
| ... | ... |

---

## Highlights

### 1. <Cluster name> (~N PRs)
- ...

### 2. <Cluster name>
- ...

---

## Stack
- **Languages**: ...
- **Backend**: ...
- **Frontend**: ...
```

## Refresh workflow

When the user says "update my resume markdown":

1. Hash the 3 application PDFs (preflight). Store hash list.
2. Read the **snapshot cutoff date** from the existing `resume_*.md`.
3. Re-run Step 1 with `--merged-at=">=<cutoff+1>"`.
4. Repeat Steps 2–4 only on the delta.
5. Append new bullets under existing sections; don't rewrite proven content.
6. Update the snapshot date and metric table totals.
7. Re-hash the 3 application PDFs (postflight). MUST match preflight.
8. Print the "PDFs are stale" reminder from Step 7 above.

## Anti-patterns (do not do)

- ❌ Never run `python3 build_resumes.py` from this skill. That script is the user's curated PDF source — touching it = silently downgrading the resume.
- ❌ Never write to `application-ai-agent/*.pdf` from this skill. Even an accidental `pdftotext` round-trip into a PDF would corrupt them.
- ❌ Don't summarize from `gh api search/commits` — rate-limited, default-branch-only, caps ~170 results. Use `gh search prs` instead.
- ❌ Don't paraphrase after reading 5 titles. Sample ≥ 20 unique titles per scope.
- ❌ Don't merge PRs from the user's other accounts. Confirm the exact GitHub login (e.g. `yupeng-dev` ≠ `BrickerP`).
- ❌ Don't fabricate metrics. Every bullet must trace to ≥ 1 PR title in the dataset.
- ❌ Don't add operational snapshot command blocks to the mined markdown if the user opts out.

## Case study discovery mode (proof-package branch)

Use this branch when the user wants LinkedIn Featured material, case studies, or asks which PRs/commits best prove ownership. Outputs go to `resume-proof/` under the same Vault folder. PDFs and `build_resumes.py` remain off-limits.

See the dedicated proof-package mining commands (npm view, public repo metadata, cherry-pick / cross-branch evidence) — these are markdown-only outputs in `resume-proof/*.md`. No PDF generation in this branch either.

## Current-machine notes (2026-06-02)

- Mined source-of-truth: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/source-of-truth/{resume_yupeng_en.md, resume_yupeng_zh.md}`.
- Curated PDF script: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/curated-script/build_resumes.py`. This file is the single source of truth for application PDFs and is **edited by the human (with Mira's help), never by this skill**.
- Application PDFs in `application-ai-agent/`:
  - `Resume_YupengLu_AI_Agent_Infra.pdf` — AI Agent Infrastructure version
  - `Resume_YupengLu_Backend_Platform.pdf` — Backend / Platform version
  - `Resume_YupengLu_General_SWE.pdf` — General SWE version
- All three PDFs: 2-page Letter, ATS-friendly single-column, header email `yplmicro@gmail.com`, GitHub `BrickerP`, location `San Francisco Bay Area` (NO "relocating from Beijing" in resume body — privacy decision).
- Verified GitHub PR totals at 2026-06-02: 741 merged PRs in 10 months across Cookiy AI; 41 MCP tools, 4 MCP servers, 12 streaming endpoints, 7 L0–L6 release-gate profiles, 291 E2E cases, 314 fix PRs. These numbers are baked into `build_resumes.py`; refresh that script when they change materially.
- `BrickerP/quant-trading` and dating repo are private; do NOT include their PR counts in Cookiy totals.
