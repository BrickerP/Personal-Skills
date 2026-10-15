# Obsidian "Database" Concepts (summary)

This skill treats "database" as three related layers:

1) **Properties (core Obsidian)**: structured metadata stored as YAML frontmatter at the top of a note. Properties have a name, value, and type; supported types include text, list, number, checkbox, date, date & time, and tags. Once a property type is assigned to a name, that name uses the same type across the vault. Properties are stored as YAML at the top of the file (`---` block), and each name must be unique within a note. Obsidian does not support nested properties, bulk-editing properties in core UI, or Markdown in properties.

2) **Dataview (community plugin)**: a live index and query engine over the vault. It indexes metadata from YAML frontmatter and inline fields like `[key:: value]`, plus implicit data such as tags and lists/tasks. Dataview is for **displaying/calculating**, not editing notes (except checking tasks). Query options include DQL, inline queries, and JavaScript queries.

3) **DB Folder (community plugin)**: a Notion-like table UI powered by Dataview. It requires Dataview, lets you view notes in a table and edit fields directly without opening the note, and can create databases in three ways: command palette, sidebar icon, or folder context menu. It also supports opening the database as a markdown note via `open as markdown` and has both global and per-database settings (database settings take priority).

## Practical guidance for automation

- If a user says "database" in Obsidian, clarify whether they mean Properties, Dataview queries, or DB Folder tables.
- When generating data views, prefer Dataview queries (DQL or JS) rather than mutating note content.
- When generating or editing metadata, write YAML frontmatter properties (respecting types) or inline fields, depending on user preference.
