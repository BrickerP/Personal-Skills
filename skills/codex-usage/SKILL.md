---
name: codex-usage
description: Create a single local AI coding usage comparison report for Codex, Claude Code, Cursor, and Comate from this computer's local files, local sessions, and local authenticated Cursor usage records. Use when the user asks to view Codex/Cursor/Claude Code/Comate token usage, local AI usage records, AI coding spending, request history, comparative usage, or Chinese triggers like "查看token用量", "查看最近的codex花费", "Cursor用量", "Claude Code用量", "Comate用量", "本地调用记录", or asks to run `npx @ccusage/codex@latest`.
---

# Local AI Usage Comparison Report

## Output Contract

- When the user invokes this skill without specifying the output type, ask them to choose one of:
  1. **Whole HTML report** — one self-contained interactive HTML file (ECharts grouped **bar** charts + time-window controls). Open it in a browser. Static PNG cannot offer a draggable time window; use HTML for that.
  2. **Today's usage only** — stdout text table for today's token usage and cost by tool, plus the total. Do not create an HTML/PNG artifact for this mode.
- If the user explicitly asks for "today", "today's usage", or "today's price", run today's usage mode directly. If they ask for the report, chart, or HTML, run the whole HTML report directly.
- **Optional:** pass `--png` to also write a screenshot (best-effort; needs network for the ECharts script unless you host `echarts.min.js` locally).
- Do not leave JSON, CSV, or stray HTML copies as artifacts besides the chosen `--out` path. The generator may use a temp directory and delete it.
- Default to full local history. Do not pass `--since`, `--until`, `-s`, or `-u` unless the user asks for a time span.
- After a successful run, print the output HTML path (and the PNG path on a second line if `--png` was set).
- For today's usage mode, print the table output directly. It should include today's date, timezone, Codex / Claude Code / Cursor / Comate tokens and USD, and the combined total.

## Default Workflow

Whole HTML report:

```bash
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/ai_usage_comparison_image.py
```

Produces something like:

```text
/tmp/ai-usage-comparison-YYYYMMDD-HHMMSS.html
```

Specific paths:

```bash
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/ai_usage_comparison_image.py --out /tmp/ai-usage-comparison.html
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/ai_usage_comparison_image.py --out /tmp/ai-usage-comparison.html --png /tmp/ai-usage-comparison.png
```

Today's usage only:

```bash
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/ai_usage_comparison_image.py --today
```

## Interactivity

- Deliverable is **one `.html` file** you open in a browser — **not** a static table. PNG cannot pan/zoom; use HTML when you need a time window.
- **Stacked grouped bar charts** (not line charts): each calendar day has adjacent columns per tool (Codex, Claude Code, Cursor, Comate). Top = total tokens; middle = cache tokens where applicable (Codex cache read, Claude cache create+read, Cursor cache write+read; Comate has no cache); bottom = USD spend (Comate cost is always 0). Hover tooltips show the full per-tool token breakdown (input / cache / output / reasoning).
- Per-tool **cards** also show input, cache, output (and reasoning for Codex) for the visible time window.
- **Trackpad-friendly:** wide bottom **slider**; **presets** (7 / 30 / 90 / all days); **date pickers + Apply**; **◀ ▶ nudge** to slide the window. Plot **inside** zoom avoids scroll-wheel zoom (reduces accidental pinch/zoom noise); toolbox **rectangle zoom** + restore remains available.
- **Selection totals** update for the visible slice only (per-tool tokens and USD sums).
- The HTML includes a short **“How the numbers are fetched”** block (exact ccusage commands + Cursor roll-up) for interviews.
- The skill ships `scripts/vendor/echarts.min.js` (~1 MB) so the generator can **embed ECharts** in the HTML for **offline** use. If that file is missing, the page falls back to jsDelivr (needs network).

## Data Sources

- Codex / Claude Code: `npx ccusage@latest … --json --offline` (Ducc counts under Claude Code)
- Cursor: Dashboard API + filtered events rolled up by calendar day in the report timezone
- Comate: `~/.comate-engine/store/chat_session_*`, positive `contextUsed` deltas as tokens (cost always 0)
- Helpers: `local_ai_usage_records.py`, `comate_usage.py`, `machine_fragments.py`

For the multi-Mac GitHub Pages publisher (`~/.local/share/ai-usage-report`), each Mac append-only updates `public/machines/<id>.json` (seed once; later freeze history / append gaps / refresh today; `--force-reseed` to rewrite). Publish SUMs Codex/Claude/Comate by day; Cursor stays account-level.

## Cursor API Notes

Authenticated `GetAggregatedUsageEvents` + paginated `GetFilteredUsageEvents` for history and per-day cost/tokens. Same scope rules as in the previous skill revision (individual `teamId: 0` vs team ids).

## Failure Handling

- If `ccusage` fails, report the failed command; do not emit a report unless the user asks for degraded output.
- If Cursor API fails, Codex/Claude/Comate curves still work; Cursor series stay at zero (or prior series when merging Pages fragments) and the Cursor card note explains API unavailability.
- Never print secrets.

## Optional Debug Helpers

```bash
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/local_ai_usage_records.py
python3 /Users/yupeng/.codex/skills/codex-usage/scripts/cursor_usage_api_probe.py
```
