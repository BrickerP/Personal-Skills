# OpenTrain Playbook

## Exact Browser Mechanism

Use **`execute active tab of window id …`** only. Do not use **`execute active tab of front window`** (wrong window when multiple Chrome windows are open).

Optional: `CHROME_EVAL_URL_MUST_CONTAIN=app.opentrain.ai` / `scripts/chrome_eval_opentrain.sh` refuses to run JS if the tab is not OpenTrain.

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of window id 1745054511 javascript "document.title"'
```

This only works after Chrome has:

`View -> Developer -> Allow JavaScript from Apple Events`

The script is running in the selected Chrome tab, not in a headless browser. That is why it can use the user's logged-in OpenTrain/Gmail profile.

## Stable Tab Workflow

List candidate tabs:

```bash
/Users/yupeng/.codex/skills/opentrain-application-agent/scripts/chrome_tabs.sh app.opentrain.ai
```

Select the exact tab:

```bash
/Users/yupeng/.codex/skills/opentrain-application-agent/scripts/select_tab.sh 1745054511 10
```

Evaluate a page script:

```bash
/Users/yupeng/.codex/skills/opentrain-application-agent/scripts/chrome_eval.sh 1745054511 /Users/yupeng/.codex/skills/opentrain-application-agent/scripts/snippets/page_summary.js 10
```

## Page Scripts

Use `scripts/snippets/page_summary.js` to verify current URL/title/body.

Use `scripts/snippets/profile_form_state.js` to inspect visible inputs, textareas, selects, and buttons.

Use `scripts/snippets/extract_jobs.js` on `/find-job` to extract first-page job cards.

If the focused window or URL does not match expectations, re-run `chrome_tabs.sh` and re-select the tab.

Pin automation to one Chrome window when multiple windows have `app.opentrain.ai` tabs (avoids the wrong “active” tab being chosen):

**This machine (Yupeng):** use the **first** browser window — `1745054511` (confirmed).

```bash
# Pinned OpenTrain window (first Chrome window on this Mac)
export OPENTRAIN_CHROME_WINDOW_ID=1745054511
python3 /Users/yupeng/.codex/skills/opentrain-application-agent/scripts/apply_until_delta.py 5
```

Underlying helper: `scripts/chrome_resolve_opentrain_in_window.sh <window_id>`.

**Note:** Agents should not use Cursor’s embedded preview browser to “check” OpenTrain; it is a separate session without your Google login. Inspect pay/proposal UI only in real Chrome (manual) or via `chrome_eval.sh` … `page_summary.js` / `profile_form_state.js` on the logged-in tab.

## Known OpenTrain Notes From This Session

- Public profile URL: `https://app.opentrain.ai/labeler-profile/lu-y`
- Profile edit/review URL: `https://app.opentrain.ai/labeler-onboarding`
- Jobs URL: `https://app.opentrain.ai/find-job`
- Good first-page matches:
  - `Computer Science Expert (Python Required)` at `/job-detail/cmnlrhux4005304k12ve7tn2v`
  - `Data Science Expert (Python, SQL, GenAI)` at `/job-detail/cmnlpih5w000104jl0bmi7fdv`
  - `Machine Learning Expert (Python, GenAI, SQL)` at `/job-detail/cmnlowid7000z04i5dl35cqto`
