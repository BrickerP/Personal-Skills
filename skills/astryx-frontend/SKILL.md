---
name: astryx-frontend
description: >-
  Scaffold and ship local React frontend demos with Meta's Astryx design system
  (Vite + React + TS, @astryxdesign/core, themes, CLI). Use when the user asks
  to build a local UI, frontend demo, chat agent page, Astryx prototype, or
  wants a unified format for subsequent local frontend builds.
---

# Astryx local frontend

Unified pipeline for **local frontend demos** using Astryx. Prefer this over inventing a new stack each time.

Reference demo: `/Users/yupeng/Downloads/astryx-chat-demo`  
Docs: https://astryx.atmeta.com · Repo: https://github.com/facebook/astryx

## When to use

- User wants a **local UI / demo page** (chat agent, dashboard, form, settings, etc.)
- User mentions **Astryx**, `@astryxdesign`, or “用开源 UI 库”
- User wants a **repeatable frontend scaffold** for later builds

## Defaults (do not renegotiate unless asked)

| Choice | Default |
|--------|---------|
| Stack | Vite + React 19 + TypeScript |
| UI | `@astryxdesign/core` + `@astryxdesign/theme-neutral` |
| CLI | `@astryxdesign/cli` (devDependency) |
| Location | New folder under `~/Downloads/<slug>/` if current workspace is not a frontend app |
| Theme | `neutral` first; swap theme package only if user asks |
| Backend | Mock / canned responses unless user asks for real API |
| Goal | Runnable `npm run dev` URL the user can open |

Do **not** bolt a React app into an unrelated Python/backend repo (e.g. quant-trading). Create a sibling project, then `move_agent_to_root` if needed.

## Checklist

```
Progress:
- [ ] 1. Project root decided / created
- [ ] 2. Vite React-TS scaffold + Astryx packages
- [ ] 3. CSS + Theme provider wired
- [ ] 4. Page built with Astryx primitives (subpath imports)
- [ ] 5. `npm run build` passes
- [ ] 6. Dev server up; give user the Local URL
```

## Step 1 — Project root

If workspace is already a Vite/React app → stay.

Otherwise:

```bash
# via Cursor MCP create_project when available, else:
mkdir -p ~/Downloads/<slug> && cd ~/Downloads/<slug>
```

Then move the agent root to that path before editing.

## Step 2 — Scaffold + install

```bash
npm create vite@latest . -- --template react-ts
npm install @astryxdesign/core @astryxdesign/theme-neutral
npm install -D @astryxdesign/cli
```

Optional `package.json` script for reliable CLI (esp. for agents):

```json
"scripts": {
  "astryx": "node node_modules/@astryxdesign/cli/bin/astryx.mjs"
}
```

## Step 3 — Wire CSS + Theme (required order)

**`src/index.css`** — import order is load-bearing:

```css
@import '@astryxdesign/core/reset.css';
@import '@astryxdesign/core/astryx.css';
@import '@astryxdesign/theme-neutral/theme.css';

html, body, #root { height: 100%; margin: 0; }
body {
  background: var(--color-background-body);
  color: var(--color-text-primary);
  font-family: var(--font-family-body);
}
```

**App root** — wrap once:

```tsx
import { Theme } from '@astryxdesign/core/theme'
import { neutralTheme } from '@astryxdesign/theme-neutral/built'

export default function App() {
  return <Theme theme={neutralTheme}>{/* page */}</Theme>
}
```

Delete Vite boilerplate (`App.css` default styles, logo assets) so Astryx tokens own the look.

## Step 4 — Build UI with Astryx (not custom CSS)

### Import rules

- Use **subpath imports**: `@astryxdesign/core/Button`, `@astryxdesign/core/Chat`, …
- Prefer Astryx layout: `AppShell`, `SideNav*`, `HStack`/`VStack`, `Section`
- Prefer Astryx content: `Text`, `Heading`, `Badge`, `Button`, `EmptyState`, `Markdown`, `CodeBlock`
- Prefer Astryx chat: `ChatLayout`, `ChatMessageList`, `ChatMessage`, `ChatMessageBubble`, `ChatComposer`, `ChatToolCalls`, `ChatSystemMessage`
- Style with tokens / component props; avoid large custom CSS files

### Discover APIs before guessing

```bash
npx astryx component              # list
npx astryx component Chat         # family docs + examples
npx astryx component Button
npx astryx docs tokens
npx astryx template --list
# or:
node node_modules/@astryxdesign/core/docs.mjs Chat
```

When props are unclear, read `node_modules/@astryxdesign/core/dist/<Component>/<Component>.d.ts` — do not invent prop names.

### Common prop gotchas

| Wrong | Right |
|-------|-------|
| `SideNavHeading title/subtitle` | `heading` / `subheading` |
| `SideNavSection label=` | `title=` |
| `Text size="small"` | `size="sm"` (scale: `4xs`…`sm`…`4xl`) |
| `IconButton icon="moreHorizontal"` | `icon={<Icon icon="moreHorizontal" />}` |
| Bubble name+meta on wrapper when using bubbles | Put `name`/`metadata` on **bubble** (first/last) |

More patterns: [reference.md](reference.md)

## Step 5 — Verify

```bash
npm run build          # must pass (tsc + vite)
npm run dev -- --host 127.0.0.1 --port 5173
```

If the port is taken, use the URL Vite prints (e.g. `5175`). Tell the user the **exact Local URL**. Do not claim done without a successful build + running server (or an explicit reason it cannot run).

## Page recipes

### Chat agent (default when user says “chat / agent”)

Structure:

1. `AppShell` + `SideNav` (thread list, New chat)
2. Header row (title + badges)
3. `ChatLayout` with `composer={<ChatComposer …/>}` and `emptyState={<EmptyState …/>}`
4. `ChatMessageList` → system dividers / user bubbles / assistant ghost bubbles
5. Assistant messages: optional `ChatToolCalls` + `Markdown` body
6. Mock `onSubmit` → append user message → short delay → canned assistant reply (+ fake tools)

See [reference.md](reference.md) for the message-model shape used in the reference demo.

### Other pages

- Forms / settings → `AppShell` + `Section` + Field/Input components
- Tables / inventory → Astryx `Table` + toolbar
- Start from `npx astryx template <name>` when a template fits

## Done criteria

- [ ] Astryx CSS + Theme wired
- [ ] UI composed from Astryx components (not a custom CSS redesign)
- [ ] `npm run build` OK
- [ ] Dev URL shared with user
- [ ] Mock vs real backend stated in one line

## Out of scope

- Production deploy / CI unless asked
- Rewriting existing design systems to Astryx unless asked
- Adding StyleX build plugins for demos (prebuilt CSS path is enough)
