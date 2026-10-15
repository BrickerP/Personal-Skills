---
name: obsidian
description: General Obsidian vault editing and automation for .md, .canvas, and common plugin formats (Dataview/DB Folder). Use when asked to update Obsidian notes, properties/frontmatter, canvases, or database-style views/queries.
---

# Obsidian

## Overview

Create or update Obsidian content across notes, canvases, and database-style views. Use references for exact specs (JSON Canvas, Dataview, Properties, DB Folder). Ask when plugin availability or desired behavior is unclear.

## Workflow

- Identify scope: note (.md), canvas (.canvas), or database-style view (Dataview/DB Folder).
- Resolve paths: use provided file path or `obsidian://open` URL; otherwise ask for vault + file.
- Apply edits: preserve existing formatting, frontmatter, and IDs; minimize unrelated changes.
- Validate structure: YAML frontmatter for properties, JSON Canvas for canvases, and query blocks for Dataview.

## Defaults and heuristics

- Default vault path (this machine): `/Users/yupeng/Documents/Obsidian Vault`.
- If the user provides an `obsidian://open` URL, parse `vault` and `file` params and map to the vault path (URL-decode). Prefer the decoded `file` value as the target note/canvas.
- For canvases, use a consistent grid (40-80 px) and align nodes to reduce visual drift.
- For canvases, place group nodes earlier in the `nodes` array so they render behind contained nodes.
- For canvases, omit `fromSide`/`toSide` unless the user specifies connection sides.
- For canvases, if no sizes are provided, start with: text 280x200, file 480x320, link 360x200, group 640x400.
- For properties, prefer YAML frontmatter; respect existing property order and types.
- For Dataview queries, use fenced blocks (` ```dataview `) and avoid mutating note content unless requested.

## Notes and rules

- If the user says “database”, clarify whether they mean Properties, Dataview queries, or DB Folder tables.
- If a plugin is required (Dataview/DB Folder) and not confirmed, ask before assuming it exists.
- When updating Markdown, preserve existing headings, links, and callouts unless explicitly asked to refactor.

## References

- Read `references/jsoncanvas-spec.md` for the schema, allowed values, and minimal examples.
- For Obsidian “database” concepts (Dataview, Properties, DB Folder), read `references/obsidian-database.md`.
