#!/usr/bin/env python3
"""
Bulk-apply on OpenTrain in the user's real Chrome (AppleScript + JS snippets).

Requires Chrome: View → Developer → Allow JavaScript from Apple Events.

Flow is fixed (navigate, phases, structural clicks, bid from published range).
Content is not: Live Chat and multiple-choice steps block on Agent handoff files.

Only stdout lines:  PositionTitle | ProcessSummary | Status

Usage:
  python3 scripts/mass_apply.py --auto-target
  python3 scripts/mass_apply.py --window 1745054511 --tab 10
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import re
from datetime import datetime
from pathlib import Path

ROOT = "/Users/yupeng/.codex/skills/opentrain-application-agent/scripts"
EVAL = f"{ROOT}/chrome_eval.sh"
TMP_NAV = "/tmp/opentrain_nav.js"
AUTOMATION = f"{ROOT}/automation"
STATE = f"{AUTOMATION}/state.js"
SCROLL = f"{ROOT}/scroll_find_job.js"
FIND_JOB_FILTERS = f"{ROOT}/snippets/find_job_apply_filters.js"

# Pre-flight title skips (see references/reject-and-decline-log.md)
_SKIP_TITLE_RES = [
    re.compile(r"digital content data collection", re.I),
    re.compile(r"digital content collection", re.I),
    re.compile(r"voice actor", re.I),
    re.compile(r"\bVO\b", re.I),
    re.compile(r"native fluency required", re.I),
    re.compile(r"accent recognition", re.I),
    re.compile(r"\(PhD Required\)", re.I),
    re.compile(r"PhD required", re.I),
    re.compile(r"\bIndia\b", re.I),
    re.compile(r"Indian nationality", re.I),
]


def should_skip_job(title: str, card_text: str = "") -> str | None:
    blob = f"{title} {card_text}"
    for rx in _SKIP_TITLE_RES:
        if rx.search(blob):
            return rx.pattern
    return None


def _agent_handoff_timeout() -> float:
    return float(
        os.environ.get(
            "OPENTRAIN_AGENT_HANDOFF_TIMEOUT_SEC",
            os.environ.get("OPENTRAIN_CHAT_TIMEOUT_SEC", "900"),
        )
    )


def _wait_for_text_file(path: Path, deadline: float) -> str:
    while time.time() < deadline:
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            try:
                path.unlink()
            except OSError:
                pass
            return text
        time.sleep(1.5)
    return ""


def _emit_js_and_run(
    window: str,
    tab: str,
    argv: list[str],
    log: list[str],
    log_prefix: str,
    *,
    stdin_text: str | None = None,
) -> tuple[bool, str]:
    er = subprocess.run(
        [sys.executable, *argv],
        input=stdin_text.encode("utf-8") if stdin_text is not None else None,
        capture_output=True,
        timeout=30,
    )
    if er.returncode != 0:
        err = (er.stderr or er.stdout or b"").decode(errors="replace").strip()
        log.append(f"  {log_prefix}_emit {err[:200]}")
        return False, "emit_failed"
    js_path = (er.stdout or b"").decode().strip().splitlines()[-1] if er.stdout else ""
    if not js_path or not Path(js_path).is_file():
        return False, "emit_empty"
    try:
        out = run_js(window, tab, js_path)
    except Exception as e:
        return False, f"run_err {e}"
    log.append(f"  {log_prefix} {out[:160]}")
    return True, out


def resolve_chrome_target(auto: bool, window: str | None, tab: str | None) -> tuple[str, str]:
    if auto:
        pref_w = (os.environ.get("OPENTRAIN_CHROME_WINDOW_ID") or "").strip()
        cmd = (
            [f"{ROOT}/chrome_resolve_opentrain_in_window.sh", pref_w]
            if pref_w
            else [f"{ROOT}/chrome_resolve_opentrain.sh"]
        )
        out = subprocess.check_output(
            cmd,
            text=True,
            timeout=60,
        ).strip()
        parts = out.split()
        if len(parts) != 2:
            raise RuntimeError(f"unexpected resolve output: {out!r}")
        return parts[0], parts[1]
    if window and tab:
        return window, tab
    raise RuntimeError("pass --auto-target or both --window and --tab")


def run_js(window: str, tab: str, path: str) -> str:
    env = os.environ.copy()
    env["CHROME_EVAL_URL_MUST_CONTAIN"] = "app.opentrain.ai"
    env["CHROME_EVAL_CONCEAL"] = os.environ.get("CHROME_EVAL_CONCEAL", "offscreen")
    last_msg = ""
    for attempt in range(5):
        r = subprocess.run(
            [EVAL, window, path, tab],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip()
            last_msg = msg or f"exit {r.returncode}"
            if "Allow JavaScript from Apple Events" in msg or "AppleScript" in msg:
                raise RuntimeError(
                    "Chrome blocked AppleScript JS. Enable: View → Developer → "
                    "Allow JavaScript from Apple Events.\n"
                    + msg
                )
            time.sleep(1.0 + attempt * 0.5)
            continue
        out = (r.stdout or "").strip()
        if out:
            return out
        last_msg = "empty stdout from chrome_eval"
        time.sleep(1.0 + attempt * 0.5)
    raise RuntimeError(last_msg or "chrome_eval failed after retries")


def nav(window: str, tab: str, url: str) -> None:
    with open(TMP_NAV, "w", encoding="utf-8") as f:
        f.write(f"(() => {{ location.assign({json.dumps(url)}); return 'ok'; }})();\n")
    run_js(window, tab, TMP_NAV)


def load_jobs(window: str, tab: str, scroll_rounds: int) -> list[tuple[str, str]]:
    print(f"OpenTrain | find-job | loading list (scrolls={scroll_rounds})", flush=True)
    nav(window, tab, "https://app.opentrain.ai/find-job")
    time.sleep(6)
    try:
        filt = run_js(window, tab, FIND_JOB_FILTERS)
        print(f"OpenTrain | find-job | filters={filt[:200]}", flush=True)
    except Exception as e:
        print(f"OpenTrain | find-job | filters_err={e}", flush=True)
    time.sleep(2)
    for _ in range(scroll_rounds):
        run_js(window, tab, SCROLL)
        time.sleep(1.2)
    raw = run_js(window, tab, f"{ROOT}/snippets/extract_jobs.js")
    data = json.loads(raw)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for c in data.get("cards", []):
        u = c.get("href")
        title = (c.get("title") or "").replace("|", " ").strip()
        text = (c.get("text") or "").replace("|", " ")
        if not u or u in seen:
            continue
        skip = should_skip_job(title or "", text)
        if skip:
            continue
        seen.add(u)
        out.append((u, title or u))
    print(f"OpenTrain | find-job | job_cards={len(out)}", flush=True)
    return out


def handle_job(
    window: str,
    tab: str,
    url: str,
    title: str,
    log: list[str],
    max_steps: int = 160,
) -> tuple[str, str]:
    trace: list[str] = []
    nav(window, tab, url)
    time.sleep(6)
    for step in range(max_steps):
        st = json.loads(run_js(window, tab, STATE))
        ph = st.get("phase") or "?"
        trace.append(str(ph))
        if len(trace) > 24:
            trace = trace[-24:]
        log.append(f"  {step} {ph} {url}")
        proc = "→".join(trace[-10:])

        if ph == "not_job":
            if step < 4:
                nav(window, tab, url)
                time.sleep(8)
                continue
            return proc, "nav_fail"
        if ph == "closed":
            return proc, "closed"
        if ph == "geo_ineligible":
            return proc, "geo_ineligible"
        if ph == "proposal_dialog":
            out = run_js(window, tab, f"{AUTOMATION}/click_dialog_start_live_chat.js")
            log.append(f"  dialog_start_chat {out}")
            if out == "no_dialog_start_chat":
                out = run_js(window, tab, f"{AUTOMATION}/click_dialog_submit_proposal.js")
                log.append(f"  dialog_submit {out}")
            if out in ("no_dialog_start_chat", "no_dialog_submit"):
                dismiss = run_js(window, tab, f"{AUTOMATION}/click_dialog_dismiss.js")
                log.append(f"  dialog_dismiss {dismiss}")
                if dismiss == "ok":
                    time.sleep(2)
                    run_js(window, tab, f"{AUTOMATION}/click_submit_a_proposal.js")
                st2 = json.loads(run_js(window, tab, STATE))
                ph2 = st2.get("phase") or ""
                if ph2 == "geo_ineligible":
                    return proc, "geo_ineligible"
            time.sleep(4)
            tailj = trace[-12:]
            if len(tailj) >= 8 and all(x == "proposal_dialog" for x in tailj):
                return "→".join(trace), "stuck_proposal_dialog"
            continue
        if ph == "already_applied":
            return proc, "already_applied"
        if ph == "pending_review":
            return proc, "pending_review"
        if ph == "proposal_blocked":
            return proc, "blocked_no_proposal_cta"
        if ph == "resume_confirm":
            run_js(window, tab, f"{AUTOMATION}/click_continue_process.js")
            time.sleep(3)
            continue
        if ph == "chat_start":
            run_js(window, tab, f"{AUTOMATION}/click_start_live_chat.js")
            time.sleep(4)
            continue
        if ph == "chat_done":
            lb = (st.get("lastBot") or "").lower()
            if re.search(
                r"not able to continue|cannot continue|end the interview here|"
                r"requires a candidate based in india|not the right fit",
                lb,
            ):
                run_js(window, tab, f"{AUTOMATION}/click_dialog_dismiss.js")
                return proc, "chat_disqualified"
            run_js(window, tab, f"{AUTOMATION}/click_next_step.js")
            time.sleep(4)
            continue
        if ph == "chat_options":
            try:
                raw = run_js(window, tab, f"{ROOT}/snippets/chat_mc_options.js")
                opts = json.loads(raw)
            except Exception as e:
                log.append(f"  mc_options_err {e}")
                return "→".join(trace), "mc_options_err"
            labels = opts.get("labels") or []
            handoff_p = Path("/tmp/opentrain_mc_handoff.json")
            reply_p = Path("/tmp/opentrain_agent_mc_reply.txt")
            payload = {
                "kind": "opentrain_agent_mc",
                "url": url,
                "title": title,
                "lastBot": (st.get("lastBot") or "")[:8000],
                "buttonLabels": labels,
            }
            handoff_p.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            opt_preview = labels[:12]
            print(
                f"OpenTrain | AGENT_MC_WAITING | reply_file={reply_p} | n={len(labels)} | sample={opt_preview}",
                flush=True,
            )
            text = _wait_for_text_file(
                reply_p, time.time() + _agent_handoff_timeout()
            )
            if not text:
                log.append("  agent_mc_timeout")
                try:
                    handoff_p.unlink(missing_ok=True)
                except OSError:
                    pass
                return "→".join(trace), "agent_mc_timeout"
            ok, _msg = _emit_js_and_run(
                window,
                tab,
                [f"{ROOT}/emit_button_click_js.py", text],
                log,
                "agent_mc_click",
            )
            try:
                handoff_p.unlink(missing_ok=True)
            except OSError:
                pass
            if not ok:
                return "→".join(trace), "agent_mc_click_failed"
            time.sleep(3)
            continue
        if ph == "chat":
            handoff_p = Path("/tmp/opentrain_chat_handoff.json")
            reply_p = Path("/tmp/opentrain_chat_agent_reply.txt")
            payload = {
                "kind": "opentrain_agent_chat",
                "url": url,
                "title": title,
                "lastBot": (st.get("lastBot") or "")[:8000],
                "phase": ph,
            }
            handoff_p.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            lb_preview = ((st.get("lastBot") or "")[:120]).replace("\n", " ")
            print(
                f"OpenTrain | AGENT_CHAT_WAITING | reply_file={reply_p} | q={lb_preview}",
                flush=True,
            )
            text = _wait_for_text_file(
                reply_p, time.time() + _agent_handoff_timeout()
            )
            if not text:
                log.append("  agent_chat_timeout")
                try:
                    handoff_p.unlink(missing_ok=True)
                except OSError:
                    pass
                return "→".join(trace), "agent_chat_timeout"
            ok, _msg = _emit_js_and_run(
                window,
                tab,
                [f"{ROOT}/emit_chat_reply_js.py"],
                log,
                "agent_chat",
                stdin_text=text + "\n",
            )
            try:
                handoff_p.unlink(missing_ok=True)
            except OSError:
                pass
            if not ok:
                return "→".join(trace), "agent_chat_failed"
            time.sleep(7)
            continue
        if ph == "job_detail":
            out = run_js(window, tab, f"{AUTOMATION}/click_submit_a_proposal.js")
            log.append(f"  submit_click {out}")
            if out == "no_submit_a_proposal":
                run_js(window, tab, f"{AUTOMATION}/click_next_step.js")
            time.sleep(4)
            tailj = trace[-18:]
            if len(tailj) >= 10 and all(x == "job_detail" for x in tailj):
                return "→".join(trace), "stuck_job_detail"
            continue
        if ph in ("proposal", "proposal_click_submit_only"):
            raw = run_js(window, tab, f"{AUTOMATION}/fill_max_bid_submit.js")
            log.append("  bid " + raw)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            if not payload.get("ok"):
                reason = str(payload.get("reason") or "").strip() or "unknown"
                return "→".join(trace), f"skipped_bid_{reason}"
            if payload.get("ok") and payload.get("submit"):
                time.sleep(4)
                summary = run_js(
                    window,
                    tab,
                    f"{ROOT}/snippets/page_summary.js",
                )
                if re.search(r"submitted|success|thank you", summary or "", re.I):
                    return "→".join(trace), "submitted"
                return "→".join(trace), "proposal_clicked_verify"
            if payload.get("ok") and not payload.get("submit"):
                run_js(window, tab, f"{AUTOMATION}/click_submit_a_proposal.js")
                time.sleep(2)
                continue
            time.sleep(2)
            continue
        if ph == "unknown":
            head = (st.get("head") or "").strip()
            if step >= 12:
                return "→".join(trace), "unknown_timeout"
            if len(head) < 90 and step < 20:
                time.sleep(3)
                continue
            run_js(window, tab, f"{AUTOMATION}/click_next_step.js")
            time.sleep(2)
            continue
        time.sleep(2)

    return "→".join(trace), "timeout"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--auto-target",
        action="store_true",
        help="Use first Chrome tab whose URL contains app.opentrain.ai",
    )
    ap.add_argument("--window", default=None)
    ap.add_argument("--tab", default=None)
    ap.add_argument("--max", type=int, default=0, help="max jobs (0=all allowed)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scrolls", type=int, default=4)
    args = ap.parse_args()

    try:
        win, tab = resolve_chrome_target(args.auto_target, args.window, args.tab)
    except Exception as e:
        print(f"OpenTrain | resolve_target | err {e}", flush=True)
        raise SystemExit(1)

    log_path = "/tmp/opentrain_mass_apply_log.txt"

    def flush_log(lines: list[str]) -> None:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    try:
        jobs = load_jobs(win, tab, args.scrolls)
    except Exception as e:
        print(f"OpenTrain | load_jobs | err {e}", flush=True)
        raise SystemExit(1)
    if args.max:
        jobs = jobs[: args.max]

    if args.dry_run:
        for url, title in jobs:
            print(f"{title} | dry-run | queued {url}", flush=True)
        return

    log_lines: list[str] = [datetime.now().isoformat(), f"queued_jobs={len(jobs)}"]
    flush_log(log_lines)

    for url, title in jobs:
        log_lines.append(url)
        flush_log(log_lines)
        skip_pat = should_skip_job(title)
        if skip_pat:
            safe_title = title.replace("|", " ")
            print(f"{safe_title} | skip_preflight | {skip_pat}", flush=True)
            continue
        if args.auto_target:
            try:
                win, tab = resolve_chrome_target(True, None, None)
            except Exception as e:
                print(f"OpenTrain | re-resolve | err {e}", flush=True)
                proc, status = "error", f"err resolve {e}"
                flush_log(log_lines)
                safe_title = title.replace("|", " ")
                print(f"{safe_title} | error | {status}", flush=True)
                continue
        try:
            proc, status = handle_job(win, tab, url, title, log_lines)
        except Exception as e:
            proc, status = "error", f"err {e}"
        flush_log(log_lines)
        safe_title = title.replace("|", " ")
        print(f"{safe_title} | {proc} | {status}", flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()
