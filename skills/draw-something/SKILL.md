---
name: draw-something
description: >-
  Turn code changes, PR diffs, or other structured inputs into a visual artifact
  and a PDF. Pipeline: gather diff or content, optionally author a Cursor Canvas
  for in-IDE review, mirror the same structure in standalone HTML, run
  scripts/html-to-pdf.mjs to produce PDF. Use when the user asks to visualize a
  change-set, export a review to PDF, or "draw" diagrams/tables/diffs from git
  or GitHub PRs.
---

# Draw something (visualize → PDF)

End-to-end flow: **inputs (prefer code / diff)** → **visual layout** → **static HTML** → **PDF file**. Cursor’s live Canvas and PDF export use **different runtimes**; the skill keeps them in sync by design.

## When to use

- User wants a **visual** summary of a PR, branch diff, or pasted patch.
- User wants a **downloadable PDF** of that visualization (not only chat or IDE preview).
- User references this skill name or phrases like “画出来 / 导出 PDF / diff 可视化”.

## Inputs (pick one)

1. **GitHub PR** (preferred): `gh pr view <n> --json baseRefName,headRefName` and `gh pr diff <n>` (diff is against the PR base — not arbitrary local branches unless user specifies).
2. **Local git**: `git diff <base>...<head>` or `git merge-base` + `git diff` for the same semantics as “changes vs base”.
3. **Arbitrary content**: user paste, paths to files, or structured notes — normalize into sections before laying out.

If the PR URL or number is missing and the user meant a specific change-set, **ask** which PR or base/head before building artifacts.

## Step A — Visual design (optional but recommended)

**Cursor Canvas (in-IDE only)**  
Read `~/.cursor/skills-cursor/canvas/SKILL.md` and `sdk/index.d.ts` for components. Rules:

- Write **one** file: `~/.cursor/projects/<workspace>/canvases/<slug>.canvas.tsx`.
- Import **only** from `cursor/canvas`; **no** `fetch`, no extra npm packages.
- Use `DiffView` / `Table` / `Card` / `Stack` as needed; flat, minimal styling per canvas policy.

Canvas is for **interactive review in the IDE**. It does **not** render in Node and has **no** official “export to PDF” API.

## Step B — Printable mirror (required for PDF)

Produce a **standalone** `.html` file that mirrors the same information hierarchy and emphasis as the Canvas (or the chosen layout if you skipped Canvas):

- Inline CSS; **print-friendly** (`@media print`, avoid broken tables across pages where possible).
- For field-level or line-level changes, use a small diff convention: e.g. classes for removed / added / unchanged rows (light red / green / neutral backgrounds), monospace for lists.
- **No network**: all data embedded in the HTML.

Place the HTML wherever fits the current workspace (e.g. `scripts/<topic>-print.html` in the repo).

**For PR code-change PDFs, follow the style template in the next section — do not invent new styling.** Copy the reference HTML and adapt its content blocks; keep the tokens, typography, structure, and diff conventions unchanged.

## PR diff style template

The canonical reference is `scripts/pr-1350-canvas-print.html`. Copy that file and replace its content; do **not** rebuild the CSS from scratch. If the reference file is unavailable, reconstruct it from the outline below.

**Color tokens** (CSS variables on `:root`)

- `--ink: #0f172a` · `--muted: #475569` · `--line: #e2e8f0` · `--accent: #1e293b`
- `--page: #ffffff` · `--panel: #f8fafc` (section header) · darker panel `#f1f5f9` for unchanged headers
- Removed: `--del-bg: #fef2f2` · `--del-ink: #991b1b` · `--del-border: #fecaca`
- Added: `--add-bg: #ecfdf5` · `--add-ink: #065f46` · `--add-border: #a7f3d0`
- Unchanged: `--keep-bg: #ffffff` · `--keep-ink: #0f172a`

**Typography**

- UI stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif` (CJK fallbacks required — most PRs have Chinese context).
- Mono stack: `"SF Mono", Menlo, Consolas, monospace` — used for CLI name, tool-id, all diff `<pre>` blocks.
- Base `12px` / line-height `1.45`. h1 `20px`, section h2 `13px`, tool-id `11px`, legend / summary / subheader `10.5px`, badge `9.5px` uppercase.

**Document anatomy**

- `header.doc`: h1 title + `<p>` PR metadata (PR number, base → head, key file paths in `<code>`) + second `<p>` describing scope + `.legend` swatches (`del` / `add` / `keep`). Bottom border `2px solid var(--accent)`.
- `.divider` between groups (e.g. "Changed CLIs" / "Unchanged CLIs") — top border `2px solid var(--accent)`, bold 13px title, muted 11px `.sub` line underneath.
- Repeated `section.tool` cards.
- `footer.doc`: one-line wrap-up, top border, muted 10.5px.

**Tool section card** (`section.tool`)

- Rounded `6px` border, `break-inside: avoid` + `page-break-inside: avoid` so the card never splits across pages.
- `header` with `var(--panel)` background: flex row with `<h2>` on the left, right-aligned `.summary` (muted, `max-width: 55%`).
  - `<h2>` = `<span class="cli">` (mono, accent color) + `<span class="tool-id">` (muted mono 11px). Append `· view=…` or extra mode hints inside `.tool-id`.
- `.cols`: 2-col grid (`1fr 1fr`) for Before / After. Use `.cols.single` (one column) when the section is reference-only.
- `.col`: mono 11px, line-height 1.55, left border between columns. Per-column `<h3>` in the UI font, uppercase muted — e.g. `Before`, `After`, or variant labels like `preview · also guide-changed re-preview`.
- Unchanged sections: add `unchanged` class → header gets the darker `#f1f5f9` panel. Append `<span class="badge">unchanged</span>` inside `<h2>`.

**Diff rendering** (inside `<pre>`)

- Each line is a `<span class="line {keep|add|del}">…</span>` — no newlines between spans; `.line` has `display: block` so it flows like a real line.
- Indent classes `.i1` / `.i2` / `.i3` (14px / 28px / 42px) — nest fields without real tabs so diff backgrounds extend full-width.
- For intra-line changes (keep the line but highlight a word), wrap the word in `<span class="inline-del">…</span>`. Use sparingly; prefer full-line `del` / `add` when possible.
- Inline `<span class="comment">// note</span>` for muted-italic annotations (e.g. `// null`, `// from the study API`).
- When one card covers multiple variants (e.g. "bridge 未配置" vs "成功路径"), separate them with `<div class="subheader">…</div>` — first one uses `.subheader.first` to remove top margin.

**Print CSS**

```css
@media print {
  @page { size: A4; margin: 12mm 10mm; }
  .page { padding: 0; }
}
```

`section.tool { break-inside: avoid; page-break-inside: avoid; }` is required — without it, a card can split mid-diff and the PDF becomes unreadable.

**Content rules**

- Every CLI / endpoint / file touched by the PR gets its own `section.tool`. Don't collapse small ones.
- Changed sections show Before + After side by side.
- **Unchanged sections are only for API-surface / schema audit PRs** (e.g. trimming response fields, renaming routes) where the reader benefits from seeing the full unchanged surface alongside the diff. For typical feature or bug-fix PRs, omit them — unchanged files should not appear in the PDF.
- The `.summary` line is one sentence explaining *why* the change was made (the whitelist rationale, the field dropped), not *what* the diff shows.

## Step C — Generate PDF

**Workspace with the helper script:**

```bash
node scripts/html-to-pdf.mjs <path-to-print.html> <path-to-output.pdf>
```

Run from that repository’s root. The script uses **Chrome / Chromium / Edge headless** (`--print-to-pdf`). On macOS it checks common app paths; Linux uses `which`; Windows uses standard install paths.

**Other workspaces:** copy `scripts/html-to-pdf.mjs` into the project, or call Chrome headless directly, e.g.:

```text
<chrome> --headless=new --disable-gpu --print-to-pdf=<out.pdf> file://<absolute-path-to.html>
```

- **`<path-to-output.pdf>`** is user-chosen (absolute or relative to CWD), e.g. `~/Desktop/review.pdf`.

If the script is missing or the browser is not found:

- **Fallback**: install Chrome, or add a tiny **Playwright** one-off (`page.goto('file://…')` + `page.pdf()`), or document manual **Print → Save as PDF** from a browser opening the HTML file.

## Step D — Verify

- Confirm the **PDF exists**, size **> 0** bytes, and opens.
- Tell the user the **absolute path** to the PDF and the **HTML source** path so they can regenerate after edits.

## Optional: PR content structure

If the source is a PR, you may **reuse the mental model** from `pr-review-canvas` (core logic → wiring → boilerplate) to order sections in Canvas/HTML/PDF — but the deliverable here is still **one coherent visual + PDF**, not a second full canvas spec.

## Anti-patterns

- Passing a `.canvas.tsx` file into `html-to-pdf.mjs` — **unsupported**; generate HTML instead.
- Hardcoding hex colors in Canvas — use `useHostTheme()` tokens per canvas skill.
- Claiming PDF export without running Step C or opening the HTML in a browser for manual print.

## Reference assets (canonical script + example)

Keep your own copy of these two helper files (the originals may be unavailable):

- `scripts/html-to-pdf.mjs` — headless print helper.
- **Canonical style template for PR diffs**: `scripts/pr-1350-canvas-print.html` (paired output: `scripts/pr-1350-cli-mcp-field-diff.pdf`). Copy this file and replace its content when producing a new PR code-change PDF — do not rewrite the CSS.

This is the **global** copy under `~/.cursor/skills/`.

## Where Claude / Cursor load this skill

- **Claude Code** (desktop or CLI) discovers skills under **`~/.claude/skills/<name>/SKILL.md`** and **`./.claude/skills/`** in the project. It does **not** automatically load `~/.cursor/skills/`.
- **Cursor** may list skills from `~/.cursor/skills/` depending on version; do not assume parity with Claude.

**Recommended install (one canonical copy, symlinks elsewhere):**

```bash
# Canonical content (edit only this copy)
# ~/.cursor/skills/draw-something/SKILL.md

# Claude Code (user-wide)
ln -sf ~/.cursor/skills/draw-something ~/.claude/skills/draw-something

# Optional: one repo that should always see the skill
ln -sf ~/.cursor/skills/draw-something /path/to/repo/.claude/skills/draw-something
```

After adding symlinks, **restart Claude Code** or start a new session so the skill index refreshes.
