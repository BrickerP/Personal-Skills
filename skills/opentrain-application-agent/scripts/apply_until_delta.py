#!/usr/bin/env python3
"""Run mass_apply in a loop until All Proposals grows by TARGET (default 10).

Uses a process lock so only one long run controls Chrome at a time.
Emits a compact final report (baseline vs final) for the operator to paste back.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time

ROOT = "/Users/yupeng/.codex/skills/opentrain-application-agent/scripts"
EVAL = f"{ROOT}/chrome_eval.sh"
MASS = f"{ROOT}/mass_apply.py"
SNIP = f"{ROOT}/snippets/proposals_stats.js"
TMP_NAV = "/tmp/opentrain_nav_target.py.js"
PROPOSALS = "https://app.opentrain.ai/ai-trainer?q=proposals"
LOCK_PATH = "/tmp/opentrain_apply_until.lock"
REPORT_PATH = "/tmp/opentrain_apply_until_last_report.json"

_lock_fp = None


def _acquire_lock() -> None:
    global _lock_fp
    _lock_fp = open(LOCK_PATH, "w", encoding="utf-8")
    try:
        fcntl.flock(_lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(
            "err: another apply_until_delta is already running (lock "
            f"{LOCK_PATH}). Do not start a second copy; tail the existing log or stop the other PID."
        )
    _lock_fp.write(str(os.getpid()))
    _lock_fp.flush()


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
    env["CHROME_EVAL_CONCEAL"] = "0"
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
    with open(TMP_NAV, "w", encoding="utf-8") as f:
        f.write(f"(() => {{ location.assign({json.dumps(url)}); return 'ok'; }})();\n")
    run_js(window, tab, TMP_NAV)
    time.sleep(4)


def read_proposals_stats() -> dict:
    """Snapshot proposals page; retry a few times if All Proposals not parsed."""
    last_err: str | None = None
    for attempt in range(5):
        try:
            win, tab = resolve()
            nav(win, tab, PROPOSALS)
            raw = run_js(win, tab, SNIP)
            data = json.loads(raw)
            if data.get("allProposals") is not None:
                return data
            last_err = "allProposals null (wrong tab or UI changed)"
        except Exception as e:
            last_err = str(e)
        time.sleep(2.0 + attempt * 0.8)
    raise RuntimeError(last_err or "could not read proposals stats")


def _print_report(
    *,
    target: int,
    baseline: dict,
    final: dict | None,
    rounds: int,
    ok: bool,
    detail: str,
) -> None:
    def grab(d: dict | None, key: str) -> str:
        if not d:
            return "?"
        v = d.get(key)
        return str(v) if v is not None else "?"

    b_all = baseline.get("allProposals")
    f_all = (final or {}).get("allProposals")
    delta = None
    if isinstance(b_all, int) and isinstance(f_all, int):
        delta = f_all - b_all

    report = {
        "ok": ok,
        "target_delta": target,
        "baseline": {
            "allProposals": b_all,
            "pending": baseline.get("pending"),
            "rejects": baseline.get("rejects"),
            "applications": baseline.get("applications"),
            "url": baseline.get("url"),
        },
        "final": (
            {
                "allProposals": final.get("allProposals"),
                "pending": final.get("pending"),
                "rejects": final.get("rejects"),
                "applications": final.get("applications"),
                "url": final.get("url"),
            }
            if final
            else None
        ),
        "delta_all_proposals": delta,
        "rounds_ran": rounds,
        "detail": detail,
    }
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2, ensure_ascii=False)
    except OSError:
        pass

    print("=== OpenTrain batch report ===", flush=True)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    print(
        f"summary: all_proposals {grab(baseline, 'allProposals')} -> {grab(final, 'allProposals')} "
        f"(delta {delta if delta is not None else '?'})  target_+{target}  rounds={rounds}  "
        f"{'OK' if ok else 'INCOMPLETE'}",
        flush=True,
    )


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    max_rounds = int(os.environ.get("OPENTRAIN_MAX_ROUNDS", "120"))

    _acquire_lock()
    try:
        baseline = read_proposals_stats()
        b0 = baseline.get("allProposals")
        if b0 is None:
            _print_report(
                target=target,
                baseline=baseline,
                final=None,
                rounds=0,
                ok=False,
                detail="baseline allProposals unreadable",
            )
            raise SystemExit(1)
        print(f"start={b0} need_+{target}", flush=True)

        env = {**os.environ, "CHROME_EVAL_CONCEAL": "0", "PYTHONUNBUFFERED": "1"}
        final: dict | None = None
        rnd = 0
        for rnd in range(1, max_rounds + 1):
            subprocess.run(
                [
                    sys.executable,
                    "-u",
                    MASS,
                    "--auto-target",
                    "--max",
                    "45",
                    "--scrolls",
                    "60",
                ],
                env=env,
            )
            time.sleep(22)
            try:
                cur = read_proposals_stats()
            except Exception as e:
                print(f"round={rnd} stats_err={e}", flush=True)
                continue
            c0 = cur.get("allProposals")
            if isinstance(b0, int) and isinstance(c0, int):
                print(f"round={rnd} all_proposals={c0} delta={c0 - b0}", flush=True)
            else:
                print(f"round={rnd} stats_missing numeric baseline/cur", flush=True)
            if isinstance(c0, int) and c0 >= b0 + target:
                final = cur
                _print_report(
                    target=target,
                    baseline=baseline,
                    final=final,
                    rounds=rnd,
                    ok=True,
                    detail=f"reached +{target} on allProposals",
                )
                return
            final = cur

        _print_report(
            target=target,
            baseline=baseline,
            final=final,
            rounds=max_rounds,
            ok=False,
            detail=f"stopped after {max_rounds} rounds without +{target}",
        )
        raise SystemExit(2)
    finally:
        try:
            if _lock_fp:
                fcntl.flock(_lock_fp.fileno(), fcntl.LOCK_UN)
                _lock_fp.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
