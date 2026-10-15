#!/usr/bin/env python3
"""Navigate to OpenTrain proposals page and print pending/rejects/applications as N/M/K."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ROOT = "/Users/yupeng/.codex/skills/opentrain-application-agent/scripts"
EVAL = f"{ROOT}/chrome_eval.sh"
PROPOSALS = "https://app.opentrain.ai/ai-trainer?q=proposals"
SNIP = f"{ROOT}/snippets/proposals_stats.js"
NAV = "/tmp/opentrain_nav_proposals.js"


def resolve() -> tuple[str, str]:
    out = subprocess.check_output(
        [f"{ROOT}/chrome_resolve_opentrain.sh"],
        text=True,
        timeout=60,
    ).strip()
    w, tab = out.split()
    return w, tab


def run_js(window: str, tab: str, path: str) -> str:
    env = os.environ.copy()
    env["CHROME_EVAL_URL_MUST_CONTAIN"] = "app.opentrain.ai"
    env["CHROME_EVAL_CONCEAL"] = os.environ.get("CHROME_EVAL_CONCEAL", "offscreen")
    r = subprocess.run(
        [EVAL, window, path, tab],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip())
    return (r.stdout or "").strip()


def nav(window: str, tab: str, url: str) -> None:
    with open(NAV, "w", encoding="utf-8") as f:
        f.write(f"(() => {{ location.assign({json.dumps(url)}); return 'ok'; }})();\n")
    run_js(window, tab, NAV)
    time.sleep(4)


def main() -> None:
    w, tab = resolve()
    nav(w, tab, PROPOSALS)
    raw = run_js(w, tab, SNIP)
    data = json.loads(raw)
    p = int(data.get("pending") or 0)
    r = int(data.get("rejects") or 0)
    k = int(data.get("applications") or 0)
    print(f"{p}/{r}/{k}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"err {e}", file=sys.stderr)
        sys.exit(1)
