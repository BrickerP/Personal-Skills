---
name: browser-control
description: >-
  Control the user's real Chrome browser via two methods: Playwright MCP Bridge
  (full page interaction) and AppleScript (URL navigation). Use when the user
  asks to operate Chrome, automate web tasks, fill forms, click buttons, send
  emails, or test web UIs in their actual browser session.
---

# Browser control (real Chrome)

Two methods. Use Playwright MCP Bridge by default. Fall back to AppleScript for URL-only tasks or when MCP is unavailable.

## 1. Playwright MCP Bridge (primary — full control)

Connects to the user's running Chrome via the Playwright MCP Bridge extension. Can do everything: navigate, snapshot, click, fill, type, screenshot, evaluate JS, read console/network.

### Prerequisites (one-time)

1. Install **Playwright MCP Bridge** extension from Chrome Web Store:
   `https://chromewebstore.google.com/detail/playwright-mcp-bridge/gjgfobfkkhkfpolbgpnagmcgiaimnhdl`

2. Click the extension icon in Chrome toolbar → copy the `PLAYWRIGHT_MCP_EXTENSION_TOKEN`.

3. Add to `~/.cursor/mcp.json`:
   ```json
   {
     "chrome": {
       "command": "npx",
       "args": ["@playwright/mcp@latest", "--extension"],
       "env": {
         "PLAYWRIGHT_MCP_EXTENSION_TOKEN": "<token from extension popup>"
       }
     }
   }
   ```

4. Reload Cursor (`Cmd+Shift+P` → "Developer: Reload Window").

### MCP server name

The server appears as `user-chrome` in Cursor. Use `CallMcpTool` with `server: "user-chrome"`.

### Core workflow

```
1. browser_snapshot          → get page structure with element refs
2. browser_click ref=eXX    → click elements
3. browser_type ref=eXX     → type into inputs/textareas
4. browser_evaluate          → run JS for contenteditable fields or complex DOM
5. browser_run_code          → run multi-step Playwright code
6. browser_snapshot          → re-snapshot after any page change
```

### Key tools and usage

| Tool | When to use | Example args |
|---|---|---|
| `browser_navigate` | Go to a URL | `{"url": "https://mail.google.com"}` |
| `browser_snapshot` | Read page structure, get refs | `{"depth": 5}` (increase if too shallow) |
| `browser_click` | Click buttons/links | `{"ref": "e108", "element": "Compose button"}` |
| `browser_type` | Type into standard inputs | `{"ref": "eXX", "text": "hello"}` |
| `browser_press_key` | Keyboard shortcuts | `{"key": "Tab"}` or `{"key": "Meta+Enter"}` |
| `browser_evaluate` | Run JS on the page | `{"function": "() => { ... }"}` |
| `browser_run_code` | Multi-step Playwright | `{"code": "async (page) => { ... }"}` |
| `browser_take_screenshot` | Visual verification | `{}` |
| `browser_tabs` | List/create/switch tabs | `{"action": "list"}` |

### Gmail-specific patterns

**Compose via URL** (pre-fills To/Subject/Body — no element hunting needed):
```
https://mail.google.com/mail/?view=cm&fs=1&to=EMAIL&su=SUBJECT&body=BODY
```

**Fill the To field** (Gmail uses a hidden input, not a standard textbox):
```js
// via browser_evaluate
() => {
  const input = document.querySelector('input[aria-label="To recipients"]');
  if (input) {
    input.focus();
    input.value = 'user@example.com';
    input.dispatchEvent(new Event('input', {bubbles: true}));
  }
}
```

**Fill the Body** (contenteditable div — `browser_type` won't work, use keyboard):
```js
// via browser_run_code
async (page) => {
  const body = page.locator('div[aria-label="Message Body"]');
  await body.click();
  await page.keyboard.type('Your message here');
}
```

**Click Send**:
```js
// via browser_run_code — the Send button has a Unicode-rich aria-label
async (page) => {
  await page.locator('div[aria-label="Send ‪(⌘Enter)‬"]').click();
}
```

### Troubleshooting

| Error | Fix |
|---|---|
| "Target page, context or browser has been closed" | Extension not connected. Click extension icon → check token matches `mcp.json` → reload Cursor. |
| "Element is not an input/textarea" | Field is contenteditable. Use `browser_evaluate` or `browser_run_code` with `page.keyboard.type()`. |
| "TrustedHTML assignment" | Gmail blocks `innerHTML`. Use `textContent` or `page.keyboard.type()` instead. |
| Snapshot too shallow | Increase `depth` parameter (try 5–8). |
| Refs are stale | Re-snapshot after any click/navigation that changes the page. |

---

## 2. AppleScript (fallback — URL navigation + basic control)

Controls the real Chrome app natively on macOS. No extension needed. Best for opening URLs, reading page title/URL, and basic window management.

### What it can do

```bash
# Navigate to URL
osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "https://example.com"'

# Get current page info
osascript -e 'tell application "Google Chrome" to return title of active tab of front window'
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'

# Open new tab
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"https://example.com"}'

# Activate Chrome
osascript -e 'tell application "Google Chrome" to activate'
```

### What it cannot do

- Click page elements
- Fill form fields
- Execute JavaScript (blocked by default; requires manual toggle in Chrome menu: View → Developer → Allow JavaScript from Apple Events)
- Send keyboard events to web content reliably

### When to use AppleScript over Playwright MCP

- Quick URL navigation when MCP is not set up
- Reading the current tab's title/URL
- Opening Chrome or switching to it
- Combining with Gmail compose URLs for simple email tasks

---

## 3. Agent rules

1. **Default to Playwright MCP Bridge** (`user-chrome`). It can do everything.
2. **Always snapshot before interacting.** Refs go stale after page changes.
3. **For contenteditable fields** (Gmail body, rich text editors): use `browser_run_code` with `page.keyboard.type()`, not `browser_type`.
4. **For hidden inputs** (Gmail To field): use `browser_evaluate` to set value via JS.
5. **Increase snapshot depth** if the target element isn't visible (default is too shallow for Gmail).
6. **Fall back to AppleScript** only for URL navigation or when MCP is unavailable.
7. **Gmail compose URL shortcut**: `https://mail.google.com/mail/?view=cm&fs=1&to=X&su=Y&body=Z` pre-fills everything without element hunting.
