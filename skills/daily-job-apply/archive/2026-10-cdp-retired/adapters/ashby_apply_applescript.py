#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    SCRIPTS_DIR,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    LEDGER_PATH,
    PDF_DIR,
    resume_pdf,
)

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))

import argparse
import base64
import csv
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


HOME = Path.home()
TRACKER = TRACKER_CSV
LEDGER = LEDGER_PATH
SKILL = SKILL_ROOT
CDP_DEPS = HOME / ".codex" / "skills" / "chrome-read-write" / "scripts" / ".cdp-deps" / "node_modules"
APP_DIR = Path("/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent")
RESUME_1P = APP_DIR / "Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf"
RESUME_2P = APP_DIR / "Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf"
RESUMES = {
    "AI Agent Infra": RESUME_1P,
    "Backend Platform": RESUME_1P,
    "General SWE": RESUME_1P,
}
CDP_HOST = os.environ.get("CHROME_CDP_HOST", "127.0.0.1")
CDP_PORT = os.environ.get("CHROME_CDP_PORT", "9222")
APPLICATION_PHONE = os.environ.get("JOB_APPLY_PHONE", "")
PROFILE_PATH = SKILL / "data" / "profile.json"
PROFILE: dict = json.loads(PROFILE_PATH.read_text(encoding="utf-8")) if PROFILE_PATH.exists() else {}
PROFILE_BASICS = PROFILE.get("basics") or {}
PROFILE_LINKEDIN = str(PROFILE_BASICS.get("linkedin") or "https://www.linkedin.com/in/yupeng-lu-845a0b411/")
PROFILE_GITHUB = str((PROFILE_BASICS.get("github") or ["https://github.com/BrickerP"])[0])
PROFILE_GITHUB_USERNAME = "BrickerP"
_github_match = re.search(r"github\.com/([^/?#]+)", PROFILE_GITHUB)
if _github_match:
    PROFILE_GITHUB_USERNAME = _github_match.group(1)
PROFILE_LOCATION = str(PROFILE_BASICS.get("location") or "San Francisco Bay Area")
PROFILE_COUNTRY = str(
    PROFILE_BASICS.get("country")
    or PROFILE_BASICS.get("country_of_residence")
    or PROFILE_BASICS.get("passport_country")
    or ((PROFILE.get("positioning") or {}).get("target_geo") or ["United States"])[-1]
    or "United States"
)
PROFILE_WORK_AUTH = str(
    PROFILE_BASICS.get("work_authorization")
    or "US Permanent Resident — No sponsorship required, now or in the future"
)
PROFILE_SUMMARY = str(PROFILE.get("summary") or "")
PROFILE_COMPANY = str((PROFILE.get("positioning") or {}).get("current_company_public_label") or "VC-backed Voice AI Platform Startup")
PROFILE_EMPLOYER = str(
    (PROFILE.get("positioning") or {}).get("current_employer_ats")
    or (PROFILE.get("positioning") or {}).get("current_company_public_label")
    or "VC-backed Voice AI Platform Startup"
)
_experience = PROFILE.get("experience") or []
PROFILE_TITLE = str(
    (_experience[0].get("title") if _experience else None)
    or (PROFILE.get("positioning") or {}).get("current_title_public_label")
    or "AI Agent Engineer"
)
PROFILE_FULL_NAME = str(PROFILE_BASICS.get("name") or "Yupeng Lu")
_name_tokens = PROFILE_FULL_NAME.split()
PROFILE_FIRST_NAME = _name_tokens[0] if _name_tokens else "Yupeng"
PROFILE_LAST_NAME = " ".join(_name_tokens[1:]) if len(_name_tokens) > 1 else (_name_tokens[-1] if _name_tokens else "Lu")
_SESSION: dict[str, str | None] = {"app_target_id": None, "gmail_target_id": None}
BOOLEAN_MATCH_JS = """
  const matchesChoice = (text, wanted) => {
    const t = clean(text);
    const w = clean(wanted);
    if (!t || !w) return false;
    if (t === w) return true;
    if (t.startsWith(w + ' ') || t.startsWith(w + ' -') || t.startsWith(w + '-') || t.startsWith(w + ',')) return true;
    const wLower = w.toLowerCase();
    const tLower = t.toLowerCase();
    if (wLower === 'no' && /^no\\b[\\s,\\-–—]/i.test(t)) return true;
    if (wLower === 'yes' && /^yes\\b[\\s,\\-–—]/i.test(t)) return true;
    if (wLower === 'no' && /^(no[,\\s\\-–—]|no - i do not|no, i have not|no i have not|no — i)/i.test(t)) return true;
    if (wLower === 'yes' && /^(yes[,\\s\\-–—]|yes - i|yes, i)/i.test(t)) return true;
    const firstWord = (tLower.split(/[\\s,\\-–—]/)[0] || '').trim();
    if (firstWord === wLower) return true;
    return false;
  };
  const findChoiceButton = (entry, wanted) => {
    if (!entry) return null;
    return [...entry.querySelectorAll('button')].find((btn) =>
      matchesChoice(btn.innerText || btn.getAttribute('aria-label') || '', wanted)
    ) || null;
  };
  const labelForInput = (input) => {
    if (!input) return '';
    let linked = null;
    try { linked = input.id ? document.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null; } catch (_) {}
    return clean((input.closest('label') || linked || input.parentElement || {}).innerText || input.value || input.getAttribute('aria-label') || '');
  };
  const findChoiceTarget = (entry, wantedVal) => {
    if (!entry) return null;
    const btn = findChoiceButton(entry, wantedVal);
    if (btn) return btn;
    for (const input of entry.querySelectorAll('input[type=radio],input[type=checkbox]')) {
      const label = labelForInput(input);
      if (matchesChoice(label, wantedVal) || matchesChoice(input.value || '', wantedVal)) return input;
    }
    for (const label of entry.querySelectorAll('label')) {
      if (matchesChoice(label.innerText || '', wantedVal)) return label;
    }
    for (const radio of entry.querySelectorAll('[role=radio],[role=button],[role=option]')) {
      if (matchesChoice(radio.innerText || radio.getAttribute('aria-label') || '', wantedVal)) return radio;
    }
    for (const node of entry.querySelectorAll('button,label,span,div')) {
      const nodeText = clean(node.innerText || node.getAttribute('aria-label') || node.textContent || '');
      if (!matchesChoice(nodeText, wantedVal)) continue;
      const clickable = node.closest('button,label,[role=radio],[role=button]') || node;
      if (clickable) return clickable;
    }
    return null;
  };
  const fieldEntries = () => [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id], fieldset, [class*="FieldEntry"], [class*="fieldEntry"]')];
  const findChoiceControl = (entry, wanted) => findChoiceTarget(entry, wanted);
  const fireCommit = (el) => {
    if (!el) return;
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: el.value || '' }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
  };
  const commitBooleanEntry = (entry, wanted) => {
    if (!entry) return { ok: false, code: 'entry-missing' };
    const wantedLower = clean(wanted).toLowerCase();
    const btn = findChoiceTarget(entry, wanted);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      if (btn instanceof HTMLInputElement && (btn.type === 'radio' || btn.type === 'checkbox')) {
        btn.checked = true;
        const checkedSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked')?.set;
        if (checkedSetter) checkedSetter.call(btn, true);
      } else {
        btn.click();
      }
      btn.setAttribute('aria-checked', 'true');
      btn.setAttribute('aria-pressed', 'true');
      btn.setAttribute('data-state', 'checked');
      for (const sibling of entry.querySelectorAll('button,[role=radio],[role=button],input[type=radio],input[type=checkbox]')) {
        if (sibling === btn) continue;
        sibling.removeAttribute('aria-checked');
        sibling.removeAttribute('data-state');
        sibling.setAttribute('aria-pressed', 'false');
        if (sibling instanceof HTMLInputElement && (sibling.type === 'radio' || sibling.type === 'checkbox')) sibling.checked = false;
      }
    }
    const hiddenInputs = [...entry.querySelectorAll('input[type=hidden],input[type=radio],input[type=checkbox]')];
    for (const input of hiddenInputs) {
      const label = clean((input.closest('label') || input.parentElement || {}).innerText || input.value || '');
      const match = matchesChoice(label, wanted) || matchesChoice(input.value || '', wanted);
      if (match || (wantedLower === 'no' && /^no/i.test(label)) || (wantedLower === 'yes' && /^yes/i.test(label))) {
        if (input.type === 'radio' || input.type === 'checkbox') input.checked = true;
        fireCommit(input);
      }
    }
    const selected = entry.querySelector('[aria-checked=true],[aria-selected=true],[data-selected=true],button[aria-pressed=true]');
    if (selected) fireCommit(selected);
    return { ok: true };
  };
  const resolveBooleanWanted = (question) => {
    const q = clean(question);
    if (!q) return '';
    if (/background check|performs background checks|does not permit use of ai agents during live interviews/i.test(q)) return 'Yes';
    if (/related to any current.*employees|related to any.*employee/i.test(q)) return 'No';
    if (/compensation range.*align with your expectations|does this align with your expectations/i.test(q)) return 'Yes';
    if (/require all employees onsite|onsite.*full-time|in-person.*full-time|accommodate an onsite|work from the office|willing to work onsite|office in sf or nyc/i.test(q)) return 'Yes';
    if (/over the age of 18|at least 18 years/i.test(q)) return 'Yes';
    if (/u\\.s\\. person|legally requires.*u\\.s\\. person|confirm whether you fall into one of the three statuses/i.test(q)) return 'Yes';
    if (/located in or prefer to work in canada|prefer to work in canada/i.test(q)) return 'No';
    if (/export administration regulations|\\bear\\b|export compliance assessment|subject to the u\\.s\\. ear/i.test(q)) return 'No';
    if (/authorized to work|legally authorized|eligible to work/i.test(q) && !/what is your work authorization/i.test(q)) return 'Yes';
    return '';
  };
  const sponsorshipQuestionRx = /will you now or in the future require sponsorship|require sponsorship for employment visa|sponsorship for employment visa|require sponsorship.*visa status/i;
  const authQuestionRx = /authorized to work|legally authorized|eligible to work|work authorization|authorization to work/i;
  const citizenshipOptionRx = /u\\.s\\. citizen|u\\.s\\. permanent resident|canadian citizen|canadian permanent resident/i;
  const statusStyleOptionRx = /\\b(citizen|visa holder|permanent resident)\\b/i;
  const statusStyleChoices = [
    'Permanent Resident', 'US Permanent Resident', 'U.S. Permanent Resident',
    'Permanent resident', 'Citizen', 'U.S. Citizen', 'US Citizen',
    'Canadian Permanent Resident', 'Canadian Citizen', 'Visa Holder', 'Other',
  ];
  const resolveAuthWanted = (entry, question) => {
    const q = clean(question);
    if (!q) return '';
    if (sponsorshipQuestionRx.test(q)) return 'No';
    if (!authQuestionRx.test(q)) return '';
    if (/legally authorized to work in the united states|authorized to work in the united states/i.test(q)) {
      return 'Yes';
    }
    const optionText = [...entry.querySelectorAll('button,label,[role=radio],[role=option]')].map((el) =>
      clean(el.innerText || el.value || el.getAttribute('aria-label') || '')
    ).join(' ');
    if (/what is your work authorization|work authorization status/i.test(q) || statusStyleOptionRx.test(optionText)) {
      for (const choice of statusStyleChoices) {
        if (findChoiceControl(entry, choice)) return choice;
      }
    }
    if (citizenshipOptionRx.test(optionText)) {
      for (const choice of statusStyleChoices) {
        if (findChoiceControl(entry, choice)) return choice;
      }
      if (findChoiceControl(entry, 'Yes')) return 'Yes';
      return 'Yes';
    }
    return 'Yes';
  };
  const authQuestionText = (entry) => {
    const heading = clean((entry.querySelector('label,legend,[class*="label"]') || {}).innerText || '');
    return clean(`${heading} ${entry.innerText || ''}`);
  };
"""


def resolve_resume(variant: str, pages: str) -> Path:
    if pages == "2":
        return RESUME_2P
    if pages == "1":
        return RESUME_1P
    return RESUMES[variant]


def sh(cmd: list[str], *, timeout: int = 30, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


def osa(script: str, *, timeout: int = 30) -> str:
    proc = sh(["osascript"], timeout=timeout, input_text=script)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def cdp_node_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CHROME_CDP_HOST"] = CDP_HOST
    env["CHROME_CDP_PORT"] = str(CDP_PORT)
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    return env


def chrome_debug_available() -> bool:
    try:
        with urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json/version", timeout=3) as response:
            return bool(response.read())
    except Exception:
        return False


def cdp_list_pages() -> list[dict]:
    with urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=5) as response:
        return [target for target in json.loads(response.read().decode("utf-8")) if target.get("type") == "page"]


def cdp_run_node(script: str, args: list[str], *, timeout: int = 45) -> dict:
    proc = subprocess.run(
        ["node", "-e", script, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=cdp_node_env(),
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-node-failed", "stderr": proc.stderr.strip()[:800]}
    raw = (proc.stdout or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-node-bad-json", "stdout": raw[:500]}


def cdp_ensure_yplmicro_window() -> dict:
    script = r"""
const CDP = require('chrome-remote-interface');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
(async () => {
  const pages = (await CDP.List({ host, port })).filter((t) => t.type === 'page');
  const gmail = pages.find((t) => t.url.includes('mail.google.com') && t.title.includes('yplmicro@gmail.com'));
  if (!gmail) {
    process.stdout.write(JSON.stringify({ ok: false, code: 'yplmicro-gmail-not-found' }));
    return;
  }
  const client = await CDP({ host, port });
  try {
    const gmailWindow = await client.Browser.getWindowForTarget({ targetId: gmail.id });
    for (const page of pages) {
      if (!page.title.includes('yupeng@cookiy.com')) continue;
      const otherWindow = await client.Browser.getWindowForTarget({ targetId: page.id });
      if (otherWindow.windowId === gmailWindow.windowId) {
        process.stdout.write(JSON.stringify({ ok: false, code: 'cookiy-gmail-in-window' }));
        return;
      }
    }
    process.stdout.write(JSON.stringify({ ok: true, gmail_target_id: gmail.id, window_id: gmailWindow.windowId }));
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    return cdp_run_node(script, [])


def cdp_open_application_tab(gmail_target_id: str, url: str) -> dict:
    script = r"""
const CDP = require('chrome-remote-interface');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const norm = (value) => String(value || '').replace(/[?#].*$/, '').replace(/\/$/, '').replace(/\/application$/, '');
(async () => {
  const gmailTargetId = process.argv[1];
  const rawUrl = process.argv[2];
  const base = norm(rawUrl);
  const appUrl = base + '/application';
  const pages = (await CDP.List({ host, port })).filter((t) => t.type === 'page');
  const existing = pages.find((t) => {
    const current = norm(t.url || '');
    return (current === base || current.startsWith(base)) && !String(t.url || '').includes('application-submitted');
  });
  if (existing) {
    const client = await CDP({ target: existing, host, port });
    try {
      await client.Page.navigate({ url: appUrl });
    } finally {
      await client.close();
    }
    process.stdout.write(JSON.stringify({ ok: true, target_id: existing.id }));
    return;
  }
  const gmail = pages.find((t) => t.id === gmailTargetId);
  if (!gmail) {
    process.stdout.write(JSON.stringify({ ok: false, code: 'gmail-target-not-found' }));
    return;
  }
  const gmailClient = await CDP({ target: gmail, host, port });
  try {
    const info = await gmailClient.Target.getTargetInfo({ targetId: gmailTargetId });
    const browserContextId = info.targetInfo.browserContextId;
    const created = await gmailClient.Target.createTarget({ url: appUrl, browserContextId, newWindow: false });
    process.stdout.write(JSON.stringify({ ok: true, target_id: created.targetId }));
  } finally {
    await gmailClient.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    return cdp_run_node(script, [gmail_target_id, url], timeout=60)


def cdp_close_target(target_id: str) -> dict:
    script = r"""
const CDP = require('chrome-remote-interface');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
(async () => {
  const targetId = process.argv[1];
  const client = await CDP({ host, port });
  try {
    await client.Target.closeTarget({ targetId });
    process.stdout.write(JSON.stringify({ ok: true, closed: true }));
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    return cdp_run_node(script, [target_id], timeout=20)


def cdp_js_eval(target_id: str, js: str, *, timeout: int = 30) -> dict:
    script = r"""
const CDP = require('chrome-remote-interface');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
(async () => {
  const targetId = process.argv[1];
  const expression = process.argv[2];
  const pages = (await CDP.List({ host, port })).filter((t) => t.type === 'page');
  const target = pages.find((t) => t.id === targetId);
  if (!target) {
    process.stdout.write(JSON.stringify({ ok: false, code: 'cdp-target-not-found' }));
    return;
  }
  const client = await CDP({ target, host, port });
  try {
    const result = await client.Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true });
    const value = result && result.result ? result.result.value : '';
    if (typeof value === 'string') {
      try {
        process.stdout.write(value);
        return;
      } catch (_) {}
    }
    process.stdout.write(JSON.stringify(value));
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    proc = subprocess.run(
        ["node", "-e", script, target_id, js],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=cdp_node_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip()[:500])
    out = (proc.stdout or "").strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non-json js result: {out[:500]}") from exc


def js_eval(js: str, *, window: int = 1, tab: int | None = None, timeout: int = 30) -> dict:
    target_id = _SESSION.get("app_target_id")
    if target_id and chrome_debug_available():
        return cdp_js_eval(target_id, js, timeout=timeout)
    window = resolve_yplmicro_window(window)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(js)
        js_path = handle.name
    try:
        target = f"tab {tab} of targetWindow" if tab else "active tab of targetWindow"
        script = f'''
set jsSource to read POSIX file {json.dumps(js_path)}
tell application "Google Chrome"
  set targetWindow to window {window}
  execute {target} javascript jsSource
end tell
'''
        out = osa(script, timeout=timeout)
    finally:
        try:
            os.unlink(js_path)
        except OSError:
            pass
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non-json js result: {out[:500]}") from exc


def now_cst() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")


def today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value)
    value = value.rstrip("/")
    value = re.sub(r"/application$", "", value)
    return value


def app_url(value: str) -> str:
    return norm_url(value) + "/application"


def ensure_window(window: int) -> dict:
    if chrome_debug_available():
        win = cdp_ensure_yplmicro_window()
        if win.get("ok"):
            _SESSION["gmail_target_id"] = win.get("gmail_target_id")
        return win
    script = f'''
tell application "Google Chrome"
  set gmailOk to false
  repeat with t from 1 to count of tabs of window {window}
    set ti to title of tab t of window {window}
    if ti contains "yplmicro@gmail.com" and ti contains "Inbox" then set gmailOk to true
    if ti contains "yupeng@cookiy.com" then return "{{\\"ok\\":false,\\"code\\":\\"cookiy-gmail-in-window\\"}}"
  end repeat
  if gmailOk then return "{{\\"ok\\":true}}"
  return "{{\\"ok\\":false,\\"code\\":\\"yplmicro-gmail-not-found\\"}}"
end tell
'''
    return json.loads(osa(script))


def find_yplmicro_window() -> int:
    script = r'''
tell application "Google Chrome"
  repeat with w from 1 to count of windows
    set gmailOk to false
    set cookiySeen to false
    repeat with t from 1 to count of tabs of window w
      set ti to title of tab t of window w
      if ti contains "yplmicro@gmail.com" and ti contains "Inbox" then set gmailOk to true
      if ti contains "yupeng@cookiy.com" then set cookiySeen to true
    end repeat
    if gmailOk and not cookiySeen then return w as text
  end repeat
end tell
return "0"
'''
    try:
        return int(osa(script))
    except (RuntimeError, ValueError):
        return 0


def resolve_yplmicro_window(window: int = 0) -> int:
    if window:
        try:
            if ensure_window(window).get("ok"):
                return window
        except Exception:
            pass
    found = find_yplmicro_window()
    return found or window


def open_application_tab(window: int, url: str) -> int:
    gmail_target_id = _SESSION.get("gmail_target_id")
    if gmail_target_id and chrome_debug_available():
        opened = cdp_open_application_tab(gmail_target_id, url)
        if not opened.get("ok"):
            raise RuntimeError(json.dumps(opened, ensure_ascii=False))
        _SESSION["app_target_id"] = opened.get("target_id")
        time.sleep(20)
        return 1
    window = resolve_yplmicro_window(window)
    base = norm_url(url)
    script = f'''
tell application "Google Chrome"
  set targetWindow to window {window}
  repeat with t from 1 to count of tabs of targetWindow
    set tabUrl to URL of tab t of targetWindow
    if tabUrl starts with {json.dumps(base)} and tabUrl does not contain "/application-submitted" then
      set URL of tab t of targetWindow to {json.dumps(app_url(url))}
      return t as text
    end if
  end repeat
  make new tab at end of tabs of targetWindow with properties {{URL:{json.dumps(app_url(url))}}}
  return (count of tabs of targetWindow) as text
end tell
'''
    tab = int(osa(script))
    time.sleep(20)
    return tab


def ashby_submit_button_gone(text: str) -> bool:
    return not re.search(r"submit application", text or "", re.I)


def ashby_inline_application_success(url: str, text: str) -> bool:
    """Skydio/WorkOS/Ashby boards: Success copy on /application after submit button disappears."""
    url_lower = (url or "").lower()
    page_text = text or ""
    on_application_page = (
        "/application" in url_lower
        and "/application-submitted" not in url_lower
        and "/application/success" not in url_lower
    )
    if not on_application_page or not ashby_submit_button_gone(page_text):
        return False
    if not re.search(
        r"thank you for submitting|thank you for your interest|thank you for your application|we received your application",
        page_text,
        re.I,
    ):
        return False
    return bool(
        re.search(
            r"application success|successfully submitted|"
            r"we(?:'|\u2019)?ll contact you if there are next steps|"
            r"we will be in touch|received your application|delighted that you would consider",
            page_text,
            re.I,
        )
    )


def ashby_submit_confirmed(url: str, title: str, text: str) -> bool:
    blob = f"{url} {title} {text}"
    if re.search(
        r"couldn'?t submit|could not submit|unable to submit|not submit your application|"
        r"already applied|duplicate application|we(?:'|\u2019)?ve received your application before",
        blob,
        re.I,
    ):
        return False
    url_lower = (url or "").lower()
    if "/application-submitted" in url_lower or "/application/success" in url_lower:
        return True
    if ashby_inline_application_success(url, text):
        return True
    on_application_page = "/application" in url_lower and "/application-submitted" not in url_lower
    if on_application_page:
        return bool(
            re.search(
                r"your application was successfully submitted|application was successfully submitted|"
                r"we(?:'|\u2019)?ll contact you if there are next steps|"
                r"thank you for your interest|we received your application|application success",
                blob,
                re.I,
            )
        )
    return bool(
        re.search(
            r"your application was successfully submitted|application was successfully submitted|"
            r"we(?:'|\u2019)?ll contact you if there are next steps|thank you for applying|"
            r"thank you for your application|we(?:'|\u2019)?ll contact you shortly",
            blob,
            re.I,
        )
    )


def close_success_tab(window: int, tab: int | None = None) -> dict:
    page = js_eval("JSON.stringify({url:location.href,title:document.title,text:(document.body&&document.body.innerText||'').slice(0,800)})", window=window, tab=tab, timeout=20)
    should_close = ashby_submit_confirmed(page.get("url") or "", page.get("title") or "", page.get("text") or "")
    if should_close:
        app_target_id = _SESSION.get("app_target_id")
        if app_target_id and chrome_debug_available():
            closed = cdp_close_target(app_target_id)
            _SESSION["app_target_id"] = None
            return {"ok": True, "closed": True, **page, **closed}
        window = resolve_yplmicro_window(window)
        target = f"tab {tab} of targetWindow" if tab else "active tab of targetWindow"
        osa(f'''
tell application "Google Chrome"
  set targetWindow to window {window}
  close {target}
end tell
''')
    return {"ok": True, "closed": bool(should_close), **page}


def close_tab(window: int, tab: int | None = None) -> dict:
    app_target_id = _SESSION.get("app_target_id")
    if app_target_id and chrome_debug_available():
        closed = cdp_close_target(app_target_id)
        _SESSION["app_target_id"] = None
        return closed
    window = resolve_yplmicro_window(window)
    target = f"tab {tab} of targetWindow" if tab else "active tab of targetWindow"
    osa(f'''
tell application "Google Chrome"
  set targetWindow to window {window}
  close {target}
end tell
''')
    return {"ok": True, "closed": True}


def cdp_target_for_url(url: str) -> str | None:
    if _SESSION.get("app_target_id"):
        return _SESSION["app_target_id"]
    base = norm_url(url)
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as response:
            targets = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    for target in targets:
        if target.get("type") != "page":
            continue
        target_url = norm_url(target.get("url", ""))
        if target_url == base or target_url.startswith(base):
            return target.get("id")
    return None


def cdp_click_points(url: str, points: list[dict]) -> dict:
    if not points:
        return {"ok": True, "clicked": 0}
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const points = JSON.parse(process.argv[2] || '[]');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime} = client;
    let count = 0;
    for (const point of points) {
      const x = Number(point.x);
      const y = Number(point.y);
      const res = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: `(() => {
          const el = document.elementFromPoint(${x}, ${y});
          if (!el) return { ok: false, code: 'click-target-not-found', x: ${x}, y: ${y} };
          const btn = el.closest('button,[role=button],label,input[type=radio],input[type=checkbox]') || el;
          btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
          btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
          btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          return { ok: true };
        })()`,
      });
      const value = res.result.value;
      if (!value || !value.ok) {
        process.stdout.write(JSON.stringify(value || { ok: false, code: 'click-eval-failed' }) + '\n');
        return;
      }
      count += 1;
      await sleep(250);
    }
    process.stdout.write(JSON.stringify({ ok: true, clicked: count }) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, json.dumps(points)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-click-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-click-bad-json", "stdout": proc.stdout[:500]}


def cdp_click_boolean_with_commit(url: str, point: dict) -> dict:
    """SCR-04h: radio label+setter+events first; SCR-04g button/radio CDP fallback."""
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    payload_obj = {
        "x": float(point.get("x") or 0),
        "y": float(point.get("y") or 0),
        "wanted": str(point.get("wanted") or ""),
        "index": point.get("index"),
        "question": str(point.get("question") or "")[:120],
    }
    question = payload_obj["question"]
    wanted = payload_obj["wanted"]
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const point = JSON.parse(process.argv[2] || '{}');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const browserCore = `
  const point = __POINT__;
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const matchesChoice = (text, w) => {
    const t = clean(text);
    const wanted = clean(w);
    if (!t || !wanted) return false;
    if (t === wanted) return true;
    if (t.startsWith(wanted + ' ') || t.startsWith(wanted + ' -') || t.startsWith(wanted + '-') || t.startsWith(wanted + ',')) return true;
    const wLower = wanted.toLowerCase();
    if (wLower === 'no' && /^no\\b[\\s,\\-]/i.test(t)) return true;
    if (wLower === 'yes' && /^yes\\b[\\s,\\-]/i.test(t)) return true;
    if (wLower === 'no' && /^(no[,\\s\\-]|no - i do not|no, i have not|no i have not|no - i)/i.test(t)) return true;
    if (wLower === 'yes' && /^(yes[,\\s\\-]|yes - i|yes, i)/i.test(t)) return true;
    return (t.toLowerCase().split(/[\\s,\\-]/)[0] || '').trim() === wLower;
  };
  const isChoicePressed = (el) => {
    if (!el) return false;
    const cls = (el.className || '').toString();
    return el.getAttribute('aria-checked') === 'true'
      || el.getAttribute('aria-selected') === 'true'
      || el.getAttribute('aria-pressed') === 'true'
      || el.getAttribute('data-state') === 'checked'
      || el.getAttribute('data-selected') === 'true'
      || el.classList.contains('selected')
      || el.classList.contains('active')
      || /(?:^|\\s)_active(?:_|\\s|$)/.test(cls);
  };
  const findChoiceButton = (entry, wantedVal) => {
    if (!entry) return null;
    const buttons = [...entry.querySelectorAll('button')].filter((btn) => {
      const text = clean(btn.innerText || btn.getAttribute('aria-label') || '');
      return matchesChoice(text, wantedVal);
    });
    return buttons[0] || null;
  };
  const labelForInput = (input) => {
    if (!input) return '';
    let linked = null;
    try { linked = input.id ? document.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null; } catch (_) {}
    return clean((input.closest('label') || linked || input.parentElement || {}).innerText || input.value || input.getAttribute('aria-label') || '');
  };
  const findRadioInput = (entry, wantedVal) => {
    if (!entry) return null;
    for (const input of entry.querySelectorAll('input[type=radio]')) {
      const label = labelForInput(input);
      if (matchesChoice(label, wantedVal) || matchesChoice(input.value || '', wantedVal)) return input;
    }
    return null;
  };
  const findChoiceTarget = (entry, wantedVal) => {
    if (!entry) return null;
    const btn = findChoiceButton(entry, wantedVal);
    if (btn) return btn;
    const radio = findRadioInput(entry, wantedVal);
    if (radio) return radio;
    for (const label of entry.querySelectorAll('label')) {
      if (matchesChoice(label.innerText || '', wantedVal)) return label;
    }
    for (const radioEl of entry.querySelectorAll('[role=radio]')) {
      if (matchesChoice(radioEl.innerText || radioEl.getAttribute('aria-label') || '', wantedVal)) return radioEl;
    }
    return null;
  };
  const fireCommit = (el) => {
    if (!el) return;
    if (el instanceof HTMLInputElement) {
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = true;
        const checkedDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
        const checkedSetter = checkedDesc && checkedDesc.set;
        if (checkedSetter) checkedSetter.call(el, true);
      } else {
        const valueDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        const setter = valueDesc && valueDesc.set;
        if (setter) setter.call(el, el.value);
      }
    }
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: el.value || '' }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
  };
  const resolveEntry = () => {
    const entries = [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')];
    const idx = point.index;
    if (idx != null && entries[idx]) return entries[idx];
    const el = document.elementFromPoint(point.x, point.y);
    return el ? el.closest('.ashby-application-form-field-entry, [data-field-entry-id]') : null;
  };
  const captureDomSnapshot = (entry) => {
    if (!entry) return { ok: false, code: 'snapshot-entry-missing' };
    const wantedVal = point.wanted;
    return {
      ok: true,
      entryId: entry.getAttribute('data-field-entry-id') || null,
      question: clean((entry.querySelector('label') || {}).innerText || entry.innerText || '').slice(0, 220),
      buttons: [...entry.querySelectorAll('button')].map((btn) => ({
        text: clean(btn.innerText || '').slice(0, 80),
        ariaChecked: btn.getAttribute('aria-checked'),
        dataState: btn.getAttribute('data-state'),
        className: (btn.className || '').toString().slice(0, 100),
      })),
      radios: [...entry.querySelectorAll('[role=radio]')].map((el) => ({
        text: clean(el.innerText || '').slice(0, 80),
        ariaChecked: el.getAttribute('aria-checked'),
      })),
      inputs: [...entry.querySelectorAll('input')].map((input) => ({
        type: input.type,
        name: input.name,
        value: input.value,
        checked: input.checked,
      })),
      html: entry.innerHTML.slice(0, 2500),
      wanted: wantedVal,
    };
  };
  const fieldEntryError = (entry) => {
    if (!entry) return false;
    const fieldErrorEl = entry.querySelector('.ashby-application-form-field-error, [class*="FieldError"], [data-testid*="error"], [role="alert"]');
    const probe = clean((fieldErrorEl || {}).innerText || '');
    if (probe) return /\\bthis field is required\\b|please select an option|please select one|missing entry for required field/i.test(probe);
    return false;
  };
  const verifyEntry = () => {
    try {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'verify-entry-not-found', committed: false };
    const wantedVal = point.wanted;
    const wantedLower = clean(wantedVal).toLowerCase();
    const isYesNo = wantedLower === 'yes' || wantedLower === 'no';
    const selectedBtn = [...entry.querySelectorAll('button,[role=radio]')].find((el) => {
      if (!el || typeof el.getAttribute !== 'function') return false;
      const text = clean(el.innerText || el.value || el.getAttribute('aria-label') || '');
      return isChoicePressed(el) && matchesChoice(text, wantedVal);
    });
    const checkedInput = [...entry.querySelectorAll('input[type=radio],input[type=checkbox]')].find((input) => {
      if (!input.checked) return false;
      const label = clean((input.closest('label') || input.parentElement || {}).innerText || input.value || '');
      const val = clean(input.value || '');
      if (isYesNo && /^on$/i.test(val) && !matchesChoice(label, wantedVal)) return false;
      return matchesChoice(label, wantedVal) || matchesChoice(val, wantedVal);
    });
    const entryError = fieldEntryError(entry);
    const committed = !!(selectedBtn || checkedInput) && !entryError;
    return { ok: committed, committed, hasSelected: !!(selectedBtn || checkedInput), entryError, selectedText: clean((selectedBtn || checkedInput || {}).innerText || (checkedInput || {}).value || '') };
    } catch (err) {
      return { ok: false, committed: false, code: 'verify-exception', error: String(err && err.message || err) };
    }
  };
  const commitHiddenInputs = () => {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'commit-entry-not-found' };
    const wantedVal = point.wanted;
    for (const input of entry.querySelectorAll('input[type=hidden],input[type=radio],input[type=checkbox]')) {
      const label = clean((input.closest('label') || input.parentElement || {}).innerText || input.value || '');
      if (matchesChoice(label, wantedVal) || matchesChoice(input.value || '', wantedVal)) {
        if (input.type === 'radio' || input.type === 'checkbox') {
          input.checked = true;
          const checkedDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
          const checkedSetter = checkedDesc && checkedDesc.set;
          if (checkedSetter) checkedSetter.call(input, true);
        } else {
          const valueDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
          const setter = valueDesc && valueDesc.set;
          if (setter) setter.call(input, input.value);
        }
        fireCommit(input);
      }
    }
    const selected = entry.querySelector('[aria-checked=true],[aria-selected=true],[data-selected=true],[data-state=checked]');
    if (selected) fireCommit(selected);
    return { ok: true };
  };
  const reactFiberKey = (el) => Object.keys(el || {}).find((k) => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  const reactPropsKey = (el) => Object.keys(el || {}).find((k) => k.startsWith('__reactProps'));
  const invokeReactChange = (el, patch) => {
    if (!el) return false;
    let invoked = false;
    const propsKey = reactPropsKey(el);
    const props = propsKey ? el[propsKey] : null;
    const synthetic = { target: el, currentTarget: el, bubbles: true, type: 'change' };
    if (props && typeof props.onChange === 'function') {
      props.onChange(synthetic);
      invoked = true;
    }
    if (props && typeof props.onClick === 'function') {
      props.onClick({ ...synthetic, type: 'click' });
      invoked = true;
    }
    let fiber = el[reactFiberKey(el)];
    for (let depth = 0; depth < 16 && fiber; depth += 1, fiber = fiber.return) {
      const fp = fiber.memoizedProps || fiber.pendingProps;
      if (fp && typeof fp.onChange === 'function') {
        fp.onChange(synthetic);
        invoked = true;
        break;
      }
      if (fp && typeof fp.onClick === 'function') {
        fp.onClick({ ...synthetic, type: 'click' });
        invoked = true;
        break;
      }
    }
    return invoked;
  };
  const commitReactFiberBoolean = () => {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'fiber-entry-not-found' };
    const wantedVal = point.wanted;
    let touched = 0;
    for (const input of entry.querySelectorAll('input[type=hidden],input[type=radio],input[type=checkbox],button,[role=radio]')) {
      const label = clean((input.closest('label') || input.parentElement || {}).innerText || input.value || input.getAttribute('aria-label') || '');
      if (!matchesChoice(label, wantedVal) && !matchesChoice(input.value || '', wantedVal)) continue;
      if (input instanceof HTMLInputElement) {
        if (input.type === 'radio' || input.type === 'checkbox') {
          input.checked = true;
          const checkedDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
          const checkedSetter = checkedDesc && checkedDesc.set;
          if (checkedSetter) checkedSetter.call(input, true);
        }
        invokeReactChange(input, { checked: true, value: input.value || wantedVal });
      } else {
        invokeReactChange(input, { checked: true, value: wantedVal });
      }
      fireCommit(input);
      touched += 1;
    }
    return { ok: touched > 0, touched };
  };
  const walkAshbyFieldState = () => {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'ashby-entry-not-found' };
    const wantedVal = point.wanted;
    let touched = 0;
    const ashby = window.__ashby || window.__ASHBY__;
    const entryId = entry.getAttribute('data-field-entry-id') || '';
    const tryPatch = (obj) => {
      if (!obj || typeof obj !== 'object') return false;
      let hit = false;
      for (const [key, val] of Object.entries(obj)) {
        if (typeof val === 'string' && matchesChoice(val, wantedVal)) {
          obj[key] = val;
          hit = true;
        }
        if (typeof val === 'object' && val) hit = tryPatch(val) || hit;
      }
      return hit;
    };
    if (ashby && typeof ashby === 'object') {
      touched += tryPatch(ashby) ? 1 : 0;
    }
    const btn = findChoiceTarget(entry, wantedVal);
    if (btn) {
      btn.setAttribute('aria-checked', 'true');
      btn.setAttribute('data-state', 'checked');
      const parentRadio = btn.closest('[role=radio]') || btn.parentElement;
      if (parentRadio && parentRadio.setAttribute) parentRadio.setAttribute('aria-checked', 'true');
      if (btn instanceof HTMLInputElement && (btn.type === 'radio' || btn.type === 'checkbox')) {
        btn.checked = true;
        const checkedSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked')?.set;
        if (checkedSetter) checkedSetter.call(btn, true);
      }
      invokeReactChange(btn, { checked: true, value: wantedVal });
      fireCommit(btn);
      touched += 1;
    }
    if (entryId && ashby && ashby.formState && typeof ashby.formState === 'object') {
      for (const key of Object.keys(ashby.formState)) {
        if (!entryId.includes(key) && !key.includes(entryId.split('__')[1] || entryId)) continue;
        ashby.formState[key] = wantedVal;
        touched += 1;
      }
    }
    return { ok: touched > 0, touched, entryId, hasAshby: !!ashby };
  };
  const forceAshbyBooleanCommit = () => {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'force-entry-not-found' };
    const wantedVal = point.wanted;
    const btn = findChoiceTarget(entry, wantedVal);
    if (!btn) return { ok: false, code: 'force-button-not-found' };
    btn.scrollIntoView({ block: 'center' });
    if (btn instanceof HTMLInputElement && (btn.type === 'radio' || btn.type === 'checkbox')) {
      btn.checked = true;
      const checkedSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked')?.set;
      if (checkedSetter) checkedSetter.call(btn, true);
      const linked = btn.id ? document.querySelector('label[for="' + CSS.escape(btn.id) + '"]') : null;
      linked && linked.click && linked.click();
    } else {
      btn.click();
    }
    btn.setAttribute('aria-checked', 'true');
    btn.setAttribute('data-state', 'checked');
    const parentRadio = btn.closest('[role=radio]') || entry.querySelector('[role=radio]');
    if (parentRadio && parentRadio.setAttribute) parentRadio.setAttribute('aria-checked', 'true');
    for (const sibling of entry.querySelectorAll('button')) {
      if (sibling === btn) continue;
      sibling.removeAttribute('aria-checked');
      sibling.removeAttribute('data-state');
    }
    for (const sibling of entry.querySelectorAll('input[type=radio],input[type=checkbox]')) {
      if (sibling === btn) continue;
      sibling.checked = false;
    }
    invokeReactChange(btn, { checked: true, value: wantedVal });
    fireCommit(btn);
    const ashbyWalk = walkAshbyFieldState();
    return { ok: true, ashbyWalk };
  };
  const commitRadioViaLabelAndSetter = () => {
    const entry = resolveEntry();
    if (!entry) return { ok: false, code: 'radio-entry-not-found', committed: false };
    const wantedVal = point.wanted;
    const btnFirst = findChoiceButton(entry, wantedVal);
    if (btnFirst) {
      btnFirst.scrollIntoView({ block: 'center' });
      btnFirst.click();
      btnFirst.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      btnFirst.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      btnFirst.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      btnFirst.setAttribute('aria-checked', 'true');
      btnFirst.setAttribute('aria-pressed', 'true');
      btnFirst.setAttribute('data-state', 'checked');
      for (const sibling of entry.querySelectorAll('button')) {
        if (sibling === btnFirst) continue;
        sibling.removeAttribute('aria-checked');
        sibling.removeAttribute('data-state');
        sibling.setAttribute('aria-pressed', 'false');
      }
      commitBooleanEntry(entry, wantedVal);
      invokeReactChange(btnFirst, { checked: true, value: wantedVal });
      fireCommit(btnFirst);
      return verifyEntry();
    }
    const input = findRadioInput(entry, wantedVal);
    if (!input) return { ok: false, code: 'radio-input-not-found', committed: false };
    const inputLabel = clean((input.closest('label') || input.parentElement || {}).innerText || input.value || '');
    if (/^on$/i.test(clean(input.value || '')) && !matchesChoice(inputLabel, wantedVal)) {
      return { ok: false, code: 'radio-opaque-on-skip', committed: false };
    }
    input.scrollIntoView({ block: 'center' });
    let linked = null;
    try { linked = input.id ? document.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null; } catch (_) {}
    const label = input.closest('label') || linked;
    if (label && label.click) label.click();
    input.checked = true;
    const checkedDesc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
    const checkedSetter = checkedDesc && checkedDesc.set;
    if (checkedSetter) checkedSetter.call(input, true);
    fireCommit(input);
    invokeReactChange(input, { checked: true, value: input.value || wantedVal });
    return verifyEntry();
  };
  const resolveClickCenter = () => {
    try {
    const entry = resolveEntry();
    const wantedVal = point.wanted;
    const btn = findChoiceTarget(entry, wantedVal);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      const tag = btn.tagName || '';
      const method = tag === 'INPUT' ? 'index-radio' : tag === 'BUTTON' ? 'index-button' : 'index-label';
      return { ok: true, cx: rect.left + rect.width / 2, cy: rect.top + rect.height / 2, method };
    }
    const el = document.elementFromPoint(point.x, point.y);
    if (!el) return { ok: false, code: 'click-target-not-found', x: point.x, y: point.y };
    const fallback = el.closest('button,[role=button],label,[role=radio],input[type=radio],input[type=checkbox]') || el;
    fallback.scrollIntoView({ block: 'center' });
    const rect = fallback.getBoundingClientRect();
    return { ok: true, cx: rect.left + rect.width / 2, cy: rect.top + rect.height / 2, method: 'element-from-point' };
    } catch (err) {
      return { ok: false, code: 'resolve-exception', error: String(err && err.message || err) };
    }
  };
`;
(async () => {
  const list = await CDP.List({host, port});
  const tab = list.find((t) => t.id === targetId);
  if (!tab) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: tab, host, port});
  try {
    const {Runtime, Input} = client;
    const coreBody = browserCore.replace('__POINT__', JSON.stringify(point));
    const wrapEval = (invoke) => '(() => {' + coreBody + '; ' + invoke + '})()';
    const radioRes = await Runtime.evaluate({
      awaitPromise: false,
      returnByValue: true,
      expression: wrapEval('try { const verify = commitRadioViaLabelAndSetter(); return { ok: !!(verify && verify.ok && verify.committed), verify, commitMethod: "scr04h-radio-label-setter-events" }; } catch (e) { return { ok: false, code: "scr04h-throw", error: String(e && e.message || e) }; }'),
    });
    const radioResult = radioRes.result.value || (radioRes.exceptionDetails ? { ok: false, code: 'scr04h-eval-failed', error: radioRes.exceptionDetails.text } : null);
    if (radioResult && radioResult.ok && radioResult.verify && radioResult.verify.committed) {
      process.stdout.write(JSON.stringify({
        ok: true,
        commitMethod: 'scr04h-radio-label-setter-events',
        wanted: point.wanted,
        question: point.question,
        verify: radioResult.verify,
        domSnapshot: null,
        clickMethod: 'radio-label-setter',
      }) + '\n');
      return;
    }
    const resolveRes = await Runtime.evaluate({
      awaitPromise: false,
      returnByValue: true,
      expression: wrapEval('try { return resolveClickCenter(); } catch (e) { return { ok: false, code: "resolve-throw", error: String(e && e.message || e) }; }'),
    });
    const center = resolveRes.result.value || (resolveRes.exceptionDetails ? { ok: false, code: 'resolve-eval-failed', error: resolveRes.exceptionDetails.text } : null);
    if (!center || !center.ok) {
      process.stdout.write(JSON.stringify(center || { ok: false, code: 'resolve-center-empty' }) + '\n');
      return;
    }
    const cx = Number(center.cx);
    const cy = Number(center.cy);
    await Input.dispatchMouseEvent({ type: 'mouseMoved', x: cx, y: cy });
    await Input.dispatchMouseEvent({ type: 'mousePressed', x: cx, y: cy, button: 'left', clickCount: 1 });
    await Input.dispatchMouseEvent({ type: 'mouseReleased', x: cx, y: cy, button: 'left', clickCount: 1 });
    await sleep(180);
    let verifyRes = await Runtime.evaluate({
      awaitPromise: false,
      returnByValue: true,
      expression: wrapEval('try { return verifyEntry(); } catch (e) { return { ok: false, committed: false, code: "verify-throw", error: String(e && e.message || e) }; }'),
    });
    let verify = verifyRes.result.value || { ok: false, committed: false, code: 'verify-empty', exception: verifyRes.exceptionDetails && verifyRes.exceptionDetails.text };
    let commitMethod = verify.ok ? 'cdp-trusted-click' : 'cdp-trusted-click-unverified';
    if (!verify.ok) {
      await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('commitHiddenInputs(); return { ok: true };'),
      });
      await sleep(120);
      verifyRes = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('return verifyEntry();'),
      });
      verify = verifyRes.result.value || { ok: false, committed: false };
      if (verify.ok) {
        commitMethod = 'react-native-setter-events';
      }
    }
    if (!verify.ok) {
      await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('return commitReactFiberBoolean();'),
      });
      await sleep(120);
      verifyRes = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('return verifyEntry();'),
      });
      verify = verifyRes.result.value || { ok: false, committed: false };
      if (verify.ok) {
        commitMethod = 'react-fiber-setter';
      }
    }
    if (!verify.ok) {
      await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('return forceAshbyBooleanCommit();'),
      });
      await sleep(150);
      verifyRes = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('return verifyEntry();'),
      });
      verify = verifyRes.result.value || { ok: false, committed: false };
      if (verify.ok) {
        commitMethod = 'ashby-force-commit';
      }
    }
    let domSnapshot = null;
    if (!verify.ok) {
      const snapRes = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: wrapEval('const entry = resolveEntry(); return captureDomSnapshot(entry);'),
      });
      domSnapshot = snapRes.result.value || null;
    }
    const committed = !!(verify && verify.ok && verify.committed !== false);
    process.stdout.write(JSON.stringify({
      ok: committed,
      commitMethod: committed ? commitMethod : 'uncommitted',
      wanted: point.wanted,
      question: point.question,
      verify,
      domSnapshot,
      clickMethod: center.method || null,
    }) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, json.dumps(payload_obj)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        log_scr04g(f"node-exit rc={proc.returncode} stderr={proc.stderr.strip()[:800]} stdout={proc.stdout.strip()[:800]}")
        return {"ok": False, "code": "cdp-boolean-commit-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-boolean-commit-bad-json", "stdout": proc.stdout[:500]}
    if result.get("commitMethod"):
        if result.get("commitMethod") == "react-fiber-setter":
            log_fn = log_scr04f
        elif result.get("commitMethod") == "scr04h-radio-label-setter-events":
            log_fn = log_scr04h
        elif result.get("commitMethod") == "ashby-force-commit":
            log_fn = log_scr04g
        else:
            log_fn = log_scr04e
        log_fn(
            f"boolean commitMethod={result.get('commitMethod')} committed={result.get('ok')} "
            f"wanted={wanted} question={question}"
        )
    if not result.get("ok") and result.get("domSnapshot"):
        snap = result.get("domSnapshot") or {}
        log_scr04g(
            f"boolean-failure wanted={wanted} question={question} "
            f"entryId={snap.get('entryId')} buttons={json.dumps(snap.get('buttons') or [])[:800]}"
        )
        log_scr04g(f"domSnapshot html={str(snap.get('html') or '')[:2000]}")
    elif not result.get("ok"):
        log_scr04g(
            f"boolean-failure-no-snap wanted={wanted} verify={json.dumps(result.get('verify') or {})[:500]} "
            f"clickMethod={result.get('clickMethod')} stdout={proc.stdout.strip()[:600]}"
        )
    return result


def _boolean_sort_key(point: dict) -> tuple[int, int]:
    """Work-auth / status fields before sponsorship Yes/No."""
    question = str(point.get("question") or "").lower()
    if SPONSORSHIP_LABEL_RX.search(question):
        return (2, int(point.get("index") or 0))
    if re.search(r"work authorization|authorization status|authorized to work|legally authorized", question):
        return (0, int(point.get("index") or 0))
    return (1, int(point.get("index") or 0))


def cdp_click_boolean_batch(url: str, window: int, tab: int | None, points: list[dict]) -> dict:
    """Scroll form, click each boolean with SCR-04d commit cascade, log commitMethod per field."""
    scroll = scroll_full_form(window, tab=tab)
    if not scroll.get("ok"):
        log_scr04d(f"scroll_full_form soft-fail code={scroll.get('code')}")
    time.sleep(0.4)
    clicked: list[dict] = []
    commit_methods: list[str] = []
    ordered = sorted(points, key=_boolean_sort_key)
    for point in ordered:
        committed = cdp_click_boolean_with_commit(url, point)
        if not committed.get("ok"):
            log_scr04g(
                f"boolean soft-fail wanted={point.get('wanted')} question={str(point.get('question') or '')[:80]} "
                f"verify={json.dumps(committed.get('verify') or {})[:300]}"
            )
            clicked.append({**point, "commitMethod": committed.get("commitMethod") or "soft-fail", "softFail": True})
            continue
        clicked.append({**point, "commitMethod": committed.get("commitMethod")})
        if committed.get("commitMethod"):
            commit_methods.append(str(committed.get("commitMethod")))
        time.sleep(0.35)
    if commit_methods:
        log_scr04d(f"batch commitMethods={commit_methods} count={len(clicked)}")
    soft_fails = sum(1 for item in clicked if item.get("softFail"))
    return {"ok": True, "clicked": len(clicked), "points": clicked, "scr04d_methods": commit_methods, "softFails": soft_fails}


def scan_boolean_groups_pre_submit(url: str, window: int, tab: int | None = None) -> dict:
    """Pre-submit scan: log all boolean groups and whether they appear committed."""
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    scan = js_eval(
        r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + r"""
  const isChoicePressed = (el) => {
    if (!el) return false;
    const cls = (el.className || '').toString();
    return el.getAttribute('aria-checked') === 'true'
      || el.getAttribute('aria-selected') === 'true'
      || el.getAttribute('aria-pressed') === 'true'
      || el.getAttribute('data-state') === 'checked'
      || el.getAttribute('data-selected') === 'true'
      || el.classList.contains('selected')
      || el.classList.contains('active')
      || /(?:^|\\s)_active(?:_|\\s|$)/.test(cls);
  };
  const groups = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {
    const question = authQuestionText(entry);
    const wanted = resolveAuthWanted(entry, question);
    if (!wanted) return;
    const controls = [...entry.querySelectorAll('button,label,[role=radio]')];
    if (controls.length < 2) return;
    const selected = controls.find((el) => isChoicePressed(el));
    const checkedInput = entry.querySelector('input[type=radio]:checked,input[type=checkbox]:checked');
    const checkedLabel = clean((checkedInput && (checkedInput.closest('label') || checkedInput.parentElement) || {}).innerText || (checkedInput || {}).value || '');
    const checkedVal = clean((checkedInput || {}).value || '');
    const selectedText = clean((selected || checkedInput || {}).innerText || checkedVal || '');
    const authYesNo = /authorized to work|legally authorized|eligible to work/i.test(question);
    const checkedOk = !!(selected || (checkedInput && !(/^on$/i.test(checkedVal) && authYesNo && !/^yes\\b/i.test(checkedLabel))));
    const wantedOk = checkedOk && matchesChoice(selectedText, wanted);
    const fieldErrorEl = entry.querySelector('.ashby-application-form-field-error, [class*="FieldError"], [data-testid*="error"], [role="alert"]');
    const entryError = fieldErrorEl ? /required|please select|missing entry for required field/i.test(clean(fieldErrorEl.innerText || '')) : false;
    groups.push({
      index,
      question,
      wanted,
      committed: wantedOk && !entryError,
      selectedText,
      entryError,
    });
  });
  return JSON.stringify({ ok: true, groups, uncommitted: groups.filter((g) => !g.committed).length });
})()
""",
        window=window,
        tab=tab,
        timeout=20,
    )
    if scan.get("groups"):
        for group in scan["groups"]:
            log_scr04d(
                f"pre-submit-scan index={group.get('index')} committed={group.get('committed')} "
                f"selected={group.get('selectedText', '')[:60]!r} question={group.get('question', '')[:80]!r}"
            )
    return scan


def cdp_type_points(url: str, entries: list[dict]) -> dict:
    if not entries:
        return {"ok": True, "typed": 0}
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const entries = JSON.parse(process.argv[2] || '[]');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime} = client;
    for (const item of entries) {
      const x = Number(item.x);
      const y = Number(item.y);
      const text = String(item.text || '');
      const res = await Runtime.evaluate({
        awaitPromise: true,
        returnByValue: true,
        expression: `(() => {
          const el = document.elementFromPoint(${x}, ${y}) || document.activeElement;
          if (!el || !('value' in el)) return { ok: false, code: 'type-target-not-found' };
          const next = ${JSON.stringify(text)};
          el.focus();
          const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
          if (setter) setter.call(el, next);
          else el.value = next;
          el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: next }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('blur', { bubbles: true }));
          return { ok: true };
        })()`,
      });
      if (!res.result.value || !res.result.value.ok) {
        process.stdout.write(JSON.stringify(res.result.value || { ok: false, code: 'type-eval-failed' }) + '\n');
        return;
      }
      await sleep(250);
    }
    process.stdout.write(JSON.stringify({ok: true, typed: entries.length}) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, json.dumps(entries)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-type-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-type-bad-json", "stdout": proc.stdout[:500]}


LINKEDIN_FIELD_LABEL_RX = re.compile(
    r"linkedin\s*profile|linkedin\s*url|linkedin\s*link|please provide.*linkedin|linkedin.*below|^linkedin\b",
    re.I,
)
HEAR_ABOUT_INLINE_RX = (
    r"how did you hear|how'd you hear about|how'd you hear|hear about us|hear about|"
    r"where did you find|referral source|how did you learn"
)
HEAR_ABOUT_LABEL_RX = re.compile(HEAR_ABOUT_INLINE_RX, re.I)
APPLY_OPTIMIZE_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-20260612.log"
APPLY_OPTIMIZE_ROUND2_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round2-20260612.log"
APPLY_OPTIMIZE_ROUND3_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round3-20260612.log"
APPLY_OPTIMIZE_ROUND4_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round4-20260612.log"
APPLY_OPTIMIZE_ROUND5_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round5-20260612.log"
APPLY_OPTIMIZE_ROUND6_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round6-20260612.log"
APPLY_OPTIMIZE_ROUND7_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round7-20260612.log"
APPLY_OPTIMIZE_ROUND8_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round8-20260612.log"
APPLY_OPTIMIZE_ROUND9_LOG = HOME / "job-hunt" / "reports" / "apply-optimize-round9-20260612.log"
SPONSORSHIP_INLINE_RX = (
    r"will you now or in the future require sponsorship|"
    r"require sponsorship for employment visa|"
    r"require sponsorship.*visa status|"
    r"sponsorship for employment visa"
)
SPONSORSHIP_LABEL_RX = re.compile(SPONSORSHIP_INLINE_RX, re.I)
SPONSORSHIP_MISSING_RX = re.compile(r"missing entry for required field:.*sponsorship", re.I)
BOOLEAN_INLINE_RX = (
    r"authorized to work|legally authorized|eligible to work|work authorization|"
    r"sponsor|sponsorship|require.*visa|future.*visa|immigration-related|immigration related support|"
    + SPONSORSHIP_INLINE_RX
)
BOOLEAN_LABEL_RX = re.compile(BOOLEAN_INLINE_RX, re.I)
AUTHENTIC_SHORTTEXT_SKIP_RX = re.compile(
    r"favorite video game|favourite video game|most played game|video game you",
    re.I,
)
NON_BLOCKER_INVALID_RX = re.compile(
    r"please select a file|please fill out this field|^(location|resume|name|email|state|city|linkedin profile?|linkedin)$",
    re.I,
)
COUNTRY_FIELD_RX = re.compile(
    r"passport country|country of residence|country.*residence|nationality",
    re.I,
)
HEAR_ABOUT_CHOICES = (
    "LinkedIn",
    "Online",
    "Other",
    "Company careers page",
    "Company website",
    "Job board",
    "Internet",
    "Social media",
)
HEAR_ABOUT_TEXT_DEFAULT = "LinkedIn"


def log_scr04c(message: str) -> None:
    try:
        APPLY_OPTIMIZE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with APPLY_OPTIMIZE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"[SCR-04c] {message}\n")
    except OSError:
        pass


def log_scr04d(message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    line = f"[SCR-04d] {stamp} {message}\n"
    for path in (APPLY_OPTIMIZE_LOG, APPLY_OPTIMIZE_ROUND2_LOG, APPLY_OPTIMIZE_ROUND3_LOG):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def log_scr04e(message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    line = f"[SCR-04e] {stamp} {message}\n"
    for path in (APPLY_OPTIMIZE_LOG, APPLY_OPTIMIZE_ROUND3_LOG, APPLY_OPTIMIZE_ROUND4_LOG):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def log_scr04f(message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    line = f"[SCR-04f] {stamp} {message}\n"
    for path in (APPLY_OPTIMIZE_LOG, APPLY_OPTIMIZE_ROUND4_LOG, APPLY_OPTIMIZE_ROUND5_LOG):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def log_scr04g(message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    line = f"[SCR-04g] {stamp} {message}\n"
    for path in (APPLY_OPTIMIZE_LOG, APPLY_OPTIMIZE_ROUND5_LOG, APPLY_OPTIMIZE_ROUND6_LOG):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def log_scr04h(message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    line = f"[SCR-04h] {stamp} {message}\n"
    for path in (APPLY_OPTIMIZE_LOG, APPLY_OPTIMIZE_ROUND6_LOG, APPLY_OPTIMIZE_ROUND7_LOG, APPLY_OPTIMIZE_ROUND8_LOG, APPLY_OPTIMIZE_ROUND9_LOG):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def scroll_full_form(window: int, tab: int | None = None) -> dict:
    """Scroll entire Ashby form so lazy boolean groups render before CDP clicks."""
    return js_eval(
        r"""
(() => {
  const form = document.querySelector('form') || document.querySelector('[class*="application-form"]') || document.body;
  const maxScroll = Math.max(0, (document.documentElement.scrollHeight || form.scrollHeight || 0) - window.innerHeight);
  const steps = Math.min(14, Math.max(4, Math.ceil(maxScroll / 350) + 1));
  for (let i = 0; i <= steps; i++) {
    window.scrollTo({ top: Math.floor((maxScroll * i) / steps), behavior: 'instant' });
  }
  window.scrollTo({ top: 0, behavior: 'instant' });
  return JSON.stringify({ ok: true, steps, maxScroll });
})()
""",
        window=window,
        tab=tab,
        timeout=20,
    )


def cdp_keyboard_type_entries(url: str, entries: list[dict]) -> dict:
    """Type into React-controlled Ashby inputs via CDP Input domain (not DOM .value)."""
    if not entries:
        return {"ok": True, "typed": 0}
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const entries = JSON.parse(process.argv[2] || '[]');
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const META = 8;
const keyEvent = async (Input, payload) => {
  await Input.dispatchKeyEvent(payload);
};
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime, Input} = client;
    if (Input.enable) await Input.enable();
    const typed = [];
    for (const item of entries) {
      const selector = String(item.selector || '');
      const text = String(item.text || '');
      if (!selector || !text) continue;
      const focusRes = await Runtime.evaluate({
        awaitPromise: false,
        returnByValue: true,
        expression: `(() => {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return { ok: false, code: 'field-not-found' };
          el.scrollIntoView({ block: 'center' });
          el.focus();
          el.click();
          return { ok: true, value: (el.value || '').trim() };
        })()`,
      });
      const focus = focusRes.result.value;
      if (!focus || !focus.ok) {
        process.stdout.write(JSON.stringify(focus || { ok: false, code: 'keyboard-focus-failed' }) + '\n');
        return;
      }
      await keyEvent(Input, { type: 'rawKeyDown', modifiers: META, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
      await keyEvent(Input, { type: 'keyUp', modifiers: META, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
      await sleep(40);
      await keyEvent(Input, { type: 'rawKeyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
      await keyEvent(Input, { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
      await sleep(60);
      if (Input.insertText) {
        await Input.insertText({ text });
      } else {
        for (const ch of text) {
          await keyEvent(Input, { type: 'keyDown', text: ch });
          await keyEvent(Input, { type: 'keyUp', text: ch });
          await sleep(8);
        }
      }
      await sleep(120);
      const want = text;
      const verifyExpr = (sel, expected) => `(() => {
        const el = document.querySelector(${JSON.stringify(sel)});
        if (!el) return { ok: false, code: 'verify-not-found' };
        const value = (el.value || '').trim();
        const want = ${JSON.stringify(text)};
        const domOk = value.length > 0 && (value === want || value.includes(want) || value.includes('linkedin.com/in/'));
        const entry = el.closest('.ashby-application-form-field-entry, [data-field-entry-id]');
        const ariaInvalid = el.getAttribute('aria-invalid') === 'true';
        const errorEl = entry && entry.querySelector('[role=alert], [aria-live=assertive], .ashby-field-error, [data-error], .error-message');
        const errorText = (errorEl && errorEl.innerText) || '';
        const entryError = /\\bthis field is required\\b|please select an option|please select one|missing entry for required field|please fill out this field/i.test(errorText.slice(0, 300));
        const reactOk = domOk && !ariaInvalid && !entryError;
        return { ok: reactOk, domOk, value, ariaInvalid, entryError: !!entryError };
      })()`;
      const commitMethods = [
        {
          id: 'events-input-change-blur',
          run: async () => {
            await Runtime.evaluate({
              awaitPromise: false,
              returnByValue: true,
              expression: `(() => {
                const el = document.querySelector(${JSON.stringify(selector)});
                if (!el) return { ok: false };
                el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: el.value || '' }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
                return { ok: true };
              })()`,
            });
            await sleep(150);
          },
        },
        {
          id: 'react-native-setter',
          run: async () => {
            await Runtime.evaluate({
              awaitPromise: false,
              returnByValue: true,
              expression: `(() => {
                const el = document.querySelector(${JSON.stringify(selector)});
                if (!el) return { ok: false };
                const next = ${JSON.stringify(text)};
                const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                if (setter) setter.call(el, next);
                else el.value = next;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
                return { ok: true, value: (el.value || '').trim() };
              })()`,
            });
            await sleep(150);
          },
        },
        {
          id: 'tab-out-wait',
          run: async () => {
            await keyEvent(Input, { type: 'rawKeyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
            await keyEvent(Input, { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
            await sleep(350);
          },
        },
      ];
      let commitMethod = 'keyboard-only';
      let verify = null;
      for (const method of commitMethods) {
        await method.run();
        const verifyRes = await Runtime.evaluate({
          awaitPromise: false,
          returnByValue: true,
          expression: verifyExpr(selector, want),
        });
        verify = verifyRes.result.value;
        if (verify && verify.ok) {
          commitMethod = method.id;
          break;
        }
      }
      if (!verify || !verify.ok) {
        process.stdout.write(JSON.stringify({
          ok: false,
          code: 'keyboard-verify-failed',
          selector,
          expected: text,
          actual: verify && verify.value,
          commitMethod,
          domOk: verify && verify.domOk,
        }) + '\n');
        return;
      }
      typed.push({ selector, label: item.label || '', value: verify.value, commitMethod });
    }
    process.stdout.write(JSON.stringify({ ok: true, typed: typed.length, entries: typed }) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, json.dumps(entries)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-keyboard-type-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-keyboard-type-bad-json", "stdout": proc.stdout[:500]}
    if result.get("ok") and result.get("entries"):
        methods = [entry.get("commitMethod") for entry in result["entries"] if entry.get("commitMethod")]
        if methods:
            result["scr04c_methods"] = methods
            log_scr04c(f"cdp_keyboard_type_entries methods={methods} selectors={[e.get('selector') for e in result['entries']]}")
    return result


def cdp_combobox_type_arrow_enter(url: str, selector: str, text: str, label: str = "") -> dict:
    """Type into an Ashby combobox and commit the first suggestion via ArrowDown + Enter."""
    if not selector or not text:
        return {"ok": False, "code": "combobox-empty-input"}
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const selector = process.argv[2];
const text = process.argv[3];
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const META = 8;
const keyEvent = async (Input, payload) => {
  await Input.dispatchKeyEvent(payload);
};
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime, Input} = client;
    if (Input.enable) await Input.enable();
    const focusRes = await Runtime.evaluate({
      awaitPromise: false,
      returnByValue: true,
      expression: `(() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { ok: false, code: 'field-not-found' };
        el.scrollIntoView({ block: 'center' });
        el.focus();
        el.click();
        return { ok: true, value: (el.value || '').trim() };
      })()`,
    });
    const focus = focusRes.result.value;
    if (!focus || !focus.ok) {
      process.stdout.write(JSON.stringify(focus || { ok: false, code: 'combobox-focus-failed' }) + '\n');
      return;
    }
    await keyEvent(Input, { type: 'rawKeyDown', modifiers: META, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await keyEvent(Input, { type: 'keyUp', modifiers: META, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await sleep(40);
    await keyEvent(Input, { type: 'rawKeyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
    await keyEvent(Input, { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
    await sleep(60);
    if (Input.insertText) await Input.insertText({ text });
    else {
      for (const ch of text) {
        await keyEvent(Input, { type: 'keyDown', text: ch });
        await keyEvent(Input, { type: 'keyUp', text: ch });
        await sleep(8);
      }
    }
    await sleep(1200);
    await keyEvent(Input, { type: 'rawKeyDown', key: 'ArrowDown', code: 'ArrowDown', windowsVirtualKeyCode: 40 });
    await keyEvent(Input, { type: 'keyUp', key: 'ArrowDown', code: 'ArrowDown', windowsVirtualKeyCode: 40 });
    await sleep(120);
    await keyEvent(Input, { type: 'rawKeyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await keyEvent(Input, { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await sleep(500);
    const verifyRes = await Runtime.evaluate({
      awaitPromise: false,
      returnByValue: true,
      expression: `(() => {
        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { ok: false, code: 'verify-not-found' };
        const value = clean(el.value || '');
        const entryNode = el.closest('.ashby-application-form-field-entry, [data-field-entry-id]');
        const entryText = clean((entryNode && entryNode.innerText) || '');
        const entryError = /missing entry for required field|please select an option|please fill out this field/i.test(entryText.slice(0, 500));
        const ok = value.length > 0 && !entryError;
        return { ok, value, entryError: !!entryError };
      })()`,
    });
    let verify = verifyRes.result.value;
    if (!verify || !verify.ok) {
      const optionRes = await Runtime.evaluate({
        awaitPromise: false,
        returnByValue: true,
        expression: `(() => {
          const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
          const opt = [...document.querySelectorAll('[role=option]')].find((el) => /san francisco|bay area|united states|remote/i.test(clean(el.innerText || '')));
          if (!opt) return { ok: false, code: 'combobox-option-not-found' };
          opt.scrollIntoView({ block: 'center' });
          opt.click();
          return { ok: true, text: clean(opt.innerText || '') };
        })()`,
      });
      const option = optionRes.result.value;
      if (option && option.ok) {
        await sleep(500);
        const verifyRes2 = await Runtime.evaluate({
          awaitPromise: false,
          returnByValue: true,
          expression: `(() => {
            const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
            const el = document.querySelector(${JSON.stringify(selector)});
            if (!el) return { ok: false, code: 'verify-not-found' };
            const value = clean(el.value || '');
            const entryNode = el.closest('.ashby-application-form-field-entry, [data-field-entry-id]');
            const entryText = clean((entryNode && entryNode.innerText) || '');
            const entryError = /missing entry for required field|please select an option|please fill out this field/i.test(entryText.slice(0, 500));
            return { ok: value.length > 0 && !entryError, value, entryError: !!entryError, commitMethod: 'option-click-fallback' };
          })()`,
        });
        verify = verifyRes2.result.value;
      }
    } else if (verify) {
      verify.commitMethod = 'arrow-down-enter';
    }
    process.stdout.write(JSON.stringify(verify || { ok: false, code: 'combobox-verify-failed' }) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, selector, text],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-combobox-type-failed", "selector": selector, "label": label, "stderr": proc.stderr.strip()[:500]}
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-combobox-type-bad-json", "stdout": proc.stdout[:500]}
    if result.get("ok"):
        method = result.get("commitMethod") or "arrow-down-enter"
        result["scr04c_methods"] = [method]
        log_scr04c(f"cdp_combobox_type_arrow_enter label={label!r} method={method} value={result.get('value')!r}")
    return result


def cdp_set_file_input(url: str, resume: Path) -> dict:
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    resume_path = str(resume.resolve())
    log_scr04h(f"cdp_set_file_input path={resume_path} url={url[:120]}")
    if not resume.exists():
        return {"ok": False, "code": "resume-file-missing", "path": resume_path}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const resumePath = process.argv[2];
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const selectors = [
  'input[type=file]#_systemfield_resume',
  'input[type=file][name="_systemfield_resume"]',
  'input[type=file][id="_systemfield_resume"]',
  'input[type=file]'
];
const readState = (used) => {
  const target = used ? document.querySelector(used) : null;
  const files = [...document.querySelectorAll('input[type=file]')].map((input) => ({
    id: input.id || '',
    name: input.name || '',
    count: input.files ? input.files.length : 0,
    names: [...(input.files || [])].map((f) => f.name),
    visible: !!(input.offsetWidth || input.offsetHeight || input.getClientRects().length),
  }));
  const targetCount = target && target.files ? target.files.length : 0;
  return {
    ok: targetCount > 0 || files.some((f) => (f.id === '_systemfield_resume' || f.name === '_systemfield_resume') && f.count > 0),
    selector: used || '',
    resumePath,
    targetCount,
    files,
  };
};
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {DOM, Runtime} = client;
    await DOM.enable();
    let used = '';
    let nodeId = 0;
    for (let attempt = 0; attempt < 12 && !nodeId; attempt += 1) {
      const {root} = await DOM.getDocument({depth: -1, pierce: true});
      for (const selector of selectors) {
        const found = await DOM.querySelector({nodeId: root.nodeId, selector});
        if (found && found.nodeId) {
          nodeId = found.nodeId;
          used = selector;
          break;
        }
      }
      if (!nodeId) await sleep(500);
    }
    if (!nodeId) {
      process.stdout.write(JSON.stringify({ok:false, code:'file-input-not-found', resumePath, attempts:12}) + '\n');
      return;
    }
    const resolveNode = async (prefer) => {
      const {root} = await DOM.getDocument({depth: -1, pierce: true});
      const order = prefer ? [prefer, ...selectors.filter((s) => s !== prefer)] : selectors;
      for (const selector of order) {
        const found = await DOM.querySelector({nodeId: root.nodeId, selector});
        if (found && found.nodeId) return { nodeId: found.nodeId, used: selector };
      }
      return { nodeId: 0, used: '' };
    };
    let lastState = { ok: false, selector: used, resumePath, targetCount: 0, files: [] };
    for (let attachAttempt = 0; attachAttempt < 3; attachAttempt += 1) {
      const resolved = await resolveNode(used || 'input[type=file]#_systemfield_resume');
      if (!resolved.nodeId) { await sleep(600); continue; }
      nodeId = resolved.nodeId;
      used = resolved.used;
      await DOM.setFileInputFiles({nodeId, files: [resumePath]});
      await Runtime.evaluate({expression: `
(() => {
  const reactFiberKey = (el) => Object.keys(el || {}).find((k) => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  const reactPropsKey = (el) => Object.keys(el || {}).find((k) => k.startsWith('__reactProps'));
  const invokeReactChange = (el) => {
    if (!el) return false;
    let invoked = false;
    const propsKey = reactPropsKey(el);
    const props = propsKey ? el[propsKey] : null;
    const synthetic = { target: el, currentTarget: el, bubbles: true, type: 'change' };
    if (props && typeof props.onChange === 'function') {
      props.onChange(synthetic);
      invoked = true;
    }
    let fiber = el[reactFiberKey(el)];
    for (let depth = 0; depth < 16 && fiber; depth += 1, fiber = fiber.return) {
      const fp = fiber.memoizedProps || fiber.pendingProps;
      if (fp && typeof fp.onChange === 'function') {
        fp.onChange(synthetic);
        invoked = true;
        break;
      }
    }
    return invoked;
  };
  const input = document.querySelector(${JSON.stringify(used)});
  if (!input) return false;
  input.dispatchEvent(new Event('input', {bubbles:true}));
  input.dispatchEvent(new Event('change', {bubbles:true}));
  input.dispatchEvent(new Event('blur', {bubbles:true}));
  invokeReactChange(input);
  return true;
})()
`, awaitPromise: true});
      await sleep(900);
      const state = await Runtime.evaluate({returnByValue:true, expression: `(() => ${readState.toString()})(${JSON.stringify(used)})`});
      lastState = state.result.value || lastState;
      if (lastState.ok) break;
      if (attachAttempt === 0 && used !== 'input[type=file]#_systemfield_resume') {
        const {root} = await DOM.getDocument({depth: -1, pierce: true});
        const retry = await DOM.querySelector({nodeId: root.nodeId, selector: 'input[type=file]#_systemfield_resume'});
        if (retry && retry.nodeId) {
          nodeId = retry.nodeId;
          used = 'input[type=file]#_systemfield_resume';
        }
      }
    }
    if (!lastState.ok) {
      const {root} = await DOM.getDocument({depth: -1, pierce: true});
      for (const selector of selectors) {
        const found = await DOM.querySelector({nodeId: root.nodeId, selector});
        if (!found || !found.nodeId || selector === used) continue;
        await DOM.setFileInputFiles({nodeId: found.nodeId, files: [resumePath]});
        await sleep(900);
        const state = await Runtime.evaluate({returnByValue:true, expression: `(() => ${readState.toString()})(${JSON.stringify(selector)})`});
        const candidate = state.result.value || {};
        if (candidate.ok) {
          lastState = candidate;
          break;
        }
      }
    }
    process.stdout.write(JSON.stringify({...lastState, attachAttempts: 3, resumePath}) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, resume_path],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
        env=env,
    )
    if proc.returncode != 0:
        log_scr04h(f"cdp_set_file_input failed rc={proc.returncode} stderr={proc.stderr.strip()[:300]} path={resume_path}")
        return {"ok": False, "code": "cdp-file-upload-failed", "stderr": proc.stderr.strip()[:500], "path": resume_path}
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-file-upload-bad-json", "stdout": proc.stdout[:500], "path": resume_path}
    log_scr04h(
        f"cdp_set_file_input ok={result.get('ok')} selector={result.get('selector')} "
        f"targetCount={result.get('targetCount')} path={resume_path}"
    )
    return result


S3_RESUME_UPLOAD_RX = re.compile(
    r"failed to upload|Failed to fetch \(ashbyhq-infra|ashbyhq-infra-prd-main-app-uploaded-files",
    re.I,
)


def page_has_resume_s3_error(window: int, tab: int | None = None) -> bool:
    scan = js_eval(
        r"""
(() => {
  const text = (document.body && document.body.innerText) || '';
  return JSON.stringify({
    ok: true,
    s3Error: /failed to upload|Failed to fetch \(ashbyhq-infra|ashbyhq-infra-prd-main-app-uploaded-files/i.test(text),
    text: text.replace(/\s+/g, ' ').trim().slice(0, 800),
  });
})()
""",
        window=window,
        tab=tab,
        timeout=15,
    )
    return bool(scan.get("s3Error"))


def retry_resume_upload(url: str, resume: Path, *, wait_sec: float = 3.0) -> dict:
    log_scr04h(f"resume-s3-retry cdp_set_file_input path={resume.resolve()} url={url[:120]}")
    result = cdp_set_file_input(url, resume)
    time.sleep(wait_sec)
    return result




def reinforce_missing_work_auth_entries(url: str, window: int, tab: int | None = None) -> dict:
    """Retry auth status / sponsorship button groups when Ashby reports missing required field."""
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(
        r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
"""
        + BOOLEAN_MATCH_JS
        + r"""
  const targets = [];
  for (const entry of fieldEntries()) {
    const question = authQuestionText(entry);
    const wanted = resolveAuthWanted(entry, question);
    if (!wanted) continue;
    const btn = findChoiceControl(entry, wanted);
    if (!btn) continue;
    btn.scrollIntoView({block:'center'});
    const r = btn.getBoundingClientRect();
    targets.push({index: targets.length, question: question.slice(0, 220), wanted, x: r.left + r.width / 2, y: r.top + r.height / 2});
  }
  return JSON.stringify({ok:true, targets});
})()
""",
        window=window,
        tab=tab,
        timeout=20,
    )
    if not targets.get("ok"):
        return targets
    points = list(targets.get("targets") or [])
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    log_scr04h(f"reinforce_missing_work_auth_entries count={len(points)} wanted={[p.get('wanted') for p in points]}")
    return cdp_click_boolean_batch(url, window, tab, points)

def reinforce_workos_auth_booleans(url: str, window: int, tab: int | None = None) -> dict:
    """SCR-04h post-autofill: legally authorized → Yes; sponsorship → No."""
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(
        r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
"""
        + BOOLEAN_MATCH_JS
        + r"""
  const targets = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {
    const question = authQuestionText(entry);
    const wanted = resolveAuthWanted(entry, question);
    if (!wanted) return;
    const btn = findChoiceControl(entry, wanted);
    if (!btn) return;
    btn.scrollIntoView({block:'center'});
    const r = btn.getBoundingClientRect();
    targets.push({index, question: question.slice(0, 220), wanted, x: r.left + r.width / 2, y: r.top + r.height / 2});
  });
  return JSON.stringify({ok:true, targets});
})()
""",
        window=window,
        tab=tab,
        timeout=20,
    )
    if not targets.get("ok"):
        return targets
    points = list(targets.get("targets") or [])
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    log_scr04h(
        f"reinforce_workos_auth_booleans count={len(points)} "
        f"wanted={[p.get('wanted') for p in points]} "
        f"questions={[p.get('question','')[:60] for p in points]}"
    )
    return cdp_click_boolean_batch(url, window, tab, points)


def reinforce_sponsorship_boolean(url: str, window: int, tab: int | None = None) -> dict:
    """Backward-compatible alias: SCR-04h auth Yes + sponsorship No."""
    return reinforce_workos_auth_booleans(url, window, tab=tab)


reinforce_auth_sponsorship = reinforce_workos_auth_booleans


def reinforce_status_style_work_auth(url: str, window: int, tab: int | None = None) -> dict:
    """Click visible Citizen/Permanent Resident buttons; skip opaque value=on radios."""
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(
        r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
"""
        + BOOLEAN_MATCH_JS
        + r"""
  const statusRx = /what is your work authorization|work authorization status/i;
  const targets = [];
  for (const entry of fieldEntries()) {
    const question = authQuestionText(entry);
    if (!statusRx.test(question)) continue;
    const wanted = resolveAuthWanted(entry, question);
    if (!wanted) continue;
    for (const input of entry.querySelectorAll('input[type=radio],input[type=checkbox]')) {
      const val = clean(input.value || '');
      const label = clean((input.closest('label') || input.parentElement || {}).innerText || '');
      if (/^on$/i.test(val) && !matchesChoice(label, wanted)) {
        input.checked = false;
        fireCommit(input);
      }
    }
    const btn = findChoiceControl(entry, wanted);
    if (!btn) continue;
    btn.scrollIntoView({block:'center'});
    const r = btn.getBoundingClientRect();
    targets.push({
      index: targets.length,
      question: question.slice(0, 220),
      wanted,
      x: r.left + r.width / 2,
      y: r.top + r.height / 2,
      method: 'status-style-choice',
    });
  }
  return JSON.stringify({ok:true, targets});
})()
""",
        window=window,
        tab=tab,
        timeout=20,
    )
    if not targets.get("ok"):
        return targets
    points = list(targets.get("targets") or [])
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    log_scr04h(f"reinforce_status_style_work_auth count={len(points)} wanted={[p.get('wanted') for p in points]}")
    return cdp_click_boolean_batch(url, window, tab, points)


def reinforce_uncommitted_auth_booleans(url: str, window: int, tab: int | None = None) -> dict:
    """SCR-04: retry auth/sponsorship button groups until pre-submit scan shows committed."""
    scan = scan_boolean_groups_pre_submit(url, window, tab=tab)
    points: list[dict] = []
    for group in scan.get("groups") or []:
        if group.get("committed"):
            continue
        question = str(group.get("question") or "")
        point = js_eval(
            f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
"""
            + BOOLEAN_MATCH_JS
            + f"""
  const entries = [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')];
  const entry = entries[{int(group["index"])}];
  if (!entry) return JSON.stringify({{ok:false, code:'auth-retry-entry-not-found'}});
  const question = {json.dumps(question[:220])};
  const wanted = resolveAuthWanted(entry, question);
  if (!wanted) return JSON.stringify({{ok:false, code:'auth-retry-no-wanted', question}});
  const btn = findChoiceControl(entry, wanted);
  if (!btn) return JSON.stringify({{ok:false, code:'auth-retry-button-not-found', wanted, question}});
  btn.scrollIntoView({{block:'center'}});
  commitBooleanEntry(entry, wanted);
  const r = btn.getBoundingClientRect();
  return JSON.stringify({{
    ok:true,
    index:{int(group["index"])},
    question,
    wanted,
    x:r.left + r.width / 2,
    y:r.top + r.height / 2,
  }});
}})()
""",
            window=window,
            tab=tab,
            timeout=20,
        )
        if point.get("ok"):
            points.append(point)
    if not points:
        return {"ok": True, "clicked": 0, "points": [], "uncommitted_before": scan.get("uncommitted", 0)}
    log_scr04h(f"reinforce_uncommitted_auth_booleans count={len(points)} wanted={[p.get('wanted') for p in points]}")
    result = cdp_click_boolean_batch(url, window, tab, points)
    scan_after = scan_boolean_groups_pre_submit(url, window, tab=tab)
    result["uncommitted_before"] = scan.get("uncommitted", 0)
    result["uncommitted_after"] = scan_after.get("uncommitted", 0)
    return result


def reinforce_sponsorship_strict(url: str, window: int, tab: int | None = None, *, max_attempts: int = 3) -> dict:
    """Commit sponsorship + work-auth booleans; auth status before sponsorship."""
    attempts: list[dict] = []
    last_scan: dict = {}

    def sponsorship_uncommitted(scan: dict) -> list[dict]:
        return [
            g for g in (scan.get("groups") or [])
            if not g.get("committed") and SPONSORSHIP_LABEL_RX.search(str(g.get("question") or ""))
        ]

    for attempt in range(max_attempts):
        scan = scan_boolean_groups_pre_submit(url, window, tab=tab)
        last_scan = scan
        uncommitted = [
            g for g in (scan.get("groups") or [])
            if not g.get("committed")
        ]
        if not uncommitted:
            return {"ok": True, "attempts": attempts, "scan": scan}
        points: list[dict] = []
        for group in sorted(uncommitted, key=lambda g: _boolean_sort_key({"question": g.get("question"), "index": g.get("index")})):
            point = js_eval(
                f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
"""
                + BOOLEAN_MATCH_JS
                + f"""
  const entries = [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')];
  const entry = entries[{int(group["index"])}];
  if (!entry) return JSON.stringify({{ok:false, code:'sponsorship-strict-entry-not-found'}});
  const question = {json.dumps(str(group.get("question") or "")[:220])};
  const wanted = resolveAuthWanted(entry, question);
  if (!wanted) return JSON.stringify({{ok:false, code:'sponsorship-strict-no-wanted', question}});
  const btn = findChoiceControl(entry, wanted);
  if (!btn) return JSON.stringify({{ok:false, code:'sponsorship-strict-button-not-found', wanted, question}});
  btn.scrollIntoView({{block:'center'}});
  commitBooleanEntry(entry, wanted);
  const r = btn.getBoundingClientRect();
  return JSON.stringify({{
    ok:true,
    index:{int(group["index"])},
    question,
    wanted,
    x:r.left + r.width / 2,
    y:r.top + r.height / 2,
  }});
}})()
""",
                window=window,
                tab=tab,
                timeout=20,
            )
            if point.get("ok"):
                points.append(point)
        if not points:
            attempts.append({"attempt": attempt + 1, "ok": False, "code": "no-click-targets", "uncommitted": len(uncommitted)})
            break
        click = cdp_click_boolean_batch(url, window, tab, points)
        scan_after = scan_boolean_groups_pre_submit(url, window, tab=tab)
        attempts.append({
            "attempt": attempt + 1,
            "click": click,
            "uncommitted_before": len(uncommitted),
            "uncommitted_after": scan_after.get("uncommitted", 0),
        })
        if scan_after.get("uncommitted", 0) == 0 or not sponsorship_uncommitted(scan_after):
            return {"ok": True, "attempts": attempts, "scan": scan_after}
        time.sleep(0.4)
    return {
        "ok": not sponsorship_uncommitted(last_scan),
        "attempts": attempts,
        "scan": last_scan,
        "sponsorship_uncommitted": len(sponsorship_uncommitted(last_scan)),
        "uncommitted": last_scan.get("uncommitted", 0),
    }


def reinforce_pre_submit_auth_booleans(url: str, window: int, tab: int | None = None) -> dict:
    """All Ashby boards: auth/sponsorship + standard boolean reinforce before submit."""
    steps: list[dict] = []
    for name, fn in (
        ("auth_sponsorship", lambda: reinforce_auth_sponsorship(url, window, tab=tab)),
        ("status_style_work_auth", lambda: reinforce_status_style_work_auth(url, window, tab=tab)),
        ("trusted_auth", lambda: trusted_click_auth_booleans(url, window, tab=tab)),
        ("trusted_standard", lambda: trusted_click_standard_choices(url, window, tab=tab)),
        ("trusted_extended", lambda: trusted_click_extended_booleans(url, window, tab=tab)),
        ("auth_sponsorship_retry", lambda: reinforce_auth_sponsorship(url, window, tab=tab)),
        ("hear_about", lambda: reinforce_hear_about_choice(url, window, tab=tab)),
        ("auth_uncommitted_retry", lambda: reinforce_uncommitted_auth_booleans(url, window, tab=tab)),
        ("sponsorship_strict", lambda: reinforce_sponsorship_strict(url, window, tab=tab)),
    ):
        result = fn()
        steps.append({name: result})
        if not result.get("ok"):
            return {"ok": False, "code": f"pre-submit-{name}-failed", "steps": steps, **result}
    scan_boolean_groups_pre_submit(url, window, tab=tab)
    return {"ok": True, "steps": steps}


def trusted_click_auth_booleans(url: str, window: int, tab: int | None = None) -> dict:
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + r"""
  const targets = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {
    const heading = clean((entry.querySelector('label') || {}).innerText || '');
    const question = clean(`${heading} ${entry.innerText || ''}`);
    const wanted = resolveAuthWanted(entry, question);
    if (!wanted) return;
    const btn = findChoiceControl(entry, wanted);
    if (!btn) return;
    targets.push({index, question, wanted});
  });
  return JSON.stringify({ok:true, targets});
})()
""", window=window, tab=tab, timeout=20)
    if not targets.get("ok"):
        return targets
    points: list[dict] = []
    for target in targets.get("targets") or []:
        point = js_eval(f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + f"""
  const entries = [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')];
  const entry = entries[{int(target["index"])}];
  if (!entry) return JSON.stringify({{ok:false, code:'auth-entry-not-found'}});
  const wanted = {json.dumps(target["wanted"])};
  const btn = findChoiceControl(entry, wanted);
  if (!btn) return JSON.stringify({{ok:false, code:'auth-button-not-found', wanted}});
  btn.scrollIntoView({{block:'center'}});
  const r = btn.getBoundingClientRect();
  return JSON.stringify({{ok:true, index:{int(target["index"])}, question:{json.dumps(target["question"])}, wanted, x:r.left + r.width / 2, y:r.top + r.height / 2}});
}})()
""", window=window, tab=tab, timeout=20)
        if not point.get("ok"):
            return point
        points.append(point)
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    return cdp_click_boolean_batch(url, window, tab, points)


def trusted_click_extended_booleans(url: str, window: int, tab: int | None = None) -> dict:
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + r"""
  const rules = [
    [/over the age of 18|at least 18 years/i, 'Yes'],
    [/export administration regulations|\\bear\\b|export compliance assessment|subject to the u\\.s\\. ear/i, 'No'],
    [/compensation range.*align with your expectations|does this align with your expectations/i, 'Yes'],
    [/relocate|relocation|willing to move|open to moving|willing to relocate/i, 'Yes'],
    [/sponsor|sponsorship|require.*visa|future.*visa|need.*visa|immigration-related|immigration related support/i, 'No'],
    [/disqualif|denied.*clearance|terminated.*cause|convicted|felony|misconduct/i, 'No'],
    [/consent.*background|agree.*background|authorize.*background|background check/i, 'Yes'],
    [/previously employed|previously employed by|worked at .* before|current employee of|employed by.*(?:Plaid|Quovo|Cognito)/i, 'No'],
    [/consent to receiving text|text message updates from/i, 'No'],
    [/permanent resident|green card|u\.s\. citizen/i, 'Yes'],
    [/agree to|i agree|acknowledge|accept the terms|consent to/i, 'Yes'],
    [/remote.*us|based in.*united states|located in.*united states/i, 'Yes'],
    [/willing to travel/i, 'Yes'],
  ];
  const targets = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {
    const question = clean((entry.querySelector('label') || {}).innerText || entry.innerText || '');
    if (!question) return;
    let wanted = resolveAuthWanted(entry, question) || resolveBooleanWanted(question);
    if (!wanted) {
      for (const [rx, candidate] of rules) {
        if (!rx.test(question)) continue;
        wanted = candidate;
        break;
      }
    }
    if (!wanted) return;
    const btn = findChoiceControl(entry, wanted);
    if (!btn) return;
    btn.scrollIntoView({block:'center'});
    const r = btn.getBoundingClientRect();
    targets.push({index, question: question.slice(0, 220), wanted, x: r.left + r.width / 2, y: r.top + r.height / 2});
  });
  return JSON.stringify({ok:true, targets});
})()
""", window=window, tab=tab, timeout=20)
    if not targets.get("ok"):
        return targets
    points = list(targets.get("targets") or [])
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    return cdp_click_boolean_batch(url, window, tab, points)


def trusted_click_standard_choices(url: str, window: int, tab: int | None = None) -> dict:
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    targets = js_eval(f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + f"""
  const targets = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {{
    const text = clean(entry.innerText || '');
    let el = null;
    let wanted = '';
    if (/preferred pronouns/i.test(text)) {{
      wanted = 'He/Him';
      el = [...entry.querySelectorAll('label,button')].find((node) => clean(node.innerText || node.value || '') === wanted);
    }} else if (/sponsor|sponsorship|require.*visa|future.*visa|immigration-related|immigration related support/i.test(text)) {{
      wanted = 'No';
      el = findChoiceControl(entry, wanted);
    }} else if (/previously employed|previously employed by|employed by.*(?:Plaid|Quovo|Cognito)/i.test(text)) {{
      wanted = 'No';
      el = findChoiceControl(entry, wanted);
    }} else if (/consent to receiving text|text message updates from/i.test(text)) {{
      wanted = 'No';
      el = findChoiceControl(entry, wanted);
    }} else {{
      const authWanted = resolveAuthWanted(entry, text);
      if (authWanted) {{
        wanted = authWanted;
        el = findChoiceControl(entry, wanted);
      }}
    }}
    if (!el && /{HEAR_ABOUT_INLINE_RX}/i.test(text)) {{
      for (const choice of ['LinkedIn', 'Online', 'Other', 'Company careers page', 'Company website', 'Job board', 'Internet', 'Social media']) {{
        el = [...entry.querySelectorAll('button,label,[role=radio],[role=option]')].find((node) => clean(node.innerText || node.value || node.getAttribute('aria-label') || '') === choice);
        if (el) {{ wanted = choice; break; }}
      }}
    }}
    if (!el) return;
    el.scrollIntoView({{block:'center'}});
    const r = el.getBoundingClientRect();
    targets.push({{index, wanted, text:text.slice(0,220), x:r.left + r.width / 2, y:r.top + r.height / 2}});
  }});
  return JSON.stringify({{ok:true, targets}});
}})()
""", window=window, tab=tab, timeout=20)
    if not targets.get("ok"):
        return targets
    points = list(targets.get("targets") or [])
    if not points:
        return {"ok": True, "clicked": 0, "points": []}
    return cdp_click_boolean_batch(url, window, tab, points)


def reinforce_hear_about_choice(url: str, window: int, tab: int | None = None) -> dict:
    """Fill Ashby hear-about text/combobox fields first; fall back to boolean/radio groups."""
    scroll_full_form(window, tab=tab)
    time.sleep(0.3)
    choices_js = json.dumps(list(HEAR_ABOUT_CHOICES))
    hear_default_js = json.dumps(HEAR_ABOUT_TEXT_DEFAULT)
    targets = js_eval(f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const choices = {choices_js};
  const hearRx = /{HEAR_ABOUT_INLINE_RX}/i;
  const hearDefault = {hear_default_js};
  const fieldSelector = (field, entry) => {{
    if (field.id) return '#' + CSS.escape(field.id);
    if (field.name) return 'input[name="' + CSS.escape(field.name) + '"], textarea[name="' + CSS.escape(field.name) + '"]';
    const entryId = entry && entry.getAttribute('data-field-entry-id');
    if (entryId) {{
      return '[data-field-entry-id="' + CSS.escape(entryId) + '"] input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden]), [data-field-entry-id="' + CSS.escape(entryId) + '"] textarea';
    }}
    return null;
  }};
  const targets = [];
  [...document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')].forEach((entry, index) => {{
    const text = clean(entry.innerText || '');
    const label = clean((entry.querySelector('label') || {{}}).innerText || '');
    const probe = label || text.slice(0, 220);
    if (!hearRx.test(text) && !hearRx.test(label)) return;
    const textField = entry.querySelector('input[role=combobox], input[type=text], input[type=search], textarea, input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden])');
    if (textField) {{
      const selector = fieldSelector(textField, entry);
      const current = clean(textField.value || '');
      const isCombo = textField.getAttribute('role') === 'combobox';
      textField.scrollIntoView({{block:'center'}});
      const r = textField.getBoundingClientRect();
      targets.push({{
        kind: isCombo ? 'combobox' : 'text',
        index,
        wanted: hearDefault,
        question: probe.slice(0, 220),
        text: probe.slice(0, 220),
        selector,
        x: r.left + r.width / 2,
        y: r.top + r.height / 2,
        skip: current.toLowerCase() === hearDefault.toLowerCase(),
      }});
      return;
    }}
    let el = null;
    let wanted = '';
    for (const choice of choices) {{
      el = [...entry.querySelectorAll('button,label,[role=radio],[role=option]')].find((node) => {{
        const nodeText = clean(node.innerText || node.value || node.getAttribute('aria-label') || '');
        return nodeText === choice || nodeText.toLowerCase() === choice.toLowerCase();
      }});
      if (el) {{ wanted = choice; break; }}
    }}
    if (el) {{
      el.scrollIntoView({{block:'center'}});
      const r = el.getBoundingClientRect();
      targets.push({{kind:'boolean', index, question: probe.slice(0,220), wanted, text:probe.slice(0,220), x:r.left + r.width / 2, y:r.top + r.height / 2}});
    }}
  }});
  return JSON.stringify({{ok:true, targets}});
}})()
""", window=window, tab=tab, timeout=20)
    if not targets.get("ok"):
        return targets
    clicked_points: list[dict] = []
    text_targets = [point for point in (targets.get("targets") or []) if point.get("kind") == "text" and not point.get("skip")]
    combobox_targets = [point for point in (targets.get("targets") or []) if point.get("kind") == "combobox" and not point.get("skip")]
    click_targets = [point for point in (targets.get("targets") or []) if point.get("kind") == "boolean"]
    for point in text_targets:
        selector = point.get("selector")
        if selector:
            typed = cdp_keyboard_type_entries(url, [{"selector": selector, "text": HEAR_ABOUT_TEXT_DEFAULT, "label": point.get("question", "")}])
            if not typed.get("ok"):
                return {"ok": False, "point": point, **typed}
            clicked_points.append({**point, "commitMethod": "keyboard-text-fill", "scr04c_methods": typed.get("scr04c_methods")})
            continue
        clicked = cdp_click_points(url, [point])
        if not clicked.get("ok"):
            return {"ok": False, "point": point, **clicked}
        time.sleep(0.3)
        typed = cdp_type_points(url, [{"x": point["x"], "y": point["y"], "text": HEAR_ABOUT_TEXT_DEFAULT}])
        if not typed.get("ok"):
            return {"ok": False, "point": point, **typed}
        clicked_points.append({**point, "commitMethod": "cdp-type-text-fill"})
        time.sleep(0.4)
    if click_targets:
        batch = cdp_click_boolean_batch(url, window, tab, click_targets)
        if not batch.get("ok"):
            return batch
        clicked_points.extend(batch.get("points") or [])
    for point in combobox_targets:
        clicked = cdp_click_points(url, [point])
        if not clicked.get("ok"):
            return {"ok": False, "point": point, **clicked}
        time.sleep(0.5)
        typed = cdp_type_points(url, [{"x": point["x"], "y": point["y"], "text": HEAR_ABOUT_TEXT_DEFAULT}])
        if not typed.get("ok"):
            return {"ok": False, "point": point, **typed}
        time.sleep(0.8)
        option = js_eval("""
(() => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const opt = [...document.querySelectorAll('[role=option]')].find((el) => /linkedin|online|other|careers page|job board/i.test(clean(el.innerText || '')));
  if (!opt) return JSON.stringify({ok:false, code:'hear-about-option-not-found'});
  const r = opt.getBoundingClientRect();
  return JSON.stringify({ok:true, x:r.left + r.width / 2, y:r.top + r.height / 2, text:clean(opt.innerText || '')});
})()
""", window=window, tab=tab, timeout=15)
        if option.get("ok"):
            clicked = cdp_click_points(url, [option])
            if not clicked.get("ok"):
                return {"ok": False, "point": option, **clicked}
            clicked_points.append(option)
    js_pass = js_eval(f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + f"""
  const hearRx = /{HEAR_ABOUT_INLINE_RX}/i;
  const choices = {choices_js};
  const results = [];
  for (const entry of document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')) {{
    const text = clean(entry.innerText || '');
    const label = clean((entry.querySelector('label') || {{}}).innerText || '');
    if (!hearRx.test(text) && !hearRx.test(label)) continue;
    const entryError = /missing entry for required field|this field is required|please select an option/i.test(text.slice(0, 500));
    const textField = entry.querySelector('input[role=combobox], input[type=text], input[type=search], textarea, input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden])');
    if (textField) {{
      const current = clean(textField.value || '');
      const wanted = {hear_default_js};
      if (current.toLowerCase() === wanted.toLowerCase() && !entryError) {{
        results.push({{ok:true, skipped:true, wanted:current, method:'text-already-filled'}});
        continue;
      }}
      textField.focus();
      const proto = textField instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) setter.call(textField, wanted); else textField.value = wanted;
      textField.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: wanted }}));
      textField.dispatchEvent(new Event('change', {{ bubbles: true }}));
      textField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
      const committed = clean(textField.value || '').toLowerCase() === wanted.toLowerCase() && !/missing entry for required field/i.test(clean(entry.innerText || ''));
      if (committed) {{
        results.push({{ok:true, wanted, method:'text-fill-pass'}});
        continue;
      }}
    }}
    const selected = entry.querySelector('[aria-checked=true],[aria-selected=true],[data-state=checked],input[type=radio]:checked');
    if (selected && !entryError) {{
      results.push({{ok:true, skipped:true, wanted: clean((selected.innerText || selected.value || '')).slice(0, 40)}});
      continue;
    }}
    let committed = false;
    for (const choice of choices) {{
      const btn = findChoiceControl(entry, choice);
      if (!btn) continue;
      btn.scrollIntoView({{block:'center'}});
      btn.click();
      btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles:true}}));
      btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles:true}}));
      btn.dispatchEvent(new MouseEvent('click', {{bubbles:true}}));
      commitBooleanEntry(entry, choice);
      const stillMissing = /missing entry for required field/i.test(clean(entry.innerText || ''));
      const nowSelected = entry.querySelector('[aria-checked=true],[aria-selected=true],[data-state=checked],input[type=radio]:checked');
      if (nowSelected && !stillMissing) {{
        committed = true;
        results.push({{ok:true, wanted:choice, method:'js-commit-pass'}});
        break;
      }}
    }}
    if (!committed) {{
      const fallbackTextField = entry.querySelector('input[type=text], textarea, input[role=combobox], input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden])');
      if (fallbackTextField) {{
        const next = {hear_default_js};
        fallbackTextField.focus();
        const proto = fallbackTextField instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
        if (setter) setter.call(fallbackTextField, next); else fallbackTextField.value = next;
        fallbackTextField.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: next }}));
        fallbackTextField.dispatchEvent(new Event('change', {{ bubbles: true }}));
        fallbackTextField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        if (clean(fallbackTextField.value || '').toLowerCase() === next.toLowerCase()) {{
          committed = true;
          results.push({{ok:true, wanted:next, method:'text-fill-pass'}});
        }}
      }}
    }}
    if (!committed) {{
      const fallbackBtn = [...entry.querySelectorAll('button,[role=radio],label')].find((node) => /linkedin|online|other|job board|careers|social media|referral|friend|search engine/i.test(clean(node.innerText || node.value || '')));
      if (fallbackBtn) {{
        fallbackBtn.click();
        commitBooleanEntry(entry, clean(fallbackBtn.innerText || fallbackBtn.value || 'LinkedIn'));
        committed = !/missing entry for required field/i.test(clean(entry.innerText || ''));
        if (committed) results.push({{ok:true, wanted: clean(fallbackBtn.innerText || ''), method:'fallback-click-pass'}});
      }}
    }}
    if (!committed) results.push({{ok:false, text:text.slice(0,120)}});
  }}
  return JSON.stringify({{ok: results.length === 0 || results.every((row) => row.ok !== false), results}});
}})()
""", window=window, tab=tab, timeout=20)
    soft_fails = sum(
        1
        for point in clicked_points
        if point.get("softFail") or point.get("commitMethod") == "uncommitted"
    )
    final_verify = js_eval(f"""
(() => {{
  const text = document.body ? document.body.innerText : '';
  const missing = (text.match(/Missing entry for required field: ([^\\n]+)/gi) || [])
    .map((line) => line.replace(/Missing entry for required field:/i, '').trim())
    .filter((label) => /{HEAR_ABOUT_INLINE_RX}/i.test(label));
  return JSON.stringify({{ok: missing.length === 0, missing, softFails: {soft_fails}}});
}})()
""", window=window, tab=tab, timeout=15)
    ok = bool(final_verify.get("ok"))
    return {
        "ok": ok,
        "clicked": len(clicked_points),
        "points": clicked_points,
        "js_pass": js_pass,
        "final_verify": final_verify,
        "softFails": soft_fails,
    }


def trusted_select_location(url: str, window: int, tab: int | None = None) -> dict:
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const profileCountry = process.argv[2] || 'United States';
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const queryTexts = ['San Francisco Bay Area', 'United States', 'Remote', 'San Francisco'];
const preferred = [
  /^San Francisco Bay Area, California, United States$/i,
  /^San Francisco, California, United States$/i,
  /^Remote(,|\s|$)/i,
  /^United States$/i,
];
const countryQueryTexts = [profileCountry, 'United States'];
const countryPreferred = [/^United States$/i, new RegExp('^' + profileCountry.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$', 'i')];
const pickOption = (options, rxList) => {
  for (const rx of rxList) {
    const hit = options.find((opt) => rx.test(opt.text));
    if (hit) return hit;
  }
  return options.find((opt) => /United States|San Francisco|Bay Area|Remote/i.test(opt.text)) || null;
};
const fillCombobox = async (entryRx, queryList, preferredList, evalJson, domClickAt, Input) => {
  const loc = await evalJson(`JSON.stringify((() => {
    const entry = [...document.querySelectorAll('.ashby-application-form-field-entry,[data-field-entry-id]')]
      .find((el) => ${entryRx}.test(el.innerText || '') && el.querySelector('input[role=combobox]'));
    if (!entry) return {ok:false, code:'combobox-not-found'};
    const input = entry.querySelector('input[role=combobox]');
    input.scrollIntoView({block:'center'});
    input.focus();
    const r = input.getBoundingClientRect();
    return {ok:true, x:r.left + r.width / 2, y:r.top + r.height / 2};
  })())`);
  if (!loc.ok) return null;
  let chosen = null;
  let state = {selected: ''};
  for (const queryText of queryList) {
    await domClickAt(loc.x, loc.y);
    await evalJson(`JSON.stringify((() => {
      const entry = [...document.querySelectorAll('.ashby-application-form-field-entry,[data-field-entry-id]')]
        .find((el) => ${entryRx}.test(el.innerText || '') && el.querySelector('input[role=combobox]'));
      const input = entry && entry.querySelector('input[role=combobox]');
      if (!input) return {ok:false, code:'input-not-found'};
      input.focus();
      input.value = '';
      input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward', data: null }));
      return {ok:true};
    })())`);
    await sleep(200);
    if (Input && Input.insertText) await Input.insertText({text: queryText});
    await sleep(2200);
    const options = await evalJson(`JSON.stringify((() => {
      const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
      return [...document.querySelectorAll('[role=option]')].map((el) => {
        const r = el.getBoundingClientRect();
        return {text: clean(el.innerText || ''), x:r.left + r.width / 2, y:r.top + r.height / 2};
      });
    })())`);
    chosen = pickOption(options, preferredList);
    if (!chosen) continue;
    await domClickAt(chosen.x, chosen.y);
    await sleep(900);
    state = await evalJson(`JSON.stringify((() => {
      const entry = [...document.querySelectorAll('.ashby-application-form-field-entry,[data-field-entry-id]')]
        .find((el) => ${entryRx}.test(el.innerText || '') && el.querySelector('input[role=combobox]'));
      const input = entry && entry.querySelector('input[role=combobox]');
      return {ok:true, selected: input ? input.value : ''};
    })())`);
    state.chosen = chosen;
    const selected = state.selected || '';
    if (/Dominican|Brazil|Argentina|Ireland|Ivory Coast|Germany|Canada|Mexico/i.test(selected) && !/United States/i.test(selected)) {
      chosen = null;
      continue;
    }
    if (/United States|San Francisco|Bay Area|Remote/i.test(selected) || selected === profileCountry) break;
    chosen = null;
  }
  return chosen ? state : null;
};
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime, Input} = client;
    const evalJson = async (expression) => {
      const res = await Runtime.evaluate({expression, returnByValue: true, awaitPromise: true});
      return JSON.parse(res.result.value);
    };
    const domClickAt = async (x, y) => evalJson(`JSON.stringify((() => {
      const el = document.elementFromPoint(${x}, ${y});
      if (!el) return {ok:false, code:'click-target-not-found', x:${x}, y:${y}};
      const btn = el.closest('button,[role=button],[role=option],label,input') || el;
      btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      return {ok:true};
    })())`);
    const filled = [];
    const locationState = await fillCombobox(/(^|\\b)location(\\b|$)/i, queryTexts, preferred, evalJson, domClickAt, Input);
    if (locationState) filled.push({field: 'location', ...locationState});
    const desiredLocationState = await fillCombobox(/desired location|location for employment/i, queryTexts, preferred, evalJson, domClickAt, Input);
    if (desiredLocationState) filled.push({field: 'desired-location', ...desiredLocationState});
    const countryState = await fillCombobox(/passport country|country of residence|country.*residence|nationality/i, countryQueryTexts, countryPreferred, evalJson, domClickAt, Input);
    if (countryState) filled.push({field: 'country', ...countryState});
    if (!filled.length) {
      process.stdout.write(JSON.stringify({ok:false, code:'location-combobox-not-found', options: []}) + '\n');
      return;
    }
    const last = filled[filled.length - 1];
    process.stdout.write(JSON.stringify({ok:true, filled, selected: last.selected, chosen: last.chosen}) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id, PROFILE_COUNTRY],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-location-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-location-bad-json", "stdout": proc.stdout[:500]}


def reinforce_core_fields(url: str, window: int, tab: int | None = None) -> dict:
    hear_about = reinforce_hear_about_choice(url, window, tab=tab)
    if not hear_about.get("ok"):
        return {"ok": False, "code": "hear-about-reinforce-failed", "hear_about": hear_about}
    phone_json = json.dumps(APPLICATION_PHONE)
    entries_js = [
        "{selector:'input[name=\"_systemfield_name\"]', text:'Yupeng Lu', label:'Name'}",
        "{selector:'input[name=\"_systemfield_email\"]', text:'yplmicro@gmail.com', label:'Email'}",
    ]
    if APPLICATION_PHONE:
        entries_js.append(
            f"{{selector:'input[name*=\"phone\" i], input[id*=\"phone\" i], input[type=tel]', text:{phone_json}, label:'Phone'}}"
        )
    entries_js_literal = ",\n    ".join(entries_js)
    targets = js_eval(f"""
(() => {{
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const labelFor = (el) => {{
    let byFor = null;
    try {{
      byFor = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    }} catch (_) {{}}
    return clean((el.closest('label') || byFor || el.parentElement || {{}}).innerText || el.getAttribute('aria-label') || el.placeholder || '');
  }};
  const profileLinkedIn = {json.dumps(PROFILE_LINKEDIN)};
  const profileGithubUsername = {json.dumps(PROFILE_GITHUB_USERNAME)};
  const profileFirstName = {json.dumps(PROFILE_FIRST_NAME)};
  const profileLastName = {json.dumps(PROFILE_LAST_NAME)};
  const hearAboutDefault = {json.dumps(HEAR_ABOUT_TEXT_DEFAULT)};
  const profileLocation = {json.dumps(PROFILE_LOCATION)};
  const locationTextForProbe = (probe) => {{
    const s = probe || '';
    if (/desired location|location for employment/i.test(s)) return 'Remote, United States';
    if (/^current location$/i.test(s.trim()) || /where are you currently located/i.test(s)) return 'San Francisco Bay Area, CA';
    if (/current location|currently residing|currently located|where.*located/i.test(s)) return 'San Francisco Bay Area, CA';
    return '';
  }};
  const entries = [
    {entries_js_literal}
  ].filter((entry) => document.querySelector(entry.selector));
  const fieldSelector = (field, entry) => {{
    if (field.id) return '#' + CSS.escape(field.id);
    if (field.name) return 'input[name="' + CSS.escape(field.name) + '"], textarea[name="' + CSS.escape(field.name) + '"]';
    const entryId = entry && entry.getAttribute('data-field-entry-id');
    if (entryId) {{
      return '[data-field-entry-id="' + CSS.escape(entryId) + '"] input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden]), [data-field-entry-id="' + CSS.escape(entryId) + '"] textarea';
    }}
    return null;
  }};
  const isCurrentLocationCombobox = (field, entry, label) => {{
    const probe = label || clean((entry && entry.innerText) || '').slice(0, 120);
    const isCombo = field.getAttribute('role') === 'combobox';
    return isCombo && (/^current location$/i.test(probe.trim()) || /where are you currently located/i.test(probe));
  }};
  const pushEntry = (field, entry, text, label) => {{
    const linkedInField = /linkedin profile|linkedin url|linkedin link|please provide.*linkedin|linkedin.*below|^linkedin\\b/i.test(label);
    const hearAboutField = /{HEAR_ABOUT_INLINE_RX}/i.test(label);
    if (!text) return;
    if (!linkedInField && !hearAboutField && field.value && field.value.trim()) return;
    const sel = fieldSelector(field, entry);
    if (!sel || seenSelectors.has(sel)) return;
    seenSelectors.add(sel);
    const kind = isCurrentLocationCombobox(field, entry, label) ? 'location-combobox' : 'text';
    const comboText = kind === 'location-combobox' ? 'San Francisco Bay Area' : text;
    entries.push({{kind, selector: sel, text: comboText, label: label || labelFor(field)}});
  }};
  const seenSelectors = new Set(entries.map((entry) => entry.selector));
  for (const entry of document.querySelectorAll('.ashby-application-form-field-entry, [data-field-entry-id]')) {{
    const entryLabel = clean((entry.querySelector('label') || {{}}).innerText || '');
    const entryProbe = entryLabel || clean(entry.innerText || '').slice(0, 180);
    const field = entry.querySelector('input[type=text], input[type=search], input[type=url], textarea, [role=combobox], input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=hidden])');
    if (!field) continue;
    let text = '';
    if (/{HEAR_ABOUT_INLINE_RX}/i.test(entryProbe)) {{
      text = hearAboutDefault;
    }} else if (/^first name$/i.test(entryProbe.trim())) {{
      text = profileFirstName;
    }} else if (/^last name$/i.test(entryProbe.trim())) {{
      text = profileLastName;
    }} else if (/linkedin profile|linkedin url|linkedin link|please provide.*linkedin|linkedin.*below|^linkedin\\b/i.test(entryProbe)) {{
      text = profileLinkedIn;
    }} else if (/github\\s*username|github\\s*handle|github\\s*user\\s*name|what is your github/i.test(entryProbe)) {{
      text = profileGithubUsername;
    }} else {{
      text = locationTextForProbe(entryProbe);
    }}
    pushEntry(field, entry, text, entryProbe);
  }}
  for (const field of document.querySelectorAll('input[type=text], input[type=search], input[type=url], textarea, [role=combobox], input[id][name]')) {{
    const label = labelFor(field);
    let text = '';
    if (/{HEAR_ABOUT_INLINE_RX}/i.test(label)) {{
      text = hearAboutDefault;
    }} else if (/^first name$/i.test(label.trim())) {{
      text = profileFirstName;
    }} else if (/^last name$/i.test(label.trim())) {{
      text = profileLastName;
    }} else if (/linkedin profile|linkedin url|linkedin link|please provide.*linkedin|linkedin.*below|^linkedin\\b/i.test(label)) {{
      text = profileLinkedIn;
    }} else if (/github\\s*username|github\\s*handle|github\\s*user\\s*name|what is your github/i.test(label)) {{
      text = profileGithubUsername;
    }} else {{
      text = locationTextForProbe(label);
    }}
    pushEntry(field, field.closest('.ashby-application-form-field-entry, [data-field-entry-id]'), text, label);
  }}
  return JSON.stringify({{ok:true, entries}});
}})()
""", window=window, tab=tab, timeout=20)
    if not targets.get("ok"):
        return targets
    typed_entries = []
    for entry in targets.get("entries") or []:
        point = js_eval(f"""
(() => {{
  const el = document.querySelector({json.dumps(entry['selector'])});
  if (!el) return JSON.stringify({{ok:false, code:'field-not-found'}});
  el.scrollIntoView({{block:'center'}});
  const r = el.getBoundingClientRect();
  return JSON.stringify({{ok:true, x:r.left + r.width / 2, y:r.top + r.height / 2, text:{json.dumps(entry['text'])}, label:{json.dumps(entry.get('label', ''))}, selector:{json.dumps(entry['selector'])}}});
}})()
""", window=window, tab=tab, timeout=20)
        if not point.get("ok"):
            return {"ok": False, "entry": entry, **point}
        label = entry.get("label") or point.get("label") or ""
        keyboard_entry = {"selector": entry["selector"], "text": entry["text"], "label": label}
        already = js_eval(f"""
(() => {{
  const el = document.querySelector({json.dumps(entry['selector'])});
  if (!el || !('value' in el)) return JSON.stringify({{ok:true, skip:false}});
  const current = String(el.value || '').trim();
  const wanted = {json.dumps(entry['text'])}.trim();
  return JSON.stringify({{ok:true, skip: current === wanted, current}});
}})()
""", window=window, tab=tab, timeout=10)
        if already.get("skip"):
            typed_entries.append({**point, "scr04c_methods": ["skip-already-filled"]})
            time.sleep(0.1)
            continue
        if entry.get("kind") == "location-combobox":
            typed = cdp_combobox_type_arrow_enter(url, entry["selector"], entry["text"], label=label)
        elif LINKEDIN_FIELD_LABEL_RX.search(label) or HEAR_ABOUT_LABEL_RX.search(label):
            typed = cdp_keyboard_type_entries(url, [keyboard_entry])
        else:
            typed = cdp_type_points(url, [point])
            if not typed.get("ok") and typed.get("code") == "type-target-not-found":
                typed = cdp_keyboard_type_entries(url, [keyboard_entry])
        if not typed.get("ok"):
            return {"ok": False, "entry": entry, "point": point, **typed}
        typed_entries.append({**point, "scr04c_methods": typed.get("scr04c_methods")})
        time.sleep(0.25)
    scr04c_methods = []
    for item in typed_entries:
        scr04c_methods.extend(item.get("scr04c_methods") or [])
    if scr04c_methods:
        log_scr04c(f"reinforce_core_fields methods={scr04c_methods}")
    return {"ok": True, "typed": len(typed_entries), "targets": typed_entries, "scr04c_methods": scr04c_methods}


def tracker_rows() -> tuple[list[dict], list[str]]:
    rows = list(csv.DictReader(TRACKER.open(newline="", encoding="utf-8"))) if TRACKER.exists() else []
    fields = list(rows[0].keys()) if rows else [
        "Date", "Company", "Role", "JD_URL", "Channel", "Referrer_Name", "Referrer_LinkedIn",
        "Message_Sent", "Application_Submitted", "Response_Status", "Stage", "Last_Updated", "Notes",
    ]
    return rows, fields


def record(company: str, role: str, url: str, status: str, notes: str, submitted: bool, variant: str) -> None:
    stamp = now_cst()
    rows, fields = tracker_rows()
    base = norm_url(url)
    idx = next((i for i, row in enumerate(rows) if norm_url(row.get("JD_URL", "")) == base), None)
    data = {
        "Date": stamp,
        "Company": company,
        "Role": role,
        "JD_URL": base,
        "Channel": "Ashby Direct",
        "Referrer_Name": "",
        "Referrer_LinkedIn": "",
        "Message_Sent": "No",
        "Application_Submitted": "Yes" if submitted else "No",
        "Response_Status": status,
        "Stage": status,
        "Last_Updated": stamp,
        "Notes": f"{notes}; resume={variant}",
    }
    if idx is None:
        rows.append(data)
    else:
        rows[idx].update({k: v for k, v in data.items() if k in rows[idx]})
    with TRACKER.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(f"- {stamp} | {status} | {company} - {role} | {base} | {notes}; resume={variant}\n")
    if submitted:
        sh([
            "python3", str(SKILL / "scripts/job_archive.py"), "emit",
            "--channel", "Ashby Direct", "--date", today(), "--status", "Submitted",
            "--company", company, "--role", role, "--jd-url", base,
        ], timeout=60)


def fill_page(resume: Path, window: int, allow_auth_boolean: bool, tab: int | None = None, url: str = "") -> dict:
    b64 = base64.b64encode(resume.read_bytes()).decode()
    js = f"""
(() => {{
  const b64 = {json.dumps(b64)};
  const resumeName = {json.dumps(resume.name)};
  const allowAuthBoolean = {str(allow_auth_boolean).lower()};
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
""" + BOOLEAN_MATCH_JS + f"""
  const text = clean(document.body ? document.body.innerText : '');
  const danger = /possible spam|error verifying|verify your application|unusual traffic|automated|are you a robot|too many attempts|hcaptcha challenge|phone verification|sms verification/i.test(text);
  const stale = /job.*not found|not found|no longer accepting|position has been closed|job is no longer available/i.test(text);
  if (danger || stale) return JSON.stringify({{ok:false, code: danger ? 'danger-text' : 'stale-job', danger, stale, text:text.slice(0,1200), url:location.href, title:document.title}});
  const fire = (el) => {{
    el.dispatchEvent(new InputEvent('input', {{bubbles:true, inputType:'insertText', data: el.value || ''}}));
    el.dispatchEvent(new Event('change', {{bubbles:true}}));
    el.dispatchEvent(new Event('blur', {{bubbles:true}}));
  }};
  const labelFor = (el) => {{
    let byFor = null;
    try {{
      byFor = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    }} catch (_) {{}}
    return clean((el.closest('label') || byFor || el.parentElement || {{}}).innerText || el.getAttribute('aria-label') || el.placeholder || '');
  }};
  const directLocationPrompt = (s) => /current location|currently residing|currently located|where are you currently located|current residence|current country|tax residence|where.*based|where.*located|city,\\s*country|country.*currently|city.*state|state.*city|city,\\s*state|passport country|country of residence|nationality|desired location|location for employment/i.test(s || '');
  const authenticShortTextSkip = (s) => /favorite video game|favourite video game|most played game|video game you/i.test(s || '');
  const profileLinkedIn = {json.dumps(PROFILE_LINKEDIN)};
  const profileGithub = {json.dumps(PROFILE_GITHUB)};
  const profileGithubUsername = {json.dumps(PROFILE_GITHUB_USERNAME)};
  const profileLocation = {json.dumps(PROFILE_LOCATION)};
  const profileCountry = {json.dumps(PROFILE_COUNTRY)};
  const profileWorkAuth = {json.dumps(PROFILE_WORK_AUTH)};
  const profileSummary = {json.dumps(PROFILE_SUMMARY)};
  const profileCompany = {json.dumps(PROFILE_COMPANY)};
  const profileEmployer = {json.dumps(PROFILE_EMPLOYER)};
  const profileTitle = {json.dumps(PROFILE_TITLE)};
  const employerCompanyPrompt = (s) => /current(?:\\s*[\\/|,]\\s*(?:last|most recent))?\\s*company(?:\\s*name)?|(?:most recent|last)\\s*company(?:\\s*name)?|current employer|most recent employer|recent employer|current or (?:most )?recent employer|current or previous employer/i.test(s || '');
  const employerTitlePrompt = (s) => /current(?:\\s*[\\/|,]\\s*last)?\\s*(?:job\\s*)?title|last (?:job )?title|most recent (?:job )?title|recent (?:job )?title|current position|current role/i.test(s || '');
  const answerRequiredText = (label, tagName) => {{
    const text = label || '';
    if (authenticShortTextSkip(text)) return '';
    if (/passport country|country of residence|nationality/i.test(text)) return profileCountry;
    if (/linkedin profile|linkedin url|linkedin link|please provide.*linkedin|linkedin.*below/i.test(text)) return profileLinkedIn;
    if (/research paper|publications or papers|google scholar|arxiv|research output/i.test(text)) return 'N/A';
    if (/typescript.*server|server.?side.*typescript/i.test(text)) {{
      return 'Yes — I have used TypeScript extensively on the server side in NestJS/Node.js production backends, not only frontend work.';
    }}
    if (/learn about|hear about|where did you (find|hear)|source/i.test(text)) return 'Company careers page';
    if (/work authorization|authorized.*work|sponsor|sponsorship/i.test(text)) return profileWorkAuth;
    if (/city.*state|state.*city|city,\\s*state/i.test(text)) return 'San Francisco, California';
    if (/career accomplishments|accomplishments.*proud|proud to share/i.test(text)) {{
      return 'I am proud of building production AI/backend platform systems with contract-driven APIs, streaming workflows, tool integrations, and reliability guardrails across web, API, and agent surfaces. I have also shipped evidence-linked AI report workflows and operational tooling that made long-running automations easier to audit and safer to release.';
    }}
    if (/LLM|large language model|limitations|tried to get working technically/i.test(text)) {{
      return 'I have built LLM and tool-use workflows where the hard parts were grounding, schema drift, latency, streaming failure modes, and tool-result validation. The main limitation I found is that free-form generation is not enough for production systems; I handle that with structured schemas, scoped tools, evidence packets, timeouts, retries, and human-auditable traces.';
    }}
    if (/why.*perplexity|why perplexity/i.test(text)) {{
      return 'Perplexity is compelling because it combines search, inference, and product velocity in a way that needs strong backend and AI infrastructure. The role matches my experience building production agent systems, API contracts, and reliable AI workflows.';
    }}
    if (/most interesting aspects of perplexity|excited to work on/i.test(text)) {{
      return 'I am most excited by Perplexity work at the intersection of retrieval, inference, and product-facing AI systems: making answers fast, grounded, and reliable at scale through strong backend infrastructure, evaluation, and observability.';
    }}
    if (/how do you use ai in your day-to-day/i.test(text)) {{
      return 'I use AI daily for backend and agent workflow development: schema-first tool contracts, retrieval/evaluation loops, debugging production LLM workflows, and building automation with clear guardrails rather than unconstrained generation.';
    }}
    if (/underappreciated benefits|pain points of your favorite ai tools/i.test(text)) {{
      return 'A useful benefit is fast iteration on structured workflows; an underappreciated pain point is hidden state drift between prompts, tools, and UI validation, which is why I prefer explicit schemas, traces, and release checks in production AI systems.';
    }}
    if (/come into the office four days|office four days per week/i.test(text)) return 'Yes';
    if (/why\\s+typesafe|why this company|why.*company|why.*role/i.test(text)) {{
      return 'The company is compelling because it is building developer infrastructure around reliable AI and data systems. The role matches my backend/platform focus: data infrastructure, production-grade automation, and making AI workflows predictable, observable, and auditable.';
    }}
    if (/why.*apply|interest.*role|why.*interested/i.test(text)) {{
      return 'I am interested because the role aligns with my work on backend platform reliability, AI tool workflows, and production systems that need clear contracts, observability, and safe automation.';
    }}
    if (/technical project|complex project|hard.*technical|most challenging/i.test(text)) {{
      return 'A recent complex project involved hardening AI workflow and reporting infrastructure across API, streaming, and tool-use boundaries. I focused on schema validation, scoped tool contracts, evidence binding, streaming cleanup, and release verification so the system could remain auditable under changing product requirements.';
    }}
    if (/years of experience|years.*experience/i.test(text)) return '5+';
    if (tagName === 'TEXTAREA') {{
      return profileSummary || 'My strongest fit is backend and AI platform engineering: contract-driven APIs, reliable streaming workflows, tool integration, data-backed automation, and production systems with clear observability and release guardrails.';
    }}
    return '';
  }};
  const nativeSet = (selector, value) => {{
    const el = document.querySelector(selector);
    if (!el) return false;
    el.scrollIntoView({{block:'center'}});
    el.focus();
    if (typeof el.select === 'function') el.select();
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, value);
    fire(el);
    return el.value === value;
  }};
  const set = (selector, value) => {{
    const el = document.querySelector(selector);
    if (!el) return false;
    if (nativeSet(selector, value)) return true;
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    fire(el);
    return true;
  }};
  const clickChoice = (entry, wanted) => {{
    const btn = findChoiceControl(entry, wanted);
    if (!btn) return false;
    btn.scrollIntoView({{block:'center'}});
    btn.click();
    btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles:true}}));
    btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles:true}}));
    btn.dispatchEvent(new MouseEvent('click', {{bubbles:true}}));
    commitBooleanEntry(entry, wanted);
    return true;
  }};
  const fillEmployerCompanyField = (field) => {{
    if (!field || field.value) return false;
    const label = labelFor(field);
    if (!employerCompanyPrompt(label)) return false;
    const proto = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) setter.call(field, profileEmployer);
    else field.value = profileEmployer;
    fire(field);
    return field.value === profileEmployer;
  }};
  set('input[name="_systemfield_name"]', 'Yupeng Lu');
  set('input[name="_systemfield_email"]', 'yplmicro@gmail.com');
  const profileFirstName = {json.dumps(PROFILE_FIRST_NAME)};
  const profileLastName = {json.dumps(PROFILE_LAST_NAME)};
  if ({json.dumps(bool(APPLICATION_PHONE))}) {{
    set('input[name*="phone" i], input[id*="phone" i], input[type=tel]', {json.dumps(APPLICATION_PHONE)});
  }}
  set('input[name*="linkedin" i], input[id*="linkedin" i]', profileLinkedIn);
  set('input[name*="company" i], input[id*="company" i]', profileEmployer);
  for (const field of document.querySelectorAll('input[type=text], input[type=url], textarea')) {{
    fillEmployerCompanyField(field);
  }}
  const fillIfEmpty = (field, value) => {{
    if (!field || !value || field.value) return false;
    field.scrollIntoView({{block:'center'}});
    field.focus();
    if (typeof field.select === 'function') field.select();
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, value);
    const proto = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) setter.call(field, value);
    else field.value = value;
    fire(field);
    return field.value === value || clean(field.value).includes(clean(value).slice(0, 12));
  }};
  for (const field of document.querySelectorAll('input[type=text], input[type=url], textarea')) {{
    const label = labelFor(field);
    if (/^first name$/i.test(label.trim()) && !field.value.trim()) {{
      fillIfEmpty(field, profileFirstName);
    }} else if (/^last name$/i.test(label.trim()) && !field.value.trim()) {{
      fillIfEmpty(field, profileLastName);
    }} else if (/{HEAR_ABOUT_INLINE_RX}/i.test(label)) {{
      fillIfEmpty(field, 'LinkedIn');
    }} else if (/linkedin profile|linkedin url|linkedin link|please provide.*linkedin|linkedin.*below|^linkedin\\b/i.test(label)) {{
      fillIfEmpty(field, profileLinkedIn);
    }} else if (/github\\s*username|github\\s*handle|github\\s*user\\s*name|what is your github/i.test(label)) {{
      fillIfEmpty(field, profileGithubUsername);
    }}
  }}
  const locationTextValue = (label) => {{
    const probe = label || '';
    if (/desired location|location for employment/i.test(probe)) return 'Remote, United States';
    if (/^current location$/i.test(probe.trim()) || /where are you currently located/i.test(probe)) return 'San Francisco Bay Area, CA';
    if (directLocationPrompt(probe)) return /passport country|country of residence|nationality/i.test(probe) ? profileCountry : 'San Francisco Bay Area, CA';
    return '';
  }};
  for (const field of document.querySelectorAll('input[type=text], input[type=search], input[type=url], textarea')) {{
    if (field.getAttribute('role') === 'combobox') continue;
    const label = labelFor(field);
    const locValue = locationTextValue(label);
    if (locValue && !String(field.value || '').trim()) fillIfEmpty(field, locValue);
  }}
  for (const field of document.querySelectorAll('input[type=text], input[type=url], textarea')) {{
    if (!field.required || field.value) continue;
    const label = labelFor(field);
    let value = '';
    if (/work authorization|authorized.*work|sponsor|sponsorship/i.test(label)) {{
      value = profileWorkAuth;
    }} else if (/linkedin/i.test(label)) {{
      value = profileLinkedIn;
    }} else if (/github\\s*username|github\\s*handle|github\\s*user\\s*name|what is your github/i.test(label)) {{
      value = profileGithubUsername;
    }} else if (/portfolio|github url|github profile|website|links?/i.test(label)) {{
      value = profileGithub;
    }} else if (/college|university|school|education/i.test(label)) {{
      value = 'Boston University; The Ohio State University';
    }} else if (/{HEAR_ABOUT_INLINE_RX}|source/i.test(label)) {{
      value = 'Company careers page';
    }} else if (field.type === 'url') {{
      value = 'https://github.com/BrickerP';
    }} else if (employerCompanyPrompt(label)) {{
      value = profileEmployer;
    }} else if (employerTitlePrompt(label)) {{
      value = profileTitle;
    }} else if (/desired location|location for employment/i.test(label)) {{
      value = 'Remote, United States';
    }} else if (directLocationPrompt(label)) {{
      value = /passport country|country of residence|nationality/i.test(label) ? profileCountry : 'San Francisco Bay Area, CA';
    }} else if (authenticShortTextSkip(label)) {{
      value = '';
    }} else {{
      value = answerRequiredText(label, field.tagName);
    }}
    if (value) {{
      const proto = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) setter.call(field, value);
      else field.value = value;
      fire(field);
    }}
  }}
  let uploaded = false;
  const fileInput = document.querySelector('input[type=file]#_systemfield_resume') || document.querySelector('input[type=file]');
  if (fileInput) {{
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const file = new File([bytes], resumeName, {{type:'application/pdf', lastModified:Date.now()}});
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fire(fileInput);
    uploaded = fileInput.files && fileInput.files.length > 0;
  }}
  if (allowAuthBoolean) {{
    const booleanRules = [
      [/what is your work authorization|work authorization status/i, statusStyleChoices],
      [/authorized to work|legally authorized|eligible to work|authorized to work in the country|authorization to work/i, ['Yes', ...statusStyleChoices]],
      [/sponsor|sponsorship|require.*visa|future.*visa|immigration-related|immigration related support/i, ['No']],
      [/relocate|relocation|willing to move|willing to relocate/i, ['Yes']],
      [/disqualif|denied.*clearance|terminated.*cause|convicted|felony/i, ['No']],
      [/consent.*background|agree.*background|authorize.*background/i, ['Yes']],
      [/previously employed|previously employed by|worked at .* before|employed by.*(?:Plaid|Quovo|Cognito)/i, ['No']],
      [/consent to receiving text|text message updates from/i, ['No']],
      [/agree to|i agree|acknowledge|accept the terms/i, ['Yes']],
      [/{HEAR_ABOUT_INLINE_RX}/i, ['LinkedIn', 'Online', 'Other', 'Company careers page', 'Company website', 'Job board']],
    ];
    for (const entry of fieldEntries()) {{
      const question = authQuestionText(entry);
      let wanted = resolveAuthWanted(entry, question) || resolveBooleanWanted(question);
      if (!wanted) {{
        for (const [rx, wantedChoices] of booleanRules) {{
          if (!rx.test(question)) continue;
          for (const choice of wantedChoices) {{
            if (clickChoice(entry, choice)) {{ wanted = choice; break; }}
          }}
          if (wanted) break;
        }}
      }} else {{
        clickChoice(entry, wanted);
      }}
    }}
    for (const input of document.querySelectorAll('input[type=radio], input[type=checkbox]')) {{
      const label = clean((input.closest('label') || input.parentElement || {{}}).innerText || input.value || '');
      const block = clean((input.closest('[data-testid], fieldset, form') || input.parentElement || {{}}).innerText || '');
      const combined = label + ' ' + block;
      if (/authorized to work|legally authorized|authorized to work in the country/i.test(combined) && /^yes\\b/i.test(label || input.value || '')) {{
        input.checked = true; fire(input);
      }}
      if (/sponsor|sponsorship|require.*visa|future.*visa/i.test(combined) && /^no\\b/i.test(label || input.value || '')) {{
        input.checked = true; fire(input);
      }}
    }}
    for (const entry of fieldEntries()) {{
      const question = authQuestionText(entry);
      if (!/legally authorized to work in the united states|authorized to work in the united states/i.test(question)) continue;
      const wanted = resolveAuthWanted(entry, question) || 'Yes';
      clickChoice(entry, wanted);
    }}
  }}
  return JSON.stringify({{ok:true, uploaded, danger:false, stale:false, url:location.href, title:document.title}});
}})()
"""
    first = js_eval(js, window=window, tab=tab, timeout=45)
    if not first.get("ok"):
        return first
    cdp_url = first.get("url") or app_url(url)
    file_upload = cdp_set_file_input(cdp_url, resume)
    if not file_upload.get("ok") and file_upload.get("code") not in {"file-input-not-found", "cdp-target-not-found"}:
        log_scr04h(f"cdp_set_file_input soft-fail code={file_upload.get('code')} path={file_upload.get('path')} — retry once after 3s")
        file_upload = retry_resume_upload(cdp_url, resume)
        if not file_upload.get("ok"):
            log_scr04h(f"cdp_set_file_input retry still failed code={file_upload.get('code')} — continuing to boolean/validation")
    location = trusted_select_location(cdp_url, window, tab=tab)
    location_soft_fail = {"location-combobox-not-found", "location-option-not-found"}
    if not location.get("ok") and location.get("code") not in location_soft_fail:
        return {"ok": False, "code": "cdp-location-select-failed", "location": location, "url": first.get("url"), "title": first.get("title")}
    extended = trusted_click_extended_booleans(cdp_url, window, tab=tab)
    if not extended.get("ok"):
        return {"ok": False, "code": "cdp-extended-boolean-failed", "extended": extended, "url": first.get("url"), "title": first.get("title")}
    sponsorship = reinforce_sponsorship_boolean(cdp_url, window, tab=tab)
    if not sponsorship.get("ok"):
        return {"ok": False, "code": "cdp-sponsorship-boolean-failed", "sponsorship": sponsorship, "url": first.get("url"), "title": first.get("title")}
    reinforced = reinforce_core_fields(first.get("url") or app_url(url), window, tab=tab)
    if not reinforced.get("ok"):
        return {"ok": False, "code": "cdp-field-reinforce-failed", "reinforced": reinforced, "url": first.get("url"), "title": first.get("title")}
    if file_upload.get("ok"):
        reinforced_after_upload = reinforce_core_fields(first.get("url") or app_url(url), window, tab=tab)
        if not reinforced_after_upload.get("ok"):
            return {"ok": False, "code": "cdp-field-reinforce-after-upload-failed", "reinforced": reinforced_after_upload, "url": first.get("url"), "title": first.get("title")}
    if allow_auth_boolean:
        trusted = trusted_click_auth_booleans(cdp_url, window, tab=tab)
        if not trusted.get("ok"):
            return {"ok": False, "code": "cdp-auth-click-failed-after-reinforce", "trusted": trusted, "url": first.get("url"), "title": first.get("title")}
        standard = trusted_click_standard_choices(cdp_url, window, tab=tab)
        if not standard.get("ok"):
            return {"ok": False, "code": "cdp-standard-choice-failed-after-reinforce", "standard": standard, "url": first.get("url"), "title": first.get("title")}
        extended = trusted_click_extended_booleans(cdp_url, window, tab=tab)
        if not extended.get("ok"):
            return {"ok": False, "code": "cdp-extended-boolean-failed-after-reinforce", "extended": extended, "url": first.get("url"), "title": first.get("title")}
        sponsorship = reinforce_sponsorship_boolean(cdp_url, window, tab=tab)
        if not sponsorship.get("ok"):
            return {"ok": False, "code": "cdp-sponsorship-boolean-failed-after-reinforce", "sponsorship": sponsorship, "url": first.get("url"), "title": first.get("title")}
    time.sleep(8)
    if page_has_resume_s3_error(window, tab=tab):
        s3_retry = retry_resume_upload(cdp_url, resume)
        log_scr04h(f"fill_page resume-s3-error detected; retry ok={s3_retry.get('ok')}")
        time.sleep(5)
    final_reinforced = reinforce_core_fields(first.get("url") or app_url(url), window, tab=tab)
    if not final_reinforced.get("ok"):
        return {"ok": False, "code": "cdp-final-field-reinforce-failed", "reinforced": final_reinforced, "url": first.get("url"), "title": first.get("title")}
    check = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const labelFor = (el) => {
    let byFor = null;
    try {
      byFor = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    } catch (_) {}
    return clean((el.closest('label') || byFor || el.parentElement || {}).innerText || el.getAttribute('aria-label') || el.placeholder || '');
  };
  const directLocationPrompt = (s) => /current location|currently residing|currently located|where are you currently located|current residence|current country|tax residence|where.*based|where.*located|city,\s*country|country.*currently|desired location|location for employment/i.test(s || '');
  const text = clean(document.body ? document.body.innerText : '');
  const invalid = [...document.querySelectorAll('input,textarea,select')]
    .filter(el => el.required && !el.checkValidity())
    .map(el => ({
      tag: el.tagName, type: el.type || '', name: el.name || '', id: el.id || '',
      msg: el.validationMessage || '',
      label: labelFor(el).slice(0,220)
    }));
  const phoneRequired = invalid.some(i => /phone/i.test(i.name + ' ' + i.id + ' ' + i.label));
  const manualLocationBlockers = invalid
    .filter(i => directLocationPrompt(i.name + ' ' + i.id + ' ' + i.label) || /(^|\\b)location(\\b|$)/i.test(i.name + ' ' + i.id))
    .map(i => i.label || i.name || i.id || 'required location field');
	  const files = [...document.querySelectorAll('input[type=file]')].map(i => ({id:i.id || '', count:i.files ? i.files.length : 0, names:[...(i.files || [])].map(f => f.name)}));
	  const submitButtons = [...document.querySelectorAll('button,input[type=submit]')]
	    .map(el => ({text: clean(el.innerText || el.value || ''), visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length), disabled: !!el.disabled}))
	    .filter(b => b.visible && /submit/i.test(b.text));
	  const systemFields = {
	    name: !!document.querySelector('input[name="_systemfield_name"]'),
	    email: !!document.querySelector('input[name="_systemfield_email"]'),
	    resume: !!document.querySelector('input[type=file]#_systemfield_resume, input[type=file]')
	  };
	  const uploaded = files.some(f => f.count > 0);
	  const formReady = text.length > 100 && (systemFields.name || systemFields.email || systemFields.resume || submitButtons.length > 0);
	  const missingEntries = (text.match(/Missing entry for required field: ([^\\n]+)/g) || [])
	    .map((line) => clean(line.replace(/Missing entry for required field:/i, '')));
	  const authenticShortTextMissing = missingEntries.filter((label) => /favorite video game|favourite video game|most played game|video game you/i.test(label));
	  const booleanMissing = missingEntries.filter((label) => !authenticShortTextMissing.includes(label));
	  const authenticShortTextInvalid = invalid.filter((i) => /favorite video game|favourite video game|most played game|video game you/i.test(i.label || ''));
	  let code;
	  if (authenticShortTextMissing.length && !booleanMissing.length && !invalid.length) code = 'manual-finish-needed:authentic-shorttext';
	  else if (authenticShortTextInvalid.length && authenticShortTextInvalid.length === invalid.length && !missingEntries.length) code = 'manual-finish-needed:authentic-shorttext';
	  else if (manualLocationBlockers.length) code = 'manual-finish-needed:current-location-residence-required';
	  else if (missingEntries.length) code = 'invalid-required-fields';
	  else if (phoneRequired) code = 'phone-required-no-active-number';
	  else if (!formReady) code = 'form-not-loaded';
	  else if (!submitButtons.length) code = 'submit-button-not-found';
	  else if (!uploaded && files.length) code = 'resume-upload-missing';
	  else if (invalid.length) code = 'invalid-required-fields';
	  return JSON.stringify({
	    ok: !code,
	    code,
	    uploaded,
	    files,
	    submitButtons,
	    systemFields,
	    formReady,
	    phoneRequired,
	    manualLocationBlockers,
	    missingEntries,
	    invalid,
    danger:/possible spam|error verifying|verify your application|unusual traffic|automated|are you a robot|too many attempts|hcaptcha challenge|phone verification|sms verification/i.test(text),
    stale:false,
    url:location.href,
    title:document.title,
    text:text.slice(0,1600)
  });
})()
""", window=window, tab=tab, timeout=30)
    missing = [str(x) for x in (check.get("missingEntries") or [])]
    auth_missing = [m for m in missing if re.search(r"authorized to work|legally authorized|eligible to work|work authorization|sponsorship", m, re.I)]
    if auth_missing:
        retry_url = cdp_url or first.get("url") or app_url(url)
        retry = reinforce_missing_work_auth_entries(retry_url, window, tab=tab)
        if retry.get("ok"):
            reinforce_pre_submit_auth_booleans(retry_url, window, tab=tab)
            check = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const labelFor = (el) => {
    let byFor = null;
    try {
      byFor = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    } catch (_) {}
    return clean((el.closest('label') || byFor || el.parentElement || {}).innerText || el.getAttribute('aria-label') || el.placeholder || '');
  };
  const directLocationPrompt = (s) => /current location|currently residing|currently located|where are you currently located|current residence|current country|tax residence|where.*based|where.*located|city,\s*country|country.*currently|desired location|location for employment/i.test(s || '');
  const text = clean(document.body ? document.body.innerText : '');
  const invalid = [...document.querySelectorAll('input,textarea,select')]
    .filter(el => el.required && !el.checkValidity())
    .map(el => ({
      tag: el.tagName, type: el.type || '', name: el.name || '', id: el.id || '',
      msg: el.validationMessage || '',
      label: labelFor(el).slice(0,220)
    }));
  const phoneRequired = invalid.some(i => /phone/i.test(i.name + ' ' + i.id + ' ' + i.label));
  const manualLocationBlockers = invalid
    .filter(i => directLocationPrompt(i.name + ' ' + i.id + ' ' + i.label) || /(^|\b)location(\b|$)/i.test(i.name + ' ' + i.id))
    .map(i => i.label || i.name || i.id || 'required location field');
  const files = [...document.querySelectorAll('input[type=file]')].map(i => ({id:i.id || '', count:i.files ? i.files.length : 0, names:[...(i.files || [])].map(f => f.name)}));
  const submitButtons = [...document.querySelectorAll('button,input[type=submit]')]
    .map(el => ({text: clean(el.innerText || el.value || ''), visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length), disabled: !!el.disabled}))
    .filter(b => b.visible && /submit/i.test(b.text));
  const systemFields = {
    name: !!document.querySelector('input[name="_systemfield_name"]'),
    email: !!document.querySelector('input[name="_systemfield_email"]'),
    resume: !!document.querySelector('input[type=file]#_systemfield_resume, input[type=file]')
  };
  const uploaded = files.some(f => f.count > 0);
  const formReady = text.length > 100 && (systemFields.name || systemFields.email || systemFields.resume || submitButtons.length > 0);
  const missingEntries = (text.match(/Missing entry for required field: ([^\n]+)/g) || [])
    .map((line) => clean(line.replace(/Missing entry for required field:/i, '')));
  const authenticShortTextMissing = missingEntries.filter((label) => /favorite video game|favourite video game|most played game|video game you/i.test(label));
  const booleanMissing = missingEntries.filter((label) => !authenticShortTextMissing.includes(label));
  const authenticShortTextInvalid = invalid.filter((i) => /favorite video game|favourite video game|most played game|video game you/i.test(i.label || ''));
  let code;
  if (authenticShortTextMissing.length && !booleanMissing.length && !invalid.length) code = 'manual-finish-needed:authentic-shorttext';
  else if (authenticShortTextInvalid.length && authenticShortTextInvalid.length === invalid.length && !missingEntries.length) code = 'manual-finish-needed:authentic-shorttext';
  else if (manualLocationBlockers.length) code = 'manual-finish-needed:current-location-residence-required';
  else if (missingEntries.length) code = 'invalid-required-fields';
  else if (phoneRequired) code = 'phone-required-no-active-number';
  else if (!formReady) code = 'form-not-loaded';
  else if (!submitButtons.length) code = 'submit-button-not-found';
  else if (!uploaded && files.length) code = 'resume-upload-missing';
  else if (invalid.length) code = 'invalid-required-fields';
  return JSON.stringify({
    ok: !code,
    code,
    uploaded,
    files,
    submitButtons,
    systemFields,
    formReady,
    phoneRequired,
    manualLocationBlockers,
    missingEntries,
    invalid,
    danger:/possible spam|error verifying|verify your application|unusual traffic|automated|are you a robot|too many attempts|hcaptcha challenge|phone verification|sms verification/i.test(text),
    stale:false,
    url:location.href,
    title:document.title,
    text:text.slice(0,1600)
  });
})()
""", window=window, tab=tab, timeout=30)
    return check


def cdp_tab_out_react_fields(url: str) -> dict:
    """Tab out of LinkedIn/hear-about React StringFields before submit."""
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    script = r"""
const CDP = require('chrome-remote-interface');
const targetId = process.argv[1];
const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const hearRx = /how did you hear|how'd you hear|hear about|linkedin profile|linkedin url|linkedin link|^linkedin\b/i;
(async () => {
  const list = await CDP.List({host, port});
  const entry = list.find((t) => t.id === targetId);
  if (!entry) throw new Error('target not found: ' + targetId);
  const client = await CDP({target: entry, host, port});
  try {
    const {Runtime, Input} = client;
    if (Input.enable) await Input.enable();
    const selectors = await Runtime.evaluate({
      returnByValue: true,
      expression: `(() => {
        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const out = [];
        for (const field of document.querySelectorAll('input[type=text], input[type=url], textarea')) {
          const label = clean((field.closest('label') || field.parentElement || {}).innerText || field.getAttribute('aria-label') || field.placeholder || '');
          if (!hearRx.test(label)) continue;
          if (field.id) out.push('#' + CSS.escape(field.id));
          else if (field.name) out.push('input[name="' + CSS.escape(field.name) + '"]');
        }
        return out;
      })()`,
    });
    const listSelectors = selectors.result.value || [];
    let tabbed = 0;
    for (const selector of listSelectors) {
      await Runtime.evaluate({
        returnByValue: true,
        expression: `(() => {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return false;
          el.focus();
          el.dispatchEvent(new Event('blur', { bubbles: true }));
          return true;
        })()`,
      });
      await Input.dispatchKeyEvent({ type: 'rawKeyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      tabbed += 1;
      await sleep(200);
    }
    await sleep(400);
    process.stdout.write(JSON.stringify({ ok: true, tabbed, selectors: listSelectors }) + '\n');
  } finally {
    await client.close();
  }
})().catch((err) => {
  process.stderr.write(String(err && err.stack || err) + '\n');
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = f"{CDP_DEPS}{os.pathsep}{env['NODE_PATH']}" if env.get("NODE_PATH") else str(CDP_DEPS)
    proc = subprocess.run(
        ["node", "-e", script, target_id],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=25,
        env=env,
    )
    if proc.returncode != 0:
        return {"ok": False, "code": "cdp-tab-out-failed", "stderr": proc.stderr.strip()[:500]}
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "code": "cdp-tab-out-bad-json", "stdout": proc.stdout[:500]}
    if result.get("tabbed"):
        log_scr04c(f"submit_page tab-out-wait tabbed={result.get('tabbed')} selectors={result.get('selectors')}")
    return result


def submit_page(window: int, tab: int | None = None, url: str = "") -> dict:
    if url:
        hear_about = reinforce_hear_about_choice(url, window, tab=tab)
        if not hear_about.get("ok"):
            return {"before": {"ok": False, "code": "pre-submit-hear-about-failed", **hear_about}, "after": {}, "ok": False}
        reinforced = reinforce_core_fields(url, window, tab=tab)
        if not reinforced.get("ok"):
            return {"before": {"ok": False, "code": "pre-submit-reinforce-failed", **reinforced}, "after": {}, "ok": False}
        auth_booleans = reinforce_pre_submit_auth_booleans(url, window, tab=tab)
        if not auth_booleans.get("ok"):
            return {"before": {"ok": False, "code": "pre-submit-auth-booleans-failed", **auth_booleans}, "after": {}, "ok": False}
        sponsorship_strict = reinforce_sponsorship_strict(url, window, tab=tab)
        if not sponsorship_strict.get("ok"):
            return {"before": {"ok": False, "code": "pre-submit-sponsorship-uncommitted", **sponsorship_strict}, "after": {}, "ok": False}
        tab_out = cdp_tab_out_react_fields(url)
        time.sleep(0.5)
    before = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const labelFor = (el) => {
    let byFor = null;
    try {
      byFor = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    } catch (_) {}
    return clean((el.closest('label') || byFor || el.parentElement || {}).innerText || el.getAttribute('aria-label') || el.placeholder || '');
  };
  const text = clean(document.body ? document.body.innerText : '');
  const danger = /possible spam|error verifying|verify your application|unusual traffic|automated|are you a robot|too many attempts|hcaptcha challenge|phone verification|sms verification/i.test(text);
  const invalid = [...document.querySelectorAll('input,textarea,select')]
    .filter(el => el.required && !el.checkValidity())
    .map(el => ({tag:el.tagName,type:el.type||'',name:el.name||'',id:el.id||'',msg:el.validationMessage||'',label:labelFor(el).slice(0,220)}));
  if (danger || invalid.length) return JSON.stringify({ok:false, code: danger ? 'danger-before-submit' : 'invalid-required-fields', invalid, text:text.slice(0,1000)});
  const btn = [...document.querySelectorAll('button,input[type=submit]')].find(el => /submit application/i.test(clean(el.innerText || el.value || '')));
  if (!btn) return JSON.stringify({ok:false, code:'submit-button-not-found', buttons:[...document.querySelectorAll('button')].map(el => clean(el.innerText || '')).filter(Boolean)});
  btn.click();
  return JSON.stringify({ok:true, code:'clicked', url:location.href, title:document.title});
})()
""", window=window, tab=tab, timeout=30)
    after = {}
    for wait_seconds in [18, 6, 6]:
        time.sleep(wait_seconds)
        after = js_eval(r"""
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const text = clean(document.body ? document.body.innerText : '');
  const blob = [location.href, document.title, text].join(' ');
  const href = location.href || '';
  const rejected = /couldn'?t submit|could not submit|unable to submit|not submit your application|already applied|duplicate application|we(?:'|\u2019)?ve received your application before/i.test(blob);
  const submitGone = !/submit application/i.test(text);
  const onApplicationPage = href.includes('/application') && !href.includes('/application-submitted') && !href.includes('/application/success');
  const workosSuccess = onApplicationPage && submitGone && /thank you for your interest|we received your application|delighted that you would consider/i.test(blob);
  const inlineSuccess = onApplicationPage && submitGone && (
    (/thank you for submitting/i.test(blob) && /application success|successfully submitted|we(?:'|\u2019)?ll contact you if there are next steps|we will be in touch/i.test(blob))
    || workosSuccess
    || (/application success/i.test(blob) && /received your application|successfully submitted|we will be in touch/i.test(blob))
  );
  const success = !rejected && (
    href.includes('/application-submitted') || href.includes('/application/success') || inlineSuccess ||
    (onApplicationPage
      ? /your application was successfully submitted|application was successfully submitted|we(?:'|\u2019)?ll contact you if there are next steps|thank you for your interest|we received your application|application success/i.test(blob)
      : /your application was successfully submitted|application was successfully submitted|we(?:'|\u2019)?ll contact you if there are next steps|thank you for applying|thank you for your application|we(?:'|\u2019)?ll contact you shortly/i.test(blob))
  );
  return JSON.stringify({
    url:location.href,
    title:document.title,
    success,
    rejected,
    danger:/possible spam|error verifying|verify your application|unusual traffic|automated|are you a robot|too many attempts|hcaptcha challenge|phone verification|sms verification/i.test(text),
    text:text.slice(0,1600)
  });
})()
""", window=window, tab=tab, timeout=30)
        if after.get("success") or after.get("danger") or after.get("rejected"):
            break
    ok = bool(after.get("success")) and not after.get("danger") and not after.get("rejected")
    return {"before": before, "after": after, "ok": ok}


def pre_submit_check(url: str) -> dict:
    target_id = cdp_target_for_url(url)
    if not target_id:
        return {"ok": False, "code": "cdp-target-not-found"}
    proc = sh([str(SKILL / "scripts/ats_pre_submit_check.cjs"), target_id], timeout=30)
    raw = (proc.stdout or proc.stderr or "").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"ok": False, "code": "pre-submit-bad-json", "raw": raw[:500]}
    result["returncode"] = proc.returncode
    if proc.returncode != 0:
        result["ok"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--variant", choices=sorted(RESUMES), default="General SWE")
    parser.add_argument("--resume-pages", choices=["auto", "1", "2"], default="auto")
    parser.add_argument("--window", type=int, default=0)
    parser.add_argument("--allow-auth-boolean", action="store_true")
    parser.add_argument("--allow-manual-retry", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()

    if args.window == 0:
        args.window = find_yplmicro_window()
    args.window = resolve_yplmicro_window(args.window)
    win = ensure_window(args.window)
    if not win.get("ok"):
        print(json.dumps({"ok": False, "stage": "window-check", **win}, ensure_ascii=False))
        return 10
    dedupe = sh([
        "python3", str(SKILL / "scripts/job_dedupe_check.py"),
        "--company", args.company, "--role", args.role, "--url", norm_url(args.url),
        "--company-cap", "20",
    ], timeout=30)
    print(dedupe.stdout.strip())
    if dedupe.returncode != 0:
        blocked_resume_retry = (
            "duplicate-url" in dedupe.stdout
            and '"status": "Blocked"' in dedupe.stdout
            and "resume-upload-missing" in dedupe.stdout
        )
        blocked_form_not_loaded_retry = (
            "duplicate-url" in dedupe.stdout
            and '"status": "Blocked"' in dedupe.stdout
            and "form-not-loaded" in dedupe.stdout
        )
        blocked_non_submitted_retry = (
            args.allow_manual_retry
            and "duplicate-url" in dedupe.stdout
            and '"status": "Blocked"' in dedupe.stdout
            and '"submitted": false' in dedupe.stdout.lower()
        )
        retryable = (
            args.allow_manual_retry
            and '"submitted": true' not in dedupe.stdout.lower()
            and "phone-required" not in dedupe.stdout
            and "platform-anti-bot" not in dedupe.stdout
            and (
                "ManualFinish" in dedupe.stdout
                or blocked_resume_retry
                or blocked_form_not_loaded_retry
                or blocked_non_submitted_retry
            )
        )
        if retryable:
            reason = (
                "retrying Blocked resume-upload-missing gap"
                if blocked_resume_retry
                else (
                    "retrying Blocked form-not-loaded gap"
                    if blocked_form_not_loaded_retry
                    else (
                        "retrying Blocked non-submitted duplicate"
                        if blocked_non_submitted_retry
                        else "retrying non-submitted ManualFinish form gap"
                    )
                )
            )
            print(json.dumps({"stage": "dedupe-override", "reason": reason}, ensure_ascii=False))
        else:
            return dedupe.returncode

    if re.search(r"\bAI Trainer\b", args.role, re.I):
        if not args.no_record:
            record(args.company, args.role, args.url, "Skipped", "not-swe-ai-trainer-contract", False, args.variant)
        print(json.dumps({
            "stage": "skipped",
            "ok": True,
            "reason": "not-swe-ai-trainer-contract",
            "company": args.company,
            "role": args.role,
            "url": norm_url(args.url),
        }, ensure_ascii=False))
        return 22

    tab = open_application_tab(args.window, args.url)
    filled = fill_page(resolve_resume(args.variant, args.resume_pages), args.window, args.allow_auth_boolean, tab=tab, url=args.url)
    if not filled.get("ok") and filled.get("code") == "form-not-loaded":
        time.sleep(15)
        filled = fill_page(resolve_resume(args.variant, args.resume_pages), args.window, args.allow_auth_boolean, tab=tab, url=args.url)
        if filled.get("ok"):
            print(json.dumps({"stage": "filled-after-form-load-retry", **filled}, ensure_ascii=False))
        else:
            print(json.dumps({"stage": "filled-after-form-load-retry-failed", **filled}, ensure_ascii=False))
    else:
        print(json.dumps({"stage": "filled", **filled}, ensure_ascii=False))
    if not filled.get("ok"):
        if filled.get("phoneRequired") and APPLICATION_PHONE:
            phone_retry = js_eval(f"""
(() => {{
  const phone = {json.dumps(APPLICATION_PHONE)};
  const fire = (el) => {{
    el.dispatchEvent(new InputEvent('input', {{bubbles:true, inputType:'insertText', data: el.value || ''}}));
    el.dispatchEvent(new Event('change', {{bubbles:true}}));
    el.dispatchEvent(new Event('blur', {{bubbles:true}}));
  }};
  for (const el of document.querySelectorAll('input[type=tel], input[name*="phone" i], input[id*="phone" i]')) {{
    el.focus();
    el.value = phone;
    fire(el);
  }}
  return JSON.stringify({{ok:true, phoneFilled:true}});
}})()
""", window=args.window, tab=tab, timeout=20)
            if phone_retry.get("ok"):
                filled = fill_page(resolve_resume(args.variant, args.resume_pages), args.window, args.allow_auth_boolean, tab=tab, url=args.url)
                print(json.dumps({"stage": "phone-retry-filled", **filled}, ensure_ascii=False))
    if not filled.get("ok") and filled.get("code") == "invalid-required-fields":
        invalid_retry = fill_page(resolve_resume(args.variant, args.resume_pages), args.window, args.allow_auth_boolean, tab=tab, url=args.url)
        print(json.dumps({"stage": "invalid-fields-retry-filled", **invalid_retry}, ensure_ascii=False))
        if invalid_retry.get("ok"):
            filled = invalid_retry
    if not filled.get("ok"):
        invalid = filled.get("invalid") or []
        invalid_labels = [str(item.get("label") or item.get("name") or "") for item in invalid]
        non_system = [
            label for label in invalid_labels
            if label and not NON_BLOCKER_INVALID_RX.search(label.strip())
        ]
        authentic_only = bool(non_system) and all(
            AUTHENTIC_SHORTTEXT_SKIP_RX.search(label) for label in non_system
        )
        code = (
            "manual-finish-needed:authentic-shorttext"
            if authentic_only or filled.get("code") == "manual-finish-needed:authentic-shorttext"
            else (
                "phone-required-no-active-number"
                if filled.get("phoneRequired") and not APPLICATION_PHONE
                else filled.get("code") or "manual-finish-needed:ashby-precheck"
            )
        )
        status = "Blocked" if code in {
            "stale-job",
            "phone-required-no-active-number",
            "form-not-loaded",
            "submit-button-not-found",
            "resume-upload-missing",
            "invalid-required-fields",
        } else "ManualFinish"
        if code == "manual-finish-needed:authentic-shorttext":
            status = "ManualFinish"
        if not args.no_record:
            record(args.company, args.role, args.url, status, str(code), False, args.variant)
        if not args.dry_run:
            closed = close_tab(args.window, tab=tab)
            print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 20
    pre_reinforce = reinforce_core_fields(args.url, args.window, tab=tab)
    print(json.dumps({"stage": "pre-submit-reinforce", **pre_reinforce}, ensure_ascii=False))
    if not pre_reinforce.get("ok"):
        if not args.no_record:
            record(args.company, args.role, args.url, "ManualFinish", "pre-submit-reinforce-failed", False, args.variant)
        if not args.dry_run:
            closed = close_tab(args.window, tab=tab)
            print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 14
    pre_auth = reinforce_pre_submit_auth_booleans(args.url, args.window, tab=tab)
    print(json.dumps({"stage": "pre-submit-auth-booleans", **pre_auth}, ensure_ascii=False))
    if not pre_auth.get("ok"):
        if not args.no_record:
            record(args.company, args.role, args.url, "ManualFinish", "pre-submit-auth-booleans-failed", False, args.variant)
        if not args.dry_run:
            closed = close_tab(args.window, tab=tab)
            print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 15
    precheck = pre_submit_check(args.url)
    print(json.dumps({"stage": "pre-submit-check", **precheck}, ensure_ascii=False))
    if not precheck.get("ok"):
        code = precheck.get("code") or "pre-submit-check-failed"
        if not args.no_record:
            record(args.company, args.role, args.url, "ManualFinish", str(code), False, args.variant)
        if not args.dry_run:
            closed = close_tab(args.window, tab=tab)
            print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 13
    if args.dry_run:
        print(json.dumps({
            "stage": "dry-run-ready",
            "ok": True,
            "status": "DryRunReady",
            "company": args.company,
            "role": args.role,
            "url": norm_url(args.url),
            "variant": args.variant,
        }, ensure_ascii=False))
        closed = close_tab(args.window, tab=tab)
        print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 0
    submitted = submit_page(args.window, tab=tab, url=args.url)
    print(json.dumps({"stage": "submit", **submitted}, ensure_ascii=False))
    if not submitted.get("ok"):
        after_text = str((submitted.get("after") or {}).get("text") or "")
        s3_resume_fail = S3_RESUME_UPLOAD_RX.search(after_text) or page_has_resume_s3_error(args.window, tab=tab)
        if s3_resume_fail:
            resume_path = resolve_resume(args.variant, args.resume_pages)
            s3_retry = retry_resume_upload(args.url, resume_path)
            print(json.dumps({"stage": "resume-s3-retry", **s3_retry}, ensure_ascii=False))
            if s3_retry.get("ok"):
                reinforce_after_s3 = reinforce_core_fields(args.url, args.window, tab=tab)
                print(json.dumps({"stage": "resume-s3-retry-reinforce", **reinforce_after_s3}, ensure_ascii=False))
        reinforce_retry = reinforce_core_fields(args.url, args.window, tab=tab)
        print(json.dumps({"stage": "submit-reinforce-retry", **reinforce_retry}, ensure_ascii=False))
        auth_retry = reinforce_pre_submit_auth_booleans(args.url, args.window, tab=tab)
        print(json.dumps({"stage": "submit-auth-reinforce-retry", **auth_retry}, ensure_ascii=False))
        after_text = str((submitted.get("after") or {}).get("text") or "")
        if SPONSORSHIP_MISSING_RX.search(after_text):
            sponsorship_retry = reinforce_sponsorship_strict(args.url, args.window, tab=tab, max_attempts=4)
            print(json.dumps({"stage": "submit-sponsorship-strict-retry", **sponsorship_retry}, ensure_ascii=False))
            missing_auth = reinforce_missing_work_auth_entries(args.url, args.window, tab=tab)
            print(json.dumps({"stage": "submit-missing-auth-retry", **missing_auth}, ensure_ascii=False))
        if reinforce_retry.get("ok") and auth_retry.get("ok"):
            submitted = submit_page(args.window, tab=tab, url=args.url)
            print(json.dumps({"stage": "submit-after-reinforce", **submitted}, ensure_ascii=False))
            if not submitted.get("ok"):
                after_text2 = str((submitted.get("after") or {}).get("text") or "")
                if S3_RESUME_UPLOAD_RX.search(after_text2) or page_has_resume_s3_error(args.window, tab=tab):
                    resume_path = resolve_resume(args.variant, args.resume_pages)
                    s3_retry2 = retry_resume_upload(args.url, resume_path)
                    print(json.dumps({"stage": "resume-s3-retry-after-reinforce", **s3_retry2}, ensure_ascii=False))
                    if s3_retry2.get("ok"):
                        submitted = submit_page(args.window, tab=tab, url=args.url)
                        print(json.dumps({"stage": "submit-after-resume-s3-retry", **submitted}, ensure_ascii=False))
    if submitted.get("ok"):
        if not args.no_record:
            record(args.company, args.role, args.url, "Submitted", "verified-ashby-success-yplmicro-window", True, args.variant)
            print(json.dumps({
                "stage": "recorded-submitted",
                "ok": True,
                "status": "Submitted",
                "company": args.company,
                "role": args.role,
                "url": norm_url(args.url),
                "variant": args.variant,
            }, ensure_ascii=False))
        closed = close_success_tab(args.window, tab=tab)
        print(json.dumps({"stage": "close-success-tab", **closed}, ensure_ascii=False))
        return 0
    after_text = str((submitted.get("after") or {}).get("text") or "")
    if re.search(r"already submitted your application|you have already applied", after_text, re.I):
        if not args.no_record:
            record(args.company, args.role, args.url, "DuplicateSubmitted", "ashby-already-submitted-duplicate", True, args.variant)
            print(json.dumps({
                "stage": "recorded-duplicate-submitted",
                "ok": True,
                "status": "DuplicateSubmitted",
                "company": args.company,
                "role": args.role,
                "url": norm_url(args.url),
                "variant": args.variant,
            }, ensure_ascii=False))
        if not args.dry_run:
            closed = close_tab(args.window, tab=tab)
            print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
        return 0
    code = submitted.get("after", {}).get("danger") and "platform-anti-bot" or submitted.get("before", {}).get("code") or "submit-unverified:ashby"
    if not args.no_record:
        record(args.company, args.role, args.url, "ManualFinish", str(code), False, args.variant)
    if not args.dry_run:
        closed = close_tab(args.window, tab=tab)
        print(json.dumps({"stage": "close-tab", **closed}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
