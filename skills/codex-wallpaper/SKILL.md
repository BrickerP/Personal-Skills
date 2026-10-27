---
name: codex-wallpaper
description: Safely list, inspect, preview, import, and switch Codex Dream Skin wallpaper themes on macOS through the exact supported upstream engine.
metadata:
  opencode/autoinvoke: false
---

# Codex Wallpaper

Use `scripts/codex-wallpaper.zsh`; do not reconstruct Dream Skin commands manually.

## Dependency

This companion does not vendor Dream Skin. It requires the external engine at
`~/.codex/codex-dream-skin-studio` and supports exactly engine version `1.5.20`.
`list` and `status` remain read-only when the engine is missing or unsupported;
all mutations fail closed. With a supported engine and safe CDP port, `status`
performs a fresh read-only verification and shows saved versus live theme IDs and
revisions. It distinguishes payload mismatch, DOM structure failure, hidden DOM
documents, and unavailable native-window verification. A hidden DOM document
does not prove the native window is hidden.

## Commands

```zsh
scripts/codex-wallpaper.zsh list
scripts/codex-wallpaper.zsh status
scripts/codex-wallpaper.zsh gallery
scripts/codex-wallpaper.zsh apply '<exact-name-or-id>'
scripts/codex-wallpaper.zsh restart-apply '<exact-name-or-id>' --yes
scripts/codex-wallpaper.zsh import '/absolute/image/path' 'theme name'
scripts/codex-wallpaper.zsh import-zip '/absolute/package.zip'
scripts/codex-wallpaper.zsh import-zip '/absolute/package.zip' --expected-sha256 '<sha256>' --expected-bytes '<bytes>'
```

Names must match exactly. Duplicate names require an ID. `import` saves without
applying. `apply` hot-applies once and never restarts. `restart-apply` requires
explicit consent, uses TERM only, and reports its detached one-shot result in
`status` plus a macOS notification.

`gallery` opens the full community catalog by default, with a separate local
installed tab, whole-catalog search, load-more and show-all controls. Community
metadata is cached; thumbnails load lazily through fixed official endpoints.
The community count is distinct from the installed count. A full cached catalog
can be browsed offline; an explicit refresh updates it. Partial refreshes do not
replace a complete cache. Do not claim every package is locally installed.
A community card installs only when the user clicks its install button, checks
the published size and SHA-256, then calls this wrapper's `import-zip` command.
It saves without applying; use the local tab to select and apply. Unsupported
platforms or incompatible packages remain visible with installation disabled.
`import-zip` delegates to the supported engine's package validator and importer,
preserves theme styles, and saves without applying. For community downloads,
pass the published SHA-256 and byte count together. Packages with an existing
theme ID are rejected before import; identical packs with another ID are
deduplicated by the engine. Do not upgrade the engine to import a pack that
requires a newer version.

## Safety Contract

- Never create watchers, launchd jobs, KeepAlive tasks, retry daemons, or other persistence.
- Never bypass the `--yes` restart gate or the one-time private worker nonce.
- Treat a non-loopback, unrelated, or unverifiable listener on port 9341 as a hard failure.
- Verify the exact theme ID and revision after applying.
- Do not print secrets, command traces, or absolute theme image paths.
