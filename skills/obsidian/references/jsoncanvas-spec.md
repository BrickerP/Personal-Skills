# JSON Canvas Spec (v1.0)

Version 1.0 — 2024-03-11

## Top-level object

- `nodes`: optional array of node objects
- `edges`: optional array of edge objects
- Node order defines z-index (first is bottom-most)

## Common node fields

- `id` (string, required)
- `type` (string, required): `text` | `file` | `link` | `group`
- `x`, `y`, `width`, `height` (integer, required)
- `color` (optional canvasColor)

## Node types

### text
- `text` (string, required) - Markdown-compatible text

### file
- `file` (string, required) - path to the file within the system
- `subpath` (string, optional) - starts with `#` for heading or block

### link
- `url` (string, required)

### group
- `label` (string, optional)
- `background` (string, optional) - background image path
- `backgroundStyle` (string, optional): `cover` | `ratio` | `repeat`

## Edges

- `id` (string, required)
- `fromNode` (string, required)
- `toNode` (string, required)
- `fromSide` (optional): `top` | `right` | `bottom` | `left`
- `toSide` (optional): `top` | `right` | `bottom` | `left`
- `fromEnd` (optional): `none` | `arrow` (default `none`)
- `toEnd` (optional): `none` | `arrow` (default `arrow`)
- `color` (optional canvasColor)
- `label` (optional string)

## canvasColor

- Hex string, e.g. `#FF0000`
- Preset strings `"1"`-`"6"` (red, orange, yellow, green, cyan, purple)
- Exact values are app-defined

## Minimal example

```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 280,
      "height": 200,
      "text": "Hello"
    }
  ],
  "edges": []
}
```
