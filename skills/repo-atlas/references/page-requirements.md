# Page requirements

Generate `index.html` from a template plus `atlas.json` with a script (Python or Node, standard library only). Keep the template, the script and `atlas.json` in `OUT/src/`.

- One HTML file: CSS, JS and data inline. No external resources (no CDN, web fonts or remote images), no npm dependency; it must open offline.
- First screen: only the map and the learning path. The map is SVG: one row per band, nodes laid out in order within the band, orthogonal polyline edges, edge labels always visible (not only on hover). The trunk is drawn thick, numbered badges mark learning stops, and a star marks the node most worth the reader's time (`meta.star`).
- Layout: map on the left, a side panel on the right with two lenses: the learning path (click a stop to highlight its nodes; progress is kept in `localStorage`) and the flows (click a flow to highlight its edges and nodes and step through it).
- Clicking a node opens a drawer: role, entry points (copyable), facts with tags, upstream and downstream edges, history line, related risks.
- A "library" group of tabs holds: history overview, risk board, couplings, docs vs code, release gap, self-test, coverage and not-read.
- Evidence links are GitHub permalinks pinned to `meta.ref`: `/blob/<ref>/<path>#L<a>-L<b>`, `/commit/<hash>`, `/pull/<n>`, `/releases/tag/<tag>`. Quote at most 10 lines of code per snippet and never copy whole files.
- Search (open with `/`), light and dark theme, no horizontal overflow at 390px width. Nodes and stops are keyboard-operable and carry `aria-label`; evidence tags show text, not only color.
- Every number on the page (node count, event count, reference count) is computed from `atlas.json`.
