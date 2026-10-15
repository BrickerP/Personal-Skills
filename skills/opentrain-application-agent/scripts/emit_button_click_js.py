#!/usr/bin/env python3
"""Emit JS that clicks the first visible button/[role=button] with exact trimmed text."""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: emit_button_click_js.py 'Exact Button Label'", file=sys.stderr)
        raise SystemExit(2)
    label = " ".join(sys.argv[1:]).strip()
    if not label:
        raise SystemExit(2)
    out = pathlib.Path("/tmp/opentrain_button_click_exec.js")
    dumped = json.dumps(label, ensure_ascii=False)
    out.write_text(
        f"""(() => {{
  const want = {dumped};
  const nodes = [...document.querySelectorAll("button, [role='button']")];
  const vis = nodes.filter((x) => {{
    const r = x.getBoundingClientRect();
    return r.height > 2 && r.width > 2;
  }});
  const b = vis.find((x) => (x.textContent || "").trim() === want);
  if (!b) return "no_btn";
  b.click();
  return "clicked";
}})();
""",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
