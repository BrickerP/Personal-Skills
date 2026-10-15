---
name: chrome-read-write
description: Control the user's Chrome (Debug) session on macOS via DevTools Protocol (:9222). List/activate tabs, read page state, fill fields, click visible controls. Same browser as PengMacBro chrome-devtools-mcp — not AppleScript, not regular Chrome.
---

# Chrome Read Write (CDP)

## Which Chrome?

This skill talks to **Chrome (Debug)** only:

- Profile: `~/Library/Application Support/Google/Chrome-Debug`
- Launcher: `~/bin/chrome-debug.sh` or Dock **Chrome (Debug)**
- CDP endpoint: `http://127.0.0.1:9222` (override with `CHROME_CDP_HOST` / `CHROME_CDP_PORT`)

Tabs in the **regular** Chrome window do **not** appear here. Open pages in Chrome (Debug) when you need the agent to see them.

Preflight (run before blaming scripts):

```bash
curl -s http://127.0.0.1:9222/json/version | head -c 120
```

Expect JSON with `"Browser": "Chrome/..."`. If it fails, start Chrome (Debug) first.
The helper scripts call `~/bin/chrome-debug.sh` once as a background recovery path when `:9222` is down.

When **PengMacBro-Chrome** MCP tools are available (`mcp__proxy__PengMacBro-Chrome__*`), prefer those for the same session — this skill is the **local shell fallback** when MCP is not loaded.

## Safety

- Resolve **`target_id`** from `chrome_tabs.sh` before every write; re-list after navigation or new tabs.
- Set `CHROME_EVAL_URL_MUST_CONTAIN=<substring>` before writes when the site is known.
- Do not submit purchases, messages, or irreversible actions unless the user explicitly asked.
- First `chrome_eval.sh` installs `chrome-remote-interface` under `scripts/.cdp-deps` (one-time, needs network).

## Workflow

Skill root: `~/.codex/skills/chrome-read-write` (or this repo copy under `scripts/`).

```bash
SKILL=~/.codex/skills/chrome-read-write

"$SKILL/scripts/chrome_tabs.sh"
"$SKILL/scripts/chrome_tabs.sh" example.com

"$SKILL/scripts/chrome_select_tab.sh" <target_id>

"$SKILL/scripts/chrome_eval.sh" <target_id> "$SKILL/scripts/read_page.js"
"$SKILL/scripts/chrome_eval.sh" <target_id> 'JSON.stringify({title: document.title, url: location.href})'

CHROME_EVAL_URL_MUST_CONTAIN=example.com \
  "$SKILL/scripts/fill_selector.py" <target_id> 'textarea[name="q"]' 'hello'

CHROME_EVAL_URL_MUST_CONTAIN=example.com \
  "$SKILL/scripts/click_text.py" <target_id> 'Submit'
```

Tab list format (note **`target=`**, not `window=`):

```text
target=E197B017... tab=1 title=... url=https://...
```

## Scripts

| File | Role |
|------|------|
| `chrome_tabs.sh [pattern]` | List page targets from `:9222/json/list` |
| `chrome_select_tab.sh <target_id>` | Activate tab; print URL + title |
| `chrome_eval.sh <target_id> <js_file_or_inline_js>` | Run JS in tab via CDP |
| `read_page.js` | Page snapshot JSON |
| `fill_selector.py <target_id> <css> <text> [--submit]` | Fill input/textarea/contenteditable |
| `click_text.py <target_id> <label>` | Click by visible label |
| `cdp_ensure_deps.sh` | Install CDP npm deps locally |

## Write rules

- Known field → `fill_selector.py`; known label → `click_text.py`; complex DOM → temp `.js` + `chrome_eval.sh`.
- Read after every meaningful write; cite page evidence, not assumptions.

## React / `isTrusted` sites

Some SPAs ignore untrusted `element.click()`. Patch before pointer sequences:

```javascript
['Event','MouseEvent','PointerEvent'].forEach((n) =>
  Object.defineProperty(window[n].prototype, 'isTrusted', { get: () => true, configurable: true }));
```

Then dispatch full `pointerdown` → `mouseup` → `click` at element center, or re-run `chrome_tabs.sh` after actions that open new tabs.

## Mercor helpers

Use **target_id** (from `chrome_tabs.sh mercor`), not window/tab index:

```bash
"$SKILL/scripts/mercor_scrape.sh" <target_id>
"$SKILL/scripts/mercor_submit_job.sh" <target_id> <listing_id>
```

Job pages: navigate via `/jobs/list_*`, trusted pointer click on Submit — see inline JS in `mercor_submit_job.sh`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `chrome CDP: no browser on http://127.0.0.1:9222` | Run `~/bin/chrome-debug.sh`; if stale Debug Chrome exists without CDP, quit only Debug Chrome and retry |
| Tab missing | Page opened in **regular** Chrome — reopen in Debug |
| `target not found` | Re-run `chrome_tabs.sh`; IDs change when tabs close |
| MCP works but scripts fail | Same port 9222; ensure Debug Chrome is the one running |
