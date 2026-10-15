#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Click a visible Chrome page control by label text.")
    parser.add_argument("target_id")
    parser.add_argument("label")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_eval = os.path.join(script_dir, "chrome_eval.sh")
    js = f"""
(() => {{
  const wanted = {json.dumps(args.label)};
  const norm = (s) => String(s || "").replace(/\\s+/g, " ").trim();
  const visible = (el) => {{
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  }};
  const labelOf = (el) => norm(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || el.title);
  const candidates = Array.from(document.querySelectorAll("button,[role='button'],a,input[type='button'],input[type='submit']"))
    .filter(visible);
  const exact = candidates.find((el) => labelOf(el) === wanted);
  const partial = exact || candidates.find((el) => labelOf(el).includes(wanted));
  if (!partial) throw new Error("No visible clickable control with label: " + wanted);
  partial.click();
  return JSON.stringify({{
    ok: true,
    url: location.href,
    clicked: labelOf(partial),
    tag: partial.tagName.toLowerCase()
  }});
}})();
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(js)
        js_path = handle.name
    try:
        subprocess.run([chrome_eval, args.target_id, js_path], check=True)
    finally:
        try:
            os.unlink(js_path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
