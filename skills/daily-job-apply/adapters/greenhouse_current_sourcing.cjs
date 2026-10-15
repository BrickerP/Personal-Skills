#!/usr/bin/env node

function skillRoot() { return require('path').resolve(__dirname, '..'); }
function workDir() { return process.env.DAILY_JOB_APPLY_WORK_DIR || require('path').join(require('os').homedir(), 'job-hunt'); }
function dataDir() { return require('path').join(skillRoot(), 'data'); }
function pdfDir() {
  if (process.env.DAILY_JOB_APPLY_PDF_DIR) return process.env.DAILY_JOB_APPLY_PDF_DIR;
  try {
    const profile = JSON.parse(require('fs').readFileSync(require('path').join(dataDir(), 'profile.json'), 'utf8'));
    const rp = profile.resume_paths || {};
    const p = rp.ai_agent_1p_en || rp.default_en;
    if (p) return require('path').dirname(p);
  } catch (_) {}
  return require('path').join(require('os').homedir(), 'Documents', 'resumes');
}
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

const HOME = os.homedir();
const TRACKER = (() => { const st = path.join(skillRoot(), 'state', 'tracker.csv'); const wd = path.join(workDir(), 'tracker.csv'); return require('fs').existsSync(wd) && (!require('fs').existsSync(st) || require('fs').statSync(st).size < 80) ? wd : st; })();
const OUT_DIR = path.join(HOME, 'job-hunt', 'candidate-pools');

const DEFAULT_BOARDS = [
  '6sense', 'airtable', 'andurilindustries', 'axon', 'brex', 'checkr',
  'clickhouse', 'discord', 'figma', 'gleanwork', 'honeycomb', 'humaninterest',
  'intercom', 'iterable', 'justworks', 'launchdarkly', 'logicgate', 'postman',
  'qualia', 'robinhood', 'stackblitz', 'tailscale', 'truework', 'twilio',
  'vercel', 'yugabyte', 'zuora',
];

const COMPANY_NAMES = {
  '6sense': '6sense',
  airtable: 'Airtable',
  andurilindustries: 'Anduril Industries',
  axon: 'Axon',
  brex: 'Brex',
  checkr: 'Checkr',
  clickhouse: 'ClickHouse',
  discord: 'Discord',
  figma: 'Figma',
  gleanwork: 'Glean',
  honeycomb: 'Honeycomb.io',
  humaninterest: 'Human Interest',
  intercom: 'Fin',
  iterable: 'Iterable',
  justworks: 'Justworks',
  launchdarkly: 'LaunchDarkly',
  logicgate: 'LogicGate',
  postman: 'Postman',
  qualia: 'Qualia',
  robinhood: 'Robinhood',
  stackblitz: 'Bolt.new',
  tailscale: 'Tailscale',
  truework: 'Truework',
  twilio: 'Twilio',
  vercel: 'Vercel',
  yugabyte: 'YugabyteDB',
  zuora: 'Zuora',
};

const BLOCKED_COMPANY_KEYS = new Set([
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
]);

const TITLE_ALLOW = /\b(software engineer|backend|back end|platform|infrastructure|infra|site reliability|sre|devops|full[- ]?stack|machine learning|ml engineer|ai engineer|distributed systems|cloud engineer|developer productivity|data platform|data engineer|systems engineer|security engineer)\b/i;
const TITLE_BLOCK = /\b(manager|director|vp|head|product manager|designer|researcher|user research|ux research|solutions engineer|sales engineer|customer|support|recruiter|account|marketing|program manager|intern|internship|apprentice|android|ios|hardware|procurement|officer)\b/i;
const LOCATION_ALLOW = /\b(remote|usa|united states|u\.s\.|us|san francisco|bay area|california|new york|seattle|boston|austin|mountain view|los angeles|menlo park|foster city|san mateo|bellevue|atlanta|chicago|denver|washington|virginia|arizona)\b/i;
const LOCATION_BLOCK = /\b(canada|india|bangalore|emea|apac|united kingdom|uk|london|israel|singapore|japan|australia|ireland|netherlands|greece|germany|france|spain|poland|brazil|mexico|latam|korea|colombia|estonia|ireland)\b/i;

function parseArgs(argv) {
  const args = { boards: [], out: '' };
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === '--boards') {
      while (argv[i + 1] && !argv[i + 1].startsWith('--')) args.boards.push(argv[++i]);
    } else if (item === '--out') {
      args.out = argv[++i];
    } else if (item === '--max-per-board') {
      args.maxPerBoard = Number(argv[++i]);
    }
  }
  return args;
}

function companyKey(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function normUrl(value) {
  return String(value || '')
    .trim()
    .replace(/[?#].*$/, '')
    .replace(/\/(?:application|confirmation|apply|thanks)\/?$/, '')
    .replace(/\/$/, '')
    .replace('https://boards.greenhouse.io/', 'https://job-boards.greenhouse.io/')
    .toLowerCase();
}

function splitCsv(line) {
  const out = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted && ch === '"' && line[i + 1] === '"') {
      cell += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === ',' && !quoted) {
      out.push(cell);
      cell = '';
    } else {
      cell += ch;
    }
  }
  out.push(cell);
  return out;
}

function trackerState() {
  const known = new Set();
  const companyCounts = new Map();
  if (!fs.existsSync(TRACKER)) return { known, companyCounts };
  const lines = fs.readFileSync(TRACKER, 'utf8').split(/\r?\n/).filter(Boolean);
  if (!lines.length) return { known, companyCounts };
  const header = splitCsv(lines[0]);
  const idx = Object.fromEntries(header.map((name, i) => [name, i]));
  for (const line of lines.slice(1)) {
    const cells = splitCsv(line);
    const url = normUrl(cells[idx.JD_URL] || '');
    if (url) known.add(url);
    if ((cells[idx.Application_Submitted] || '') === 'Yes') {
      const key = companyKey(cells[idx.Company] || '');
      companyCounts.set(key, (companyCounts.get(key) || 0) + 1);
    }
  }
  return { known, companyCounts };
}

function variantFor(company, role, url) {
  const text = `${company} ${role} ${url}`;
  if (/\b(ai|llm|agent|machine learning|ml|inference|model)\b/i.test(text)) return 'AI Agent Infra';
  if (/\b(backend|platform|infra|infrastructure|devops|sre|cloud|distributed|data|security)\b/i.test(text)) return 'Backend Platform';
  return 'General SWE';
}

function csvCell(value) {
  const text = String(value || '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

async function extractBoard(page, board, maxPerBoard) {
  const url = `https://job-boards.greenhouse.io/${board}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(5000);
  return page.evaluate(({ board, maxPerBoard }) => {
    const out = [];
    const seen = new Set();
    for (const anchor of [...document.querySelectorAll('a[href*="/jobs/"]')]) {
      const href = new URL(anchor.href, window.location.href).href.replace(/[?#].*$/, '').replace(/\/$/, '');
      const match = href.match(/\/jobs\/(\d+)/);
      if (!match || seen.has(href)) continue;
      seen.add(href);
      const container = anchor.closest('[data-job-id], li, article, section, div') || anchor;
      const text = (container.innerText || anchor.innerText || '').replace(/\s+/g, ' ').trim();
      const title = (anchor.innerText || text.split(/\s{2,}|Remote|San Francisco|New York|United States|USA/i)[0] || '').replace(/\s+/g, ' ').trim();
      let jobLocation = '';
      const candidates = text.split(/\s{2,}|\n/).map((part) => part.trim()).filter(Boolean);
      for (const part of candidates) {
        if (/remote|united states|usa|u\.s\.|san francisco|new york|california|seattle|boston|austin|menlo park|foster city|denver|atlanta|chicago|bellevue|virginia|arizona/i.test(part) && part !== title) {
          jobLocation = part;
          break;
        }
      }
      out.push({ board, id: match[1], url: href, title, location: jobLocation, text: text.slice(0, 500) });
      if (maxPerBoard && out.length >= maxPerBoard) break;
    }
    return out;
  }, { board, maxPerBoard });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const boards = args.boards.length ? args.boards : DEFAULT_BOARDS;
  const maxPerBoard = args.maxPerBoard || 80;
  const { known, companyCounts } = trackerState();
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  const rows = [];
  for (const board of boards) {
    const company = COMPANY_NAMES[board] || board;
    if (BLOCKED_COMPANY_KEYS.has(companyKey(company)) || BLOCKED_COMPANY_KEYS.has(companyKey(board))) continue;
    if ((companyCounts.get(companyKey(company)) || 0) >= 20) continue;
    try {
      const jobs = await extractBoard(page, board, maxPerBoard);
      for (const job of jobs) {
        const role = job.title || '';
        const location = job.location || job.text || '';
        if (!role || known.has(normUrl(job.url))) continue;
        if (!TITLE_ALLOW.test(role) || TITLE_BLOCK.test(role)) continue;
        if (LOCATION_BLOCK.test(location) && !/remote\s*-?\s*(us|usa|u\.s\.|united states)|united states|usa|u\.s\./i.test(location)) continue;
        if (location && !LOCATION_ALLOW.test(location)) continue;
        rows.push({
          status: 'rendered_current',
          ats: 'greenhouse',
          company,
          role,
          location,
          url: job.url,
          variant: variantFor(company, role, job.url),
          board,
          id: job.id,
          source_text: job.text,
        });
      }
    } catch (err) {
      rows.push({
        status: 'source_error',
        ats: 'greenhouse',
        company,
        role: '',
        location: '',
        url: `https://job-boards.greenhouse.io/${board}`,
        variant: '',
        board,
        id: '',
        source_text: String(err && err.message || err).slice(0, 300),
      });
    }
  }
  await browser.close();

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const out = args.out || path.join(OUT_DIR, `greenhouse-current-rendered-${new Date().toISOString().slice(0, 10)}.csv`);
  const fields = ['status', 'ats', 'company', 'role', 'location', 'url', 'variant', 'board', 'id', 'source_text'];
  fs.writeFileSync(out, `${fields.join(',')}\n${rows.map((row) => fields.map((field) => csvCell(row[field])).join(',')).join('\n')}\n`);
  const usable = rows.filter((row) => row.status === 'rendered_current');
  console.log(JSON.stringify({ out, rows: rows.length, rendered_current: usable.length, source_error: rows.length - usable.length }, null, 2));
  for (const row of usable.slice(0, 50)) {
    console.log(`${row.company} | ${row.role} | ${row.location} | ${row.url}`);
  }
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
