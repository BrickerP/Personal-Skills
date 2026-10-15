#!/usr/bin/env node
/* Conservative LinkedIn Easy Apply batch runner for Chrome Debug (:9222).
 * Requires the chrome-read-write skill's CDP dependency install.
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const chromeSkill = process.env.CHROME_READ_WRITE_SKILL || '/Users/yupeng/.codex/skills/chrome-read-write';
const CDP = require(path.join(chromeSkill, 'scripts/.cdp-deps/node_modules/chrome-remote-interface'));

const currentResume1P = '/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf';
const resumePaths = {
  aiAgent: currentResume1P,
  backendPlatform: currentResume1P,
  generalSWE: currentResume1P,
};
const blockedCompanyKeys = new Set([
  'speechify',
  'hightouch',
  'jobgether',
  'anthropic',
  'togetherai',
  'scaleai',
  'okta',
  'samsara',
  'pinterest',
  'verkada',
  'coder',
  'decagon',
  'entefy',
  'aifund',
  'crossinghurdles',
  'micro1',
  'jobrightai',
  'kiewit',
  'quantumworldtechnologiesinc',
  'technogeninc',
  'pacergroup',
  'princetonitservicesinc',
  'insightglobal',
  'millennium',
  'kraftkennedyinc',
  'saragossa',
  'motionrecruitment',
  'roberthalf',
  'thejudgegroup',
  'largetongroup',
  'ventureup',
  'hanwhaenergyusa',
  'tiktok',
]);
const defaultLinkedInProfile = readProfileJsonLinkedIn() || 'https://www.linkedin.com/in/yupeng-lu-845a0b411/';

function readProfileJsonLinkedIn() {
  try {
    const profileJson = '/Users/yupeng/.codex/skills/daily-job-apply/data/profile.json';
    return JSON.parse(fs.readFileSync(profileJson, 'utf8'))?.basics?.linkedin || '';
  } catch {
    return '';
  }
}

const cfg = {
  host: process.env.CHROME_CDP_HOST || '127.0.0.1',
  port: Number(process.env.CHROME_CDP_PORT || 9222),
  targetId: process.env.LINKEDIN_TARGET_ID || '',
  targetNew: Number(process.env.LINKEDIN_TARGET_NEW || 30),
  submit: process.env.LINKEDIN_SUBMIT === '1',
  dryRun: process.env.LINKEDIN_DRY_RUN === '1',
  resumeOverride: process.env.LINKEDIN_RESUME || '',
  resumeStrategy: process.env.LINKEDIN_RESUME_STRATEGY || (process.env.LINKEDIN_RESUME ? 'override' : 'auto'),
  resume: process.env.LINKEDIN_RESUME || resumePaths.aiAgent,
  email: process.env.LINKEDIN_EMAIL || 'yplmicro@gmail.com',
  phone: process.env.LINKEDIN_PHONE ?? '',
  profile: process.env.LINKEDIN_PROFILE || defaultLinkedInProfile,
  expectedProfile: process.env.LINKEDIN_EXPECTED_PROFILE || process.env.LINKEDIN_PROFILE || defaultLinkedInProfile,
  allowProfileMismatch: process.env.LINKEDIN_ALLOW_PROFILE_MISMATCH === '1',
  skipProfileCheck: process.env.LINKEDIN_SKIP_PROFILE_CHECK === '1',
  logPath: process.env.LINKEDIN_LOG_PATH || defaultLogPath(),
  ledgerPath: process.env.JOB_APPLICATION_LEDGER || '/Users/yupeng/job-hunt/application-ledger.md',
  trackerPath: process.env.JOB_TRACKER || '/Users/yupeng/job-hunt/tracker.csv',
  dailyCap: Number(process.env.LINKEDIN_DAILY_CAP || 25),
  companyCap: Number(process.env.LINKEDIN_COMPANY_CAP || 20),
  maxPhoneBlocks: Number(process.env.LINKEDIN_MAX_PHONE_BLOCKS || 8),
  maxNonSubmittedAttempts: Number(process.env.LINKEDIN_MAX_NON_SUBMITTED_ATTEMPTS || 30),
};

const defaultSearches = [
  ['AI Platform Engineer OR AI Agent Engineer OR Backend Engineer', 'United States'],
  ['Backend Engineer AI Platform', 'United States'],
  ['Software Engineer AI Platform', 'United States'],
  ['Developer Tools Engineer AI', 'United States'],
  ['Founding Engineer AI', 'United States'],
  ['Full Stack AI Engineer', 'United States'],
  ['Python Backend Engineer AI', 'United States'],
  ['TypeScript Backend Engineer AI', 'United States'],
  ['AI Infrastructure Engineer', 'United States'],
  ['Backend Platform Engineer', 'San Francisco Bay Area'],
  ['AI Agent Engineer', 'San Francisco Bay Area'],
];
const searches = process.env.LINKEDIN_SEARCHES_JSON ? JSON.parse(process.env.LINKEDIN_SEARCHES_JSON) : defaultSearches;

const includeTitle = /(ai|a\/i|ai\/ml|ml\b|agent|backend|back end|back-end|platform|software engineer|developer tools|devtools|full.stack|node|typescript|python|infrastructure|mcp|llm|machine learning|generative ai|solutions engineer)/i;
const excludeTitle = /(ios|android|mobile|qa|quality assurance|sdet|frontend only|front-end only|designer|sales|recruiter|product manager|data annot|annotation|annotator|prompt engineer|trainer|tutor|writer|content|clinical|nurse|marketing|legal|onsite|hybrid|bridge|naval|structural|bim|apigee|iws|windows|helpdesk|support|administrator|architect)/i;

function defaultLogPath() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/applications/linkedin-batch-${yyyy}-${mm}-${dd}.md`;
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function esc(s) { return String(s || '').replace(/\|/g, '\\|').replace(/\n/g, ' ').trim(); }
function companyKey(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ''); }
function blockedCompany(s) { return blockedCompanyKeys.has(companyKey(s)); }
function ensureLog() {
  fs.mkdirSync(path.dirname(cfg.logPath), { recursive: true });
  if (!fs.existsSync(cfg.logPath)) {
    const phoneLine = cfg.phone ? `+1 ${cfg.phone}` : 'none; email preferred; phone inactive';
    fs.writeFileSync(cfg.logPath, `# LinkedIn Batch Applications\n\nResume strategy: \`${cfg.resumeStrategy}\`\nResume paths: AI Agent=\`${resumePaths.aiAgent}\`; Backend Platform=\`${resumePaths.backendPlatform}\`; General SWE=\`${resumePaths.generalSWE}\`${cfg.resumeOverride ? `; Override=\`${cfg.resumeOverride}\`` : ''}\nPhone used: ${phoneLine}\nEmail: ${cfg.email}\n\n| # | Status | Company | Role | Job ID | Link | Notes |\n|---:|---|---|---|---|---|---|\n`);
  }
}
function loadExisting() {
  ensureLog();
  const applied = new Set();
  let rowNo = 1;
  for (const line of fs.readFileSync(cfg.logPath, 'utf8').split(/\n/)) {
    const m = line.match(/^\|\s*(\d+)\s*\|\s*([^|]+)\|[^|]*\|[^|]*\|\s*(\d*)\s*\|/);
    if (m) {
      rowNo = Math.max(rowNo, Number(m[1]) + 1);
      if (m[3] && /Submitted|Applied/i.test(m[2])) applied.add(m[3]);
    }
  }
  return { applied, rowNo };
}
function appendRow(state, status, company, role, id, notes = '') {
  const link = id ? `https://www.linkedin.com/jobs/view/${id}/` : '';
  fs.appendFileSync(cfg.logPath, `| ${state.rowNo++} | ${esc(status)} | ${esc(company)} | ${esc(role)} | ${esc(id)} | ${link} | ${esc(notes)} |\n`);
  if (cfg.dryRun) return;
  appendLedger(status, company, role, link);
  upsertTracker(status, company, role, link, notes);
}
function localTimestamp() {
  const stamp = new Date().toLocaleString('sv-SE', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).replace(' ', 'T');
  return `${stamp}+08:00`;
}
function localDate() {
  return localTimestamp().slice(0, 10);
}
function localDateTime() {
  return localTimestamp().slice(0, 19).replace('T', ' ');
}
function ledgerText(s) {
  return String(s || '').replace(/\|/g, '/').replace(/\s+/g, ' ').trim();
}
function appendLedger(status, company, role, link) {
  if (!link) return;
  fs.mkdirSync(path.dirname(cfg.ledgerPath), { recursive: true });
  if (!fs.existsSync(cfg.ledgerPath)) {
    fs.writeFileSync(cfg.ledgerPath, '# Job Application Ledger\n\nOne line per touched job. Format: `timestamp | status | name | url`.\n\n');
  }
  const name = ledgerText(`${company || ''}${company && role ? ' — ' : ''}${role || ''}`);
  const lineKey = `| ${ledgerText(status)} | ${name} | ${ledgerText(link)}`;
  const existing = fs.readFileSync(cfg.ledgerPath, 'utf8');
  if (existing.includes(lineKey)) return;
  fs.appendFileSync(cfg.ledgerPath, `- ${localTimestamp()} | ${ledgerText(status)} | ${name} | ${ledgerText(link)}\n`);
}
function splitCsvLine(line) {
  const out = [];
  let cur = '', quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cur += ch;
    } else if (ch === ',') {
      out.push(cur); cur = '';
    } else if (ch === '"') {
      quoted = true;
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}
function csvCell(s) {
  const v = String(s ?? '');
  return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}
function defaultTrackerFields() {
  return ['Date', 'Company', 'Role', 'JD_URL', 'Channel', 'Referrer_Name', 'Referrer_LinkedIn', 'Message_Sent', 'Application_Submitted', 'Response_Status', 'Stage', 'Last_Updated', 'Notes'];
}
function readTracker() {
  if (!fs.existsSync(cfg.trackerPath)) return { fields: defaultTrackerFields(), rows: [] };
  const lines = fs.readFileSync(cfg.trackerPath, 'utf8').split(/\r?\n/).filter(Boolean);
  if (!lines.length) return { fields: defaultTrackerFields(), rows: [] };
  const fields = splitCsvLine(lines[0]);
  const rows = lines.slice(1).map(line => {
    const values = splitCsvLine(line);
    return Object.fromEntries(fields.map((f, i) => [f, values[i] || '']));
  });
  return { fields, rows };
}
function companySubmittedCount(company) {
  const key = companyKey(company);
  if (!key) return 0;
  return readTracker().rows.filter(r => companyKey(r.Company) === key && /^yes$/i.test(r.Application_Submitted || '')).length;
}
function writeTracker(fields, rows) {
  fs.mkdirSync(path.dirname(cfg.trackerPath), { recursive: true });
  fs.writeFileSync(cfg.trackerPath, [fields.join(','), ...rows.map(r => fields.map(f => csvCell(r[f] || '')).join(','))].join('\n') + '\n');
}
function trackerStage(status) {
  if (/submitted/i.test(status)) return ['Yes', 'Submitted', 'Applied'];
  if (/readyforreview|manualfinish/i.test(status)) return ['No', status, 'ManualFinish'];
  if (/blocked/i.test(status)) return ['No', 'Blocked', 'Blocked'];
  if (/skipped/i.test(status)) return ['No', 'Skipped', 'Skipped'];
  return ['No', status, status || 'Touched'];
}
function upsertTracker(status, company, role, link, notes = '') {
  if (!link) return false;
  const { fields, rows } = readTracker();
  for (const f of defaultTrackerFields()) if (!fields.includes(f)) fields.push(f);
  const [submitted, responseStatus, stage] = trackerStage(status);
  const idx = rows.findIndex(r => String(r.JD_URL || '').trim() === link);
  const runNote = `${status} via LinkedIn Easy Apply; source=linkedin-application-agent; resume_auto=${/resume uploaded:([^:;]+)/.exec(notes)?.[1] || 'unknown'}; ${ledgerText(notes).slice(0, 240)}`.trim();
  const base = {
    Date: localDate(),
    Company: company || '',
    Role: role || '',
    JD_URL: link,
    Channel: 'LinkedIn Easy Apply',
    Referrer_Name: '',
    Referrer_LinkedIn: '',
    Message_Sent: '',
    Application_Submitted: submitted,
    Response_Status: responseStatus,
    Stage: stage,
    Last_Updated: localDateTime(),
    Notes: runNote,
  };
  if (idx >= 0) {
    const existing = rows[idx];
    const existingSubmitted = /yes/i.test(existing.Application_Submitted || '') || /submitted|applied/i.test(`${existing.Response_Status || ''} ${existing.Stage || ''}`);
    rows[idx] = {
      ...existing,
      Company: existing.Company || base.Company,
      Role: existing.Role || base.Role,
      Channel: existing.Channel || base.Channel,
      Last_Updated: base.Last_Updated,
      Notes: [existing.Notes, runNote].filter(Boolean).join(' | ').slice(-1800),
    };
    if (!existingSubmitted || submitted === 'Yes') {
      rows[idx].Application_Submitted = base.Application_Submitted;
      rows[idx].Response_Status = base.Response_Status;
      rows[idx].Stage = base.Stage;
      rows[idx].Date = base.Date;
    }
  } else {
    rows.push(base);
  }
  writeTracker(fields, rows);
  return idx < 0;
}
function countTodayLinkedInSubmissions(ledgerPath = cfg.ledgerPath, day = localDate()) {
  if (!fs.existsSync(ledgerPath)) return 0;
  let count = 0;
  for (const line of fs.readFileSync(ledgerPath, 'utf8').split(/\r?\n/)) {
    if (!line.startsWith(`- ${day}`)) continue;
    const parts = line.slice(2).split(' | ').map(s => s.trim());
    if (parts.length >= 4 && /^Submitted$/i.test(parts[1]) && /^https:\/\/www\.linkedin\.com\/jobs\/view\//.test(parts[3])) count++;
  }
  return count;
}
function applyDailyCap() {
  if (cfg.dryRun || !cfg.submit) return { todaySubmitted: countTodayLinkedInSubmissions(), remaining: cfg.dailyCap, target: cfg.targetNew };
  const todaySubmitted = countTodayLinkedInSubmissions();
  const remaining = Math.max(0, cfg.dailyCap - todaySubmitted);
  if (remaining <= 0) {
    cfg.targetNew = 0;
    return { todaySubmitted, remaining, target: 0 };
  }
  if (cfg.targetNew > remaining) cfg.targetNew = remaining;
  return { todaySubmitted, remaining, target: cfg.targetNew };
}
function validateResumePaths() {
  const paths = cfg.resumeOverride ? [cfg.resumeOverride] : Object.values(resumePaths);
  for (const p of paths) {
    if (!fs.existsSync(p)) throw new Error(`Resume PDF not found: ${p}`);
  }
}
function ensureChromeDebug() {
  const launcher = '/Users/yupeng/bin/chrome-debug.sh';
  if (fs.existsSync(launcher)) spawnSync(launcher, { stdio: 'ignore' });
}
function selectedResume(job = {}) {
  if (cfg.resumeOverride || cfg.resumeStrategy === 'override') {
    return { label: 'Override', path: cfg.resumeOverride || cfg.resume };
  }
  const text = `${job.title || ''} ${job.company || ''} ${job.text || ''}`.toLowerCase();
  const aiSpecific = /(^|\b)(ai agent|ai engineer|ai\/ml|a\/i|genai|gen ai|generative ai|applied ai|speech ai|ai platform|ai infra|ai infrastructure|ai developer platforms?|ai developer tools|ai application|ai solutions engineer|agent infrastructure|agentic|llms?|inference|ml systems|machine learning|ml engineer|developer tools|devtools|mcp|tool[- ]?using|ai[- ]native)(\b|$)/i;
  const aiEngineering = /\b(ai|a\/i)\b.*\b(engineer|developer|platform|infrastructure|application|solutions|backend|software|ml)\b|\b(engineer|developer|platform|infrastructure|application|solutions|backend|software|ml)\b.*\b(ai|a\/i)\b/i;
  if (aiSpecific.test(text) || aiEngineering.test(text)) {
    return { label: 'AI Agent', path: resumePaths.aiAgent };
  }
  if (/(^|\b)(backend|back-end|back end|platform|api|infrastructure|infra|distributed|systems|reliability|sre|cloud|data platform|server|services|devops|site reliability)(\b|$)/i.test(text)) {
    return { label: 'Backend Platform', path: resumePaths.backendPlatform };
  }
  return { label: 'General SWE', path: resumePaths.generalSWE };
}

async function resolveTarget() {
  const list = await CDP.List({ host: cfg.host, port: cfg.port });
  if (cfg.targetId) return cfg.targetId;
  const jobs = list.find(t => t.type === 'page' && /linkedin\.com\/jobs/.test(t.url || ''));
  if (jobs) return jobs.id;
  const linkedIn = list.find(t => t.type === 'page' && /linkedin\.com/.test(t.url || ''));
  if (linkedIn) return linkedIn.id;
  throw new Error('No LinkedIn tab found in Chrome Debug. Open LinkedIn in Chrome Debug first.');
}
function linkedinProfileSlug(url) {
  const m = String(url || '').match(/linkedin\.com\/in\/([^/?#]+)/i) || String(url || '').match(/\/in\/([^/?#]+)/i);
  return m ? decodeURIComponent(m[1]).replace(/\/+$/, '').toLowerCase() : '';
}
async function verifyLinkedInProfile({ evalObj, navigate }) {
  if (cfg.skipProfileCheck) return { skipped: true };
  const expected = linkedinProfileSlug(cfg.expectedProfile);
  if (!expected) throw new Error(`LINKEDIN_EXPECTED_PROFILE is not a LinkedIn /in/ URL: ${cfg.expectedProfile}`);
  const returnUrl = await evalObj(() => location.href);
  const profileUrl = /\/in\//i.test(cfg.expectedProfile)
    ? String(cfg.expectedProfile).split(/[?#]/)[0].replace(/\/+$/, '')
    : `https://www.linkedin.com/in/${expected}/`;
  await navigate(profileUrl);
  const foundSlug = linkedinProfileSlug(await evalObj(() => location.href));
  if (!foundSlug) {
    throw new Error('LinkedIn profile preflight failed: location.href has no /in/ slug after navigating to expected profile; account may be logged out or page is authwalled.');
  }
  if (foundSlug !== expected) {
    const msg = `LinkedIn profile mismatch: expected /in/${expected}, found /in/${foundSlug}`;
    if (!cfg.allowProfileMismatch) throw new Error(`${msg}. Set LINKEDIN_EXPECTED_PROFILE to the intended logged-in account, or LINKEDIN_ALLOW_PROFILE_MISMATCH=1 only for a deliberate override.`);
    console.warn(`WARN ${msg}; continuing because LINKEDIN_ALLOW_PROFILE_MISMATCH=1`);
  }
  if (returnUrl && returnUrl !== profileUrl && /linkedin\.com\/jobs/.test(returnUrl)) {
    await navigate(returnUrl);
  }
  return { expected, slugs: [foundSlug], profileUrl, returnUrl };
}

async function main() {
  ensureChromeDebug();
  validateResumePaths();
  const state = loadExisting();
  state.resumeCounts = { 'AI Agent': 0, 'Backend Platform': 0, 'General SWE': 0, Override: 0 };
  const cap = applyDailyCap();
  console.log(`CAP today_submitted=${cap.todaySubmitted}, daily_cap=${cfg.dailyCap}, remaining=${cap.remaining}, target=${cap.target}`);
  if (cfg.submit && !cfg.dryRun && cfg.targetNew <= 0) {
    console.log(`DONE submitted=0, target=0, stop=daily-cap, log=${cfg.logPath}, tracker=${cfg.trackerPath}, ledger=${cfg.ledgerPath}`);
    return;
  }
  let submitted = 0;
  let dryRunCandidates = 0;
  let nonSubmittedAttempts = 0;
  let phoneBlocks = 0;
  const targetId = await resolveTarget();
  const client = await CDP({ target: targetId, host: cfg.host, port: cfg.port });
  const { Runtime, DOM, Page } = client;
  await Runtime.enable(); await DOM.enable(); await Page.enable().catch(() => {});
  let stopReason = '';

  async function evalJS(expression) {
    const result = await Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || JSON.stringify(result.exceptionDetails));
    return result.result?.value;
  }
  async function evalObj(fn, ...args) {
    return evalJS(`(${fn.toString()})(...${JSON.stringify(args)})`);
  }
  async function navigate(url) { await Page.navigate({ url }); await sleep(5500); }
  const profileCheck = await verifyLinkedInProfile({ evalObj, navigate });
  if (!profileCheck.skipped) console.log(`PROFILE expected=/in/${profileCheck.expected}, verified=/in/${profileCheck.slugs[0]}, restored=${profileCheck.returnUrl || 'n/a'}`);
  async function closeOverlays() {
    return evalObj(async () => {
      const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
      const clicked = [];
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      const buttons = [...document.querySelectorAll('button,a,[role=button]')];
      for (const el of buttons) {
        const txt = norm(el.innerText || el.textContent || el.getAttribute('aria-label'));
        const html = norm(el.outerHTML).slice(0, 500);
        if (/close your conversation|dismiss|close/i.test(txt) && /conversation|message|msg|toast|overlay/i.test(html + ' ' + txt)) {
          try { el.click(); clicked.push(txt || 'close'); await sleep(120); } catch {}
        }
      }
      for (const sel of ['.msg-overlay-conversation-bubble', '.msg-overlay-list-bubble', '[data-test-artdeco-toast]', '.artdeco-toast-item']) {
        for (const el of document.querySelectorAll(sel)) {
          el.style.display = 'none';
          clicked.push('hide ' + sel);
        }
      }
      return clicked;
    });
  }
  async function setFileInput(selector, file) {
    const { root } = await DOM.getDocument({ depth: -1, pierce: true });
    const { nodeId } = await DOM.querySelector({ nodeId: root.nodeId, selector });
    if (!nodeId) return false;
    await DOM.setFileInputFiles({ nodeId, files: [file] });
    await sleep(2500);
    return true;
  }
  async function clickText(text) {
    return evalObj((wanted) => {
      const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
      const visible = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      const el = [...document.querySelectorAll('button,a,[role=button]')].filter(visible)
        .find(x => norm(x.innerText || x.textContent || x.getAttribute('aria-label')) === wanted);
      if (!el) return false;
      el.click(); return true;
    }, text);
  }
  async function closeModal() {
    await evalObj(() => {
      const dialog = document.querySelector('[role="dialog"], .jobs-easy-apply-modal');
      if (!dialog) return 'none';
      const b = [...document.querySelectorAll('button')].find(x => /Dismiss|Close/i.test(x.getAttribute('aria-label') || x.innerText || ''));
      if (b) b.click();
      return 'closed';
    });
    await sleep(700);
    await evalObj(() => { const b = [...document.querySelectorAll('button')].find(x => /Discard|Leave/i.test(x.innerText || '')); if (b) b.click(); });
  }
  async function collectJobs() {
    return evalObj(() => {
      const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
      const jobs = [], seen = new Set();
      for (const a of [...document.querySelectorAll('a')].filter(x => (x.href || '').includes('/jobs/view/'))) {
        const title = norm(a.innerText || a.textContent); if (!title) continue;
        const href = a.href;
        const id = (href.match(/currentJobId=(\d+)/) || href.match(/jobs\/view\/(\d+)/) || [])[1];
        if (!id || seen.has(id)) continue;
        const card = a.closest('li') || a.closest('[data-job-id]') || a.closest('div');
        const text = norm(card?.innerText || '');
        const lines = (card?.innerText || '').split('\n').map(x => x.trim()).filter(Boolean);
        const ix = lines.findIndex(x => x === title);
        jobs.push({ id, title, company: ix >= 0 ? (lines[ix + 1] || '') : '', href, text });
        seen.add(id);
      }
      return jobs;
    });
  }
  function candidate(job) {
    if (!job || state.applied.has(job.id)) return false;
    if (blockedCompany(job.company)) return false;
    if (cfg.companyCap > 0 && companySubmittedCount(job.company) >= cfg.companyCap) return false;
    if (!/Easy\s*Apply/i.test(job.text)) return false;
    if (/Applied/i.test(job.text)) return false;
    if (!includeTitle.test(job.title) || excludeTitle.test(job.title)) return false;
    return true;
  }
  async function openJob(job) {
    await closeOverlays();
    const clicked = await evalObj((id, title) => {
      const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
      const a = [...document.querySelectorAll('a')].find(x => (x.href || '').includes('/jobs/view/') && ((x.href || '').includes(id) || norm(x.innerText || x.textContent) === title));
      if (!a) return false;
      a.scrollIntoView({ block: 'center' }); a.click(); return true;
    }, job.id, job.title);
    if (clicked) return true;
    await Page.navigate({ url: `https://www.linkedin.com/jobs/view/${job.id}/` });
    await sleep(4500);
    return true;
  }
  async function clickEasyApply() {
    await closeOverlays();
    return evalObj(() => {
      const visible = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      const b = [...document.querySelectorAll('button')].filter(visible)
        .find(x => (x.getAttribute('aria-label') || '').startsWith('Easy Apply to ')) ||
        [...document.querySelectorAll('button')].filter(visible).find(x => (x.innerText || '').trim() === 'Easy Apply' && x.getBoundingClientRect().x > 650);
      if (!b) return false;
      b.click(); return true;
    });
  }
  async function clickEasyApplyWithRetry(attempts = 4) {
    for (let i = 0; i < attempts; i++) {
      if (await clickEasyApply()) return true;
      await sleep(1500);
    }
    return false;
  }
  async function fillStep(job) {
    await closeOverlays();
    const info = await evalObj((c) => {
      const modal = document.querySelector('[role="dialog"], .jobs-easy-apply-modal');
      if (/daily limit|application limit|try again tomorrow|reached.*limit/i.test(document.body?.innerText || '')) return { modal: false, notes: [], risk: 'linkedin-limit' };
      if (!modal) return { modal: false, notes: [], risk: 'no modal' };
      const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
      const lower = s => String(s || '').toLowerCase();
      const notes = [];
      const risks = [];
      const set = (el, val) => { const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype; try { Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, String(val)); } catch { el.value = String(val); } el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: String(val) })); el.dispatchEvent(new Event('change', { bubbles: true })); };
      const fieldText = el => norm((el.closest('fieldset,.fb-dash-form-element,.jobs-easy-apply-form-section__grouping,[data-test-form-element]') || el.parentElement)?.innerText || '');
      const choose = (label, opts) => {
        const l = lower(label), os = opts.filter(o => o.value && !/select|choose/.test(lower(o.text)));
        const find = re => os.find(o => re.test(lower(o.text)));
        if (/privacy|data processing|sms|text message|phone call/.test(l)) { risks.push('consent/contact-risk: ' + label.slice(0, 90)); return null; }
        if (/located in|reside in|commut|onsite|on-site|hybrid/.test(l) && !/remote|bay area|san francisco|mountain view|palo alto|california|united states/.test(l)) { risks.push('location-risk: ' + label.slice(0, 90)); return null; }
        if (/gender|race|ethnic|veteran|disabil|demographic|hispanic/.test(l)) return find(/prefer|decline|not wish|do not wish|choose not|not to answer/)?.value || os.at(-1)?.value;
        if (/contact.*preference|preferred.*contact/.test(l)) return find(/email/)?.value || os[0]?.value;
        if (/country code/.test(l)) return find(/united states|\+1/)?.value || os[0]?.value;
        if (/authorized|eligible to work|work authorization/.test(l)) return find(/yes/)?.value || os[0]?.value;
        if (/sponsorship|visa|h-?1b|opt|cpt/.test(l) && /require|need|future/.test(l)) return find(/^no$|no/)?.value || os[0]?.value;
        if (/citizen/.test(l) && !/permanent|green card|lawful|protected/.test(l)) return find(/^no$|no/)?.value || os[0]?.value;
        if (/permanent resident|green card|protected individual/.test(l)) return find(/yes/)?.value || os[0]?.value;
        if (/production.*(ai|llm|agent)|ai\/llm|agentic systems|founding engineer|early engineer|startup|backend|infrastructure|data/.test(l)) return find(/yes/)?.value || os[0]?.value;
        if (/degree|bachelor|master|18|background|drug|start immediately/.test(l)) return find(/yes/)?.value || os[0]?.value;
        risks.push('unknown-select: ' + label.slice(0, 90)); return null;
      };
      const years = label => { const l = lower(label); if (/python/.test(l)) return '5'; if (/typescript|javascript|node|react|backend|api|postgres|redis/.test(l)) return '4'; if (/aws|docker|fastapi|kafka|oauth|payment|security|cloud|linux|git/.test(l)) return '3'; if (/ai|agent|llm|mcp|machine learning|openai/.test(l)) return '1'; if (/embedded|\bc\b/.test(l)) return '2'; return '3'; };
      const textAnswer = label => {
        const l = lower(label);
        if (/first name/.test(l)) return 'Yupeng';
        if (/last name/.test(l)) return 'Lu';
        if (/middle name/.test(l)) return 'N/A';
        if (/email/.test(l)) return c.email;
        if (/phone|mobile/.test(l)) {
          if (!c.phone) {
            risks.push('phone-required-mandatory-field: ' + label.slice(0, 90));
            return null;
          }
          return c.phone;
        }
        if (/city/.test(l)) return 'Mountain View';
        if (/state/.test(l)) return 'California';
        if (/zip|postal/.test(l)) return '94043';
        if (/location|address/.test(l)) return 'Mountain View, California, United States';
        if (/linkedin/.test(l)) return c.profile;
        if (/github/.test(l)) return 'https://github.com/yupeng-dev';
        if (/website|portfolio/.test(l)) return c.profile;
        if (/salary|compensation|base/.test(l)) return '160000';
        if (/cover|why|interest|summary|additional/.test(l)) return 'I build production AI-agent and backend platform systems end-to-end, including MCP/tool-use contracts, REST APIs, OAuth/billing, report integrity, data pipelines, and cloud release gates. I am a U.S. Permanent Resident, authorized to work in the United States without sponsorship.';
        risks.push('unknown-text: ' + label.slice(0, 90));
        return null;
      };

      for (const input of [...modal.querySelectorAll('input[type=text],input[type=tel],input[type=email],input[type=number],input:not([type])')]) {
        if (input.closest('.jobs-search-box')) continue;
        const label = fieldText(input);
        const isPhoneField = /phone|mobile|tel/.test(lower(label + ' ' + input.id + ' ' + input.name + ' ' + input.type));
        if (isPhoneField && !c.phone) {
          const prefilled = input.value.trim();
          if (prefilled) {
            risks.push('phone-required-prefilled-inactive: ' + label.slice(0, 60) + ' val=' + prefilled.slice(0, 24));
          } else {
            risks.push('phone-required-mandatory-field: ' + label.slice(0, 90));
          }
          continue;
        }
        if (input.value.trim()) continue;
        const val = /numeric|years|year|experience/i.test(input.id + label) ? years(label) : textAnswer(label);
        if (val == null) continue;
        set(input, val); notes.push('input:' + label.slice(0, 60) + '=' + val);
      }
      for (const ta of [...modal.querySelectorAll('textarea')]) { if (ta.value.trim()) continue; const label = fieldText(ta); const val = textAnswer(label); if (val != null) { set(ta, val); notes.push('textarea:' + label.slice(0, 60)); } }
      for (const sel of [...modal.querySelectorAll('select')]) {
        const selected = lower(sel.options[sel.selectedIndex]?.textContent || sel.value);
        if (sel.value && !/select|choose/.test(selected)) continue;
        const val = choose(fieldText(sel), [...sel.options].map(o => ({ value: o.value, text: o.textContent.trim() })));
        if (val) { set(sel, val); notes.push('select:' + fieldText(sel).slice(0, 60)); }
      }
      for (const fs of [...modal.querySelectorAll('fieldset')]) {
        const radios = [...fs.querySelectorAll('input[type=radio]')]; if (!radios.length || radios.some(r => r.checked)) continue;
        const label = fieldText(fs); const val = choose(label, radios.map(r => ({ value: r.value || r.id, text: (modal.querySelector(`label[for="${CSS.escape(r.id)}"]`)?.innerText || r.parentElement?.innerText || '').trim(), r })));
        const opt = radios.map(r => ({ r, text: (modal.querySelector(`label[for="${CSS.escape(r.id)}"]`)?.innerText || r.parentElement?.innerText || '').trim() })).find(o => (o.r.value || o.r.id) === val);
        if (opt) { opt.r.click(); notes.push('radio:' + label.slice(0, 60) + '=' + opt.text.slice(0, 30)); }
      }
      const follow = modal.querySelector('#follow-company-checkbox'); if (follow && follow.checked) { follow.click(); notes.push('unfollow'); }
      for (const cb of [...modal.querySelectorAll('input[type=checkbox]')]) { if (cb.id === 'follow-company-checkbox' || cb.checked) continue; const label = fieldText(cb); if (/agree|acknowledge|certify|confirm|terms|authorized|understand/.test(lower(label))) { cb.click(); notes.push('checkbox:' + label.slice(0, 60)); } }
      return { modal: true, notes, risk: risks[0] || '', hasFile: !!modal.querySelector('input[type=file]'), text: norm(modal.innerText).slice(0, 900) };
    }, { email: cfg.email, phone: cfg.phone, profile: cfg.profile });
    if (info.hasFile) {
      const resume = selectedResume(job);
      state.resumeCounts[resume.label] = (state.resumeCounts[resume.label] || 0) + 1;
      await setFileInput('input[type=file]', resume.path);
      info.notes.push(`resume uploaded:${resume.label}:${path.basename(resume.path)}`);
    }
    return info;
  }
  async function driveApplication(job) {
    const notes = [];
    for (let i = 0; i < 12; i++) {
      await sleep(1200);
      const info = await fillStep(job);
      notes.push(...(info.notes || []).slice(0, 4));
      if (info.risk) return { status: 'Blocked', notes: info.risk + '; ' + notes.join('; ') };
      const buttons = await evalObj(() => [...(document.querySelector('[role="dialog"], .jobs-easy-apply-modal')?.querySelectorAll('button') || [])].map(b => (b.innerText || b.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean));
      if (buttons.includes('Submit application')) {
        if (!cfg.submit || cfg.dryRun) return { status: 'ReadyForReview', notes: 'stopped before submit; ' + notes.join('; ') };
        await clickText('Submit application'); await sleep(5000);
        const body = await evalJS('document.body.innerText.slice(0,5000)');
        if (/Applied|Application submitted|Your application was sent/i.test(body)) return { status: 'Submitted', notes: notes.join('; ') };
        notes.push('submit clicked but not confirmed');
      } else if (buttons.includes('Review')) await clickText('Review');
      else if (buttons.includes('Next')) await clickText('Next');
      else if (buttons.includes('Done')) { await clickText('Done'); return { status: 'Submitted', notes: notes.join('; ') }; }
      else return { status: 'Blocked', notes: 'no next/review/submit; ' + (info.text || '').slice(0, 250) };
    }
    return { status: 'Blocked', notes: 'step limit; ' + notes.join('; ') };
  }

  for (const [kw, loc] of searches) {
    if (submitted >= cfg.targetNew || stopReason) break;
    const url = 'https://www.linkedin.com/jobs/search/?' + new URLSearchParams({ keywords: kw, location: loc, f_AL: 'true', f_TPR: 'r604800', sortBy: 'R' });
    console.log('SEARCH', kw, loc); await navigate(url);
    for (let page = 0; page < 5 && submitted < cfg.targetNew && !stopReason; page++) {
      for (let scroll = 0; scroll < 8 && submitted < cfg.targetNew && !stopReason; scroll++) {
        const jobs = await collectJobs();
        const candidates = jobs.filter(candidate);
        console.log(`page ${page + 1} scroll ${scroll}: ${jobs.length} jobs, ${candidates.length} candidates`);
        for (const job of candidates) {
          if (submitted >= cfg.targetNew) break;
          console.log('TRY', job.id, job.company, '—', job.title);
          state.applied.add(job.id);
          if (cfg.dryRun) {
            const resume = selectedResume(job);
            state.resumeCounts[resume.label] = (state.resumeCounts[resume.label] || 0) + 1;
            appendRow(state, 'Candidate', job.company, job.title, job.id, `dry run; resume=${resume.label}:${path.basename(resume.path)}`);
            dryRunCandidates++;
            console.log(`DRYRUN_CANDIDATE ${dryRunCandidates}/${cfg.targetNew}: ${job.title}`);
            if (dryRunCandidates >= cfg.targetNew) {
              stopReason = 'dry-run-target';
              console.log(`STOP dry-run-target: collected ${dryRunCandidates}`);
              break;
            }
            continue;
          }
          if (!await openJob(job)) { appendRow(state, 'Skipped', job.company, job.title, job.id, 'could not open'); continue; }
          await sleep(3500);
          if (!await clickEasyApplyWithRetry()) { appendRow(state, 'Skipped', job.company, job.title, job.id, 'no clickable Easy Apply in detail'); continue; }
          await sleep(2500);
          let result;
          try {
            result = await driveApplication(job);
          } catch (err) {
            result = { status: 'Blocked', notes: `automation-error: ${String(err.message || err).slice(0, 180)}` };
          }
          appendRow(state, result.status, job.company, job.title, job.id, result.notes);
          if (/linkedin-limit/i.test(result.notes || '')) {
            stopReason = 'linkedin-limit';
            console.log(`STOP linkedin-limit: ${job.title}`);
            break;
          }
          if (result.status === 'Submitted') { submitted++; console.log(`SUBMITTED ${submitted}/${cfg.targetNew}: ${job.title}`); }
          else {
            nonSubmittedAttempts++;
            if (/phone-required-(prefilled-inactive|mandatory-field|no-active-number)/i.test(result.notes || '')) phoneBlocks++;
            console.log(`${result.status}: ${job.title} — ${String(result.notes).slice(0, 180)}`);
            if (phoneBlocks >= cfg.maxPhoneBlocks) {
              stopReason = 'phone-blocked-no-us-phone-policy';
              console.log(`STOP phone-blocked-no-us-phone-policy: ${phoneBlocks} jobs require phone (prefilled-inactive or mandatory field); no US phone on profile by policy`);
              break;
            }
            if (nonSubmittedAttempts >= cfg.maxNonSubmittedAttempts) {
              stopReason = 'non-submitted-attempt-cap';
              console.log(`STOP non-submitted-attempt-cap: ${nonSubmittedAttempts} attempts without enough submissions`);
              break;
            }
          }
          await closeModal(); await sleep(1200);
        }
        await evalObj(() => { const el = [...document.querySelectorAll('.jobs-search-results-list,[aria-label="Search results"],main')].find(e => e.scrollHeight > e.clientHeight) || document.scrollingElement; if (el) el.scrollBy(0, 700); });
        await sleep(1500);
      }
      const next = await evalObj(() => { const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === 'Next' && /View next page/.test(x.getAttribute('aria-label') || '')); if (b && !b.disabled) { b.click(); return true; } return false; });
      if (!next) break; await sleep(4500);
    }
  }
  console.log(`RESUME_COUNTS ${Object.entries(state.resumeCounts).map(([k, v]) => `${k}=${v}`).join(', ')}`);
  console.log(`DONE submitted=${submitted}, target=${cfg.targetNew}, stop=${stopReason || 'none'}, log=${cfg.logPath}, tracker=${cfg.trackerPath}, ledger=${cfg.ledgerPath}`);
  await client.close();
}

if (require.main === module) {
  main().catch(err => { console.error('FATAL', err); process.exit(1); });
} else {
  module.exports = {
    cfg,
    resumePaths,
    selectedResume,
    countTodayLinkedInSubmissions,
    upsertTracker,
    linkedinProfileSlug,
    trackerStage,
  };
}
