#!/usr/bin/env python3
"""Emit a one-off Chrome JS file that pastes MESSAGE into the Live Chat textarea and clicks Send.

Usage:
  python3 scripts/emit_chat_reply_js.py "Your answer…"
  echo "Your answer…" | python3 scripts/emit_chat_reply_js.py

Then run chrome_eval_opentrain.sh on the printed path.
"""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> None:
    if len(sys.argv) < 2 and sys.stdin.isatty():
        print(
            "usage: emit_chat_reply_js.py MESSAGE…  (or pipe message on stdin)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    msg = (
        " ".join(sys.argv[1:]).strip()
        if len(sys.argv) > 1
        else sys.stdin.read().strip()
    )
    if not msg:
        print("empty message", file=sys.stderr)
        raise SystemExit(2)
    out = pathlib.Path("/tmp/opentrain_chat_reply_exec.js")
    dumped = json.dumps(msg, ensure_ascii=False)
    out.write_text(
        f"""(() => {{
  const text = {dumped};
  const ta = document.querySelector("textarea");
  if (!ta) return "no_textarea";
  ta.focus();
  const desc = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value");
  if (desc && desc.set) desc.set.call(ta, text);
  else ta.value = text;
  ta.dispatchEvent(new InputEvent("input", {{ bubbles: true, data: text }}));
  const sendBtn = Array.from(document.querySelectorAll("button")).find(
    (b) => (b.textContent || "").trim() === "Send"
  );
  if (!sendBtn) return "no_send";
  sendBtn.click();
  return "sent";
}})();
""",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
