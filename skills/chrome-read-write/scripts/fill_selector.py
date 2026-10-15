#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Fill a Chrome page element by CSS selector.")
    parser.add_argument("target_id")
    parser.add_argument("selector")
    parser.add_argument("text")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_eval = os.path.join(script_dir, "chrome_eval.sh")
    js = f"""
(() => {{
  const selector = {json.dumps(args.selector)};
  const value = {json.dumps(args.text)};
  const el = document.querySelector(selector);
  if (!el) throw new Error("No element for selector: " + selector);
  el.focus();
  if (el.isContentEditable) {{
    el.textContent = value;
  }} else {{
    el.value = value;
  }}
  el.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: value }}));
  el.dispatchEvent(new Event("change", {{ bubbles: true }}));
  if ({str(args.submit).lower()}) {{
    const form = el.closest("form");
    if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
  }}
  return JSON.stringify({{
    ok: true,
    url: location.href,
    selector,
    tag: el.tagName.toLowerCase(),
    value: (el.value || el.textContent || "").slice(0, 500)
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
