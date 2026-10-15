# Astryx frontend reference

Companion to [SKILL.md](SKILL.md). Read when building a page or debugging props.

## Package map

| Package | Role |
|---------|------|
| `@astryxdesign/core` | Components, Theme, tokens CSS |
| `@astryxdesign/theme-neutral` | Default theme (`/theme.css`, `/built`) |
| `@astryxdesign/cli` | Docs, templates, swizzle, doctor |
| `@astryxdesign/theme-*` | butter, chocolate, gothic, matcha, stone, y2k |

## CSS layers (order matters)

1. `reset.css` → `@layer reset`
2. `astryx.css` → `@layer astryx-base`
3. `theme.css` → `@layer astryx-theme`

Tailwind (optional): see core README — import `tailwind-theme.css` bridge and declare layer order.

## Theme provider

```tsx
import { Theme } from '@astryxdesign/core/theme'
import { neutralTheme } from '@astryxdesign/theme-neutral/built'

<Theme theme={neutralTheme}>{children}</Theme>
```

## Chat agent message model

Use a small discriminated union; keep tool calls on assistant messages:

```ts
type ChatItem =
  | { id: string; kind: 'system'; text: string; variant?: 'divider' }
  | {
      id: string
      kind: 'message'
      role: 'user' | 'assistant'
      text: string
      time: string
      toolCalls?: Array<{
        name: string
        status?: 'pending' | 'running' | 'complete' | 'error'
        target?: string
        duration?: string
        resultDetail?: React.ReactNode
      }>
    }
```

### Render map

| Item | Components |
|------|------------|
| system divider | `ChatSystemMessage variant="divider"` |
| user | `ChatMessage sender="user"` → `ChatMessageBubble` + `ChatMessageMetadata` |
| assistant | `ChatMessage sender="assistant" avatar name` → optional `ChatToolCalls` → `ChatMessageBubble variant="ghost"` → `Markdown` |
| thinking | `ChatToolCalls` with `status: 'running'` + muted `Text` |

### ChatLayout shell

```tsx
<ChatLayout
  density="balanced"
  emptyState={<EmptyState title="…" description="…" actions={…} />}
  composer={
    <ChatComposer
      value={draft}
      onChange={setDraft}
      onSubmit={handleSubmit}
      isStopShown={isThinking}
      onStop={() => setIsThinking(false)}
      placeholder="Message…"
    />
  }
>
  <ChatMessageList>{/* messages */}</ChatMessageList>
</ChatLayout>
```

## AppShell + SideNav skeleton

```tsx
<AppShell
  height="fill"
  contentPadding={0}
  variant="elevated"
  sideNav={
    <SideNav
      header={
        <SideNavHeading
          heading="Studio"
          subheading="Chat agents"
          icon={<Avatar name="App" size="small" />}
        />
      }
      topContent={<Button label="New chat" variant="primary" size="md" onClick={…} />}
      footer={<Text size="sm" color="secondary">…</Text>}
    >
      <SideNavSection title="Recent">
        <SideNavItem label="…" isSelected onClick={…} />
      </SideNavSection>
    </SideNav>
  }
>
  {/* main column: header + ChatLayout */}
</AppShell>
```

## Icons

Built-in semantic names include: `close`, `chevronDown`, `menu`, `moreHorizontal`, `search`, `copy`, `stop`, `microphone`, …

```tsx
import { Icon } from '@astryxdesign/core/Icon'
import { IconButton } from '@astryxdesign/core/IconButton'

<IconButton label="More" icon={<Icon icon="moreHorizontal" />} variant="ghost" size="sm" />
```

Themes may register Lucide icons; for demos, semantic `Icon` names are enough.

## CLI cheat sheet

```bash
npx astryx --help
npx astryx init
npx astryx component Button
npx astryx docs theme
npx astryx docs tokens
npx astryx template --list
npx astryx template dashboard
npx astryx swizzle Button
npx astryx doctor
```

## Reference demo paths

```
~/Downloads/astryx-chat-demo/
  src/index.css      # CSS imports
  src/App.tsx        # AppShell + Chat agent
  package.json       # core + theme-neutral + cli
```

Run:

```bash
cd ~/Downloads/astryx-chat-demo && npm run dev -- --host 127.0.0.1
```
