# atlas.json

The single source of data for the page. The page script reads it; nothing is typed into the HTML by hand. Tag values are `code | history | docs | inferred`; the page shows them in LANG (for zh-CN: 代码 / 历史 / 文档 / 推断).

```json
{
  "meta": {"repo": "owner/name", "ref": "full sha", "ref_date": "YYYY-MM-DD", "default_branch": "", "type": "library|service|cli|app|framework|monorepo", "license": "", "scope": "whole repo|subdir", "audience": "", "trunk": "one-line trunk scenario", "star": "node id", "generated": "YYYY-MM-DD"},
  "bands": [{"id": "", "name": "", "note": ""}],
  "nodes": [{"id": "", "name": "", "role": "one line", "band": "", "kind": "point|resource", "paths": [""], "entry": ["path:symbol"], "facts": [{"t": "", "tag": "code|history|docs|inferred", "ref": ""}]}],
  "edges": [{"from": "", "to": "", "label": "", "level": "trunk|primary|secondary", "bidir": false, "ref": "path:line"}],
  "flows": [{"id": "A", "name": "", "hint": "", "steps": [{"title": "", "edge": "from>to", "detail": "", "tag": "", "ref": ""}]}],
  "stops": [{"n": 1, "name": "", "goal": "", "read": [{"path": "", "why": ""}], "ask": [""], "verify": [""], "nodes": [""], "minutes": 60}],
  "events": [{"node": "", "date": "YYYY-MM-DD", "text": "", "ref": "hash | #PR | tag", "kind": "add|change|fix|remove|release"}],
  "risks": [{"id": "R1", "title": "", "group": "security|stability|performance|release|debt", "nodes": [""], "body": "", "evidence": [{"tag": "", "ref": ""}], "action": "", "confidence": "high|medium|low"}],
  "couplings": [{"name": "", "parts": [""], "failure": "", "tag": ""}],
  "docs_vs_code": [{"doc": "path#anchor", "claim": "", "reality": "", "ref": ""}],
  "selftest": [{"q": "", "a": "", "ref": ""}],
  "release_gap": {"latest": "", "date": "", "ahead": 0, "ref": ""},
  "coverage": {"read": [{"path": "", "depth": "full|skim"}], "commits_scanned": 0, "prs_read": 0, "not_read": [{"what": "", "why": ""}], "unverified": [""]}
}
```

## Limits

- bands 2-4; nodes at most 20; events at most 8 per node
- stops 8-10; flows 3-5 with at most 10 steps each; risks at most 15; selftest 8-12

## Notes

- `nodes[].kind`: `point` is a node you explored; `resource` is an external system or another repo you only show.
- `edges[].level`: `trunk` edges form the main scenario; they are drawn thick and define which nodes sit on the trunk.
- `flows[].steps[].edge` uses the `from>to` form of an existing edge; prefix `!` for the same edge travelled backwards.
- `meta.star` is the node that is most worth the reader's time; it gets the star on the map.
- Optional `machines` array: see `lifecycle-layer.md`.
