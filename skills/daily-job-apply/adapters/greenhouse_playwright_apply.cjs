#!/usr/bin/env node

function skillRoot() { return require('path').resolve(__dirname, '..'); }
function workDir() { return process.env.DAILY_JOB_APPLY_WORK_DIR || require('path').join(require('os').homedir(), 'job-hunt'); }
function dataDir() { return require('path').join(skillRoot(), 'data'); }
function pdfDir() {
  if (process.env.DAILY_JOB_APPLY_PDF_DIR) return process.env.DAILY_JOB_APPLY_PDF_DIR;
  try {
    const profile = JSON.parse(require('fs').readFileSync(require('path').join(dataDir(), 'profile.json'), 'utf8'));
    const rp = profile.resume_paths || {};
    const p = rp.ai_agent_1p_en || rp.default_en || rp.default_1p_en || rp.ai_agent || rp.backend_platform || rp.general_swe;
    if (p) return require('path').dirname(p);
  } catch (_) {}
  return require('path').join(require('os').homedir(), 'Documents', 'resumes');
}
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { chromium } = require('playwright');

const HOME = os.homedir();
function trackerHasData(csvPath) {
  if (!fs.existsSync(csvPath)) return false;
  const lines = fs.readFileSync(csvPath, 'utf8').split(/\r?\n/).filter((line) => line.trim());
  return lines.length > 1;
}
const TRACKER = (() => {
  const st = path.join(skillRoot(), 'state', 'tracker.csv');
  const wd = path.join(workDir(), 'tracker.csv');
  return trackerHasData(wd) && !trackerHasData(st) ? wd : st;
})();
const LEDGER = path.join(workDir(), 'application-ledger.md');
const SKILL = skillRoot();
const APP_DIR = pdfDir();
const RESUME_1P = path.join(APP_DIR, 'Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf');
const GMAIL_WORKER = path.join(HOME, '.codex', 'gmail-ai-daily-ops', 'gmail-ai-worker');
const GMAIL_PYTHON = path.join(GMAIL_WORKER, '.venv/bin/python');
const CHROME_CDP_ENDPOINT = process.env.CHROME_CDP_ENDPOINT || 'http://127.0.0.1:9222';
const RESUMES = {
  'AI Agent Infra': RESUME_1P,
  'Backend Platform': RESUME_1P,
  'General SWE': RESUME_1P,
};
const NODE_PATH_HINT = process.env.NODE_PATH || path.join(skillRoot(), 'adapters', 'node_modules');
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

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith('--')) continue;
    const key = item.slice(2);
    if (key === 'submit' || key === 'dry-run' || key === 'precheck-only' || key === 'precheck-security-only' || key === 'headful' || key === 'allow-manual-retry' || key === 'no-record' || key === 'system-chrome') args[key] = true;
    else args[key] = argv[++i];
  }
  return args;
}

function clean(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function isSourceQuestion(label) {
  return /(?:how|where|first).{0,50}(hear|heard|learn|found)|(?:job|role|posting|opportunity).{0,50}source|source.{0,50}(job|role|posting|opportunity)/i.test(label)
    && !/open source|source code|data source|source material|source control/i.test(label);
}

function nowCst() {
  const fmt = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  return `${fmt.format(new Date()).replace(' ', ' ')} CST`;
}

function todayCst() {
  return nowCst().slice(0, 10);
}

function normUrl(value) {
  return String(value || '')
    .trim()
    .replace(/[?#].*$/, '')
    .replace(/\/(?:application|confirmation|apply|thanks)\/?$/, '')
    .replace(/\/$/, '')
    .replace('https://boards.greenhouse.io/', 'https://job-boards.greenhouse.io/');
}

function companyKey(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function blockedCompany(value) {
  return BLOCKED_COMPANY_KEYS.has(companyKey(value));
}

function roleVariant(company, role, url) {
  const text = `${company} ${role} ${url}`;
  if (/\b(ai|llm|genai|agent|machine learning|ml|inference|model|research)\b/i.test(text)) return 'AI Agent Infra';
  if (/\b(backend|back-end|platform|infra|infrastructure|devops|sre|reliability|data|distributed|cloud|golang|java)\b/i.test(text)) return 'Backend Platform';
  return 'General SWE';
}

function loadProfile() {
  const profilePath = path.join(HOME, 'job-hunt', 'data', 'profile.json');
  const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
  const basics = profile.basics || {};
  const positioning = profile.positioning || {};
  const github = Array.isArray(basics.github)
    ? (basics.github.find((u) => /BrickerP/i.test(u)) || basics.github[0])
    : basics.github;
  return {
    firstName: 'Yupeng',
    lastName: 'Lu',
    fullName: basics.name || 'Yupeng Lu',
    preferredName: 'Yupeng',
    email: basics.email || 'yplmicro@gmail.com',
    location: 'San Francisco Bay Area',
    city: 'San Francisco',
    state: 'California',
    zip: '94105',
    org: 'VC-backed Voice AI Platform Startup',
    title: 'AI Agent & Backend Platform Engineer',
    linkedin: basics.linkedin || 'https://www.linkedin.com/in/yupeng-lu-845a0b411/',
    github: github || 'https://github.com/BrickerP',
    authorization: basics.work_authorization || 'US Permanent Resident - No sponsorship required, now or in the future',
  };
}

const values = loadProfile();

function isUsRole(job) {
  const loc = clean(`${(job.location && job.location.name) || ''} ${job.job_post_location || ''}`);
  if (/remote\s*-\s*canada|canada|india|bangalore|emea|apac|united kingdom|\buk\b|london|israel|singapore|japan|australia|ireland|netherlands/i.test(loc)
      && !/remote,?\s*us|remote,?\s*united states|united states|usa|u\.s\./i.test(loc)) {
    return false;
  }
  return /remote|united states|usa|u\.s\.|san francisco|bay area|california|new york|\bnyc\b|seattle|austin|boston|washington|los angeles|mountain view|palo alto|sunnyvale|san mateo|costa mesa|waltham|chicago|bellevue|st\. louis|dallas|jacksonville|florida/i.test(loc);
}

function valueLabel(value) {
  return clean(value && value.label);
}

function pickOption(field, matchers) {
  for (const matcher of matchers) {
    const found = (field.values || []).find((opt) => matcher(valueLabel(opt), String(opt.value || '')));
    if (found) return valueLabel(found);
  }
  return '';
}

function hasSubmittedCompany(company) {
  try {
    const raw = fs.readFileSync(TRACKER, 'utf8');
    return raw.split(/\r?\n/).some((line) => line.includes(company) && /,Yes,Submitted,/.test(line));
  } catch (_) {
    return false;
  }
}

function companySubmittedCount(company) {
  const proc = spawnSync('python3', ['-c', String.raw`
import csv, json, pathlib, sys
tracker=pathlib.Path(sys.argv[1])
def key(v):
    return "".join(ch for ch in (v or "").casefold() if ch.isalnum())
wanted=key(sys.argv[2])
count=0
if tracker.exists() and wanted:
    with tracker.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if key(row.get("Company"))==wanted and row.get("Application_Submitted")=="Yes":
                count+=1
print(json.dumps({"count": count}))
`, TRACKER, company || ''], { encoding: 'utf8', timeout: 30000 });
  if (proc.status !== 0) return 0;
  try {
    return JSON.parse(proc.stdout || '{}').count || 0;
  } catch (_) {
    return 0;
  }
}

function isNoAiQuestion(label) {
  return /no ai-generated|ai-generated answers|if you.?re an ai (?:tool|or agent)|if you are an ai (?:tool|or agent)|activation function|application challenge|do not use ai|do not use it for (?:this )?application|human-written/i.test(label);
}

function textAnswer(question, field, job) {
  const label = clean(`${question.label || ''} ${question.description || ''}`);
  const name = field.name || '';
  if (name === 'first_name') return values.firstName;
  if (name === 'last_name') return values.lastName;
  if (name === 'preferred_name') return values.preferredName;
  if (name === 'email') return values.email;
  if (name === 'phone') return '';
  if (name === 'resume' || name === 'cover_letter') return '';
  if (name === 'resume_text') return '';
  if (name === 'cover_letter_text') return '';
  if (/legal.*first/i.test(label)) return values.firstName;
  if (/legal.*last/i.test(label)) return values.lastName;
  if (/legal name/i.test(label)) return values.fullName;
  if (/1-minute video|one-minute video|video introducing yourself|share the link to.*video/i.test(label)) return '';
  if (/identify one company|raised <\$?10m|enduring part of this generation/i.test(label)) return '';
  if (/preferred.*last name|surname/i.test(label)) return values.lastName;
  if (/preferred.*first name|preferred name/i.test(label)) return values.preferredName;
  if (/zip|postal code/i.test(label)) return values.zip;
  if (/linkedin/i.test(label)) return values.linkedin;
  if (/what ai tools|which ai tools|ai tools.*using|using ai today|how are you using ai today|last ai experiment/i.test(label)) {
    return 'I use Codex-style coding agents, OpenAI APIs, retrieval/evaluation workflows, and automated QA gates to prototype, review, and harden production AI and backend systems.';
  }
  if (/what excites you most about working in ai today|excites you.*about.*ai today/i.test(label)) {
    return 'I am excited by AI systems that move beyond demos into reliable production workflows: agents with clear constraints, measurable quality gates, useful retrieval, and backend infrastructure that makes outputs auditable and dependable.';
  }
  if (/github|website|portfolio|personal site/i.test(label)) return values.github;
  if (/current.*employer|recent.*employer|current company|company.*currently/i.test(label)) return values.org;
  if (/current.*title|recent.*job title|job title/i.test(label)) return values.title;
  if (/current position/i.test(label)) return values.title;
  if (/current work status|work status/i.test(label)) return 'US Permanent Resident; authorized to work in the United States without sponsorship.';
  if (/7\+ years|seven\+ years|extensive.*7/i.test(label)) return 'No; I have 5+ years of relevant backend, platform, and AI systems engineering experience.';
  if (/current country of residence|country of residence/i.test(label)) return 'United States';
  if (/which part of the bay area|part of the bay area/i.test(label)) return 'San Francisco Bay Area';
  if (/state and city|city and state|address.*working|plan on working|current location|where.*based|where.*located|where.*live|currently live|city/i.test(label)) return values.location;
  if (/pronounce|pronunciation/i.test(label)) return 'Yoo-peng Loo';
  if (/pronoun/i.test(label)) return '';
  if (/^if yes|if yes,|please describe|if you currently work.*capital one|employee id \(eid\)/i.test(label)
    && !/ai-enabled platforms|rag pipelines|vector databases|llm integrations|agentic ai frameworks|langchain|autogen/i.test(label)) {
    return question.required ? 'N/A' : '';
  }
  if (/will you.*require.*sponsorship|do you.*require.*sponsorship|require sponsorship|require.*visa sponsorship/i.test(label)) return 'No';
  if (/sponsor|visa|work authorization|authorized.*work|eligible.*work/i.test(label)) return values.authorization;
  if (/start[- ]?date|earliest.*start|notice period|when can you start|soonest date/i.test(label)) return 'Available after a standard notice period.';
  if (isSourceQuestion(label)) return 'Company careers page';
  if (/major|area of study/i.test(label)) return 'Mathematical Finance and FinTech';
  if (/degree in computer science/i.test(label)) return 'No; my degree is in Mathematical Finance and FinTech, and my professional experience is in software, backend platform, and AI systems.';
  if (/highest level of education|highest.*education/i.test(label)) return "Master's degree";
  if (/programming language.*coding interview|coding interview.*language|which programming language/i.test(label)) return 'Python';
  if (/top 3 programming languages|what programming languages|programming languages.*proficient|languages.*level of expertise/i.test(label)) {
    return 'Python: advanced; TypeScript/JavaScript: advanced; Go: working proficiency.';
  }
  if (/development experience.*languages|languages.*years of experience|what is your development experience/i.test(label)) {
    return '5+ years building production backend, platform, data, and AI workflow systems. Strongest languages are Python and TypeScript/JavaScript, with working Go experience; recent work includes APIs, agent-style tooling, retrieval/evaluation workflows, reliability debugging, and cloud-backed product systems.';
  }
  if (/tell us about your experience.*relates to this position|experience.*relates to this position/i.test(label)) {
    return 'I have 5+ years building production backend, full-stack, data, and AI workflow systems with Python, TypeScript, React, APIs, cloud infrastructure, and reliability-focused delivery.';
  }
  if (/what tech stack.*experience|tech stack do you have experience/i.test(label)) {
    return 'Python, TypeScript/JavaScript, React, Node.js, Go, FastAPI, PostgreSQL, Redis, AWS, Docker, CI/CD, observability, retrieval workflows, and LLM/API integrations.';
  }
  if (/experience with type.?script|typescript experience|do you have.*typescript/i.test(label)) {
    return 'Yes. I have production TypeScript/JavaScript experience across full-stack product work, React interfaces, API integrations, and developer workflow tooling.';
  }
  if (/postgres.*transactional.*analytical|transactional vs\.? analytical databases/i.test(label)) {
    return 'Yes. I have used PostgreSQL for transactional product data and designed reporting/data workflows where analytical access patterns, freshness, indexing, and materialization choices matter.';
  }
  if (/strong sql.*python|deep proficiency in python|sql and.*python/i.test(label)) {
    return 'Yes. Python is one of my strongest languages, and I have used SQL extensively for backend features, reporting pipelines, debugging, and data-quality checks.';
  }
  if (/ai coding assistants|coding assistants.*workflows|developed workflows.*faster/i.test(label)) {
    return 'Yes. I use agentic coding assistants for repository inspection, scoped implementation, regression checks, review prep, and QA workflows under explicit human constraints.';
  }
  if (/describe your ideal job|ideal job.*responsibilities|responsibilities be in that role/i.test(label)) {
    return 'My ideal role combines backend/platform system design, hands-on implementation, AI workflow quality, reliability work, and close collaboration with product and research partners to ship durable production systems.';
  }
  if (/cloud providers.*familiar|familiar.*cloud providers/i.test(label)) {
    return 'AWS, Google Cloud, and Azure; strongest with AWS-backed application and data infrastructure.';
  }
  if (/cloud platforms.*deploy machine learning workloads|deploy machine learning workloads/i.test(label)) {
    return 'AWS and Google Cloud, including containerized services, batch/data workflows, storage, queues, monitoring, and API infrastructure around model-backed applications.';
  }
  if (/parts of the machine learning lifecycle.*owned|machine learning lifecycle.*owned/i.test(label)) {
    return 'I have owned production integration, data/reporting pipelines, evaluation and QA gates, deployment support, monitoring, debugging, and reliability follow-through for AI-backed product workflows.';
  }
  if (/timezone.*based|timezone.*reside|which timezone/i.test(label)) {
    return 'Pacific Time';
  }
  if (/monitoring stack|observability stack/i.test(label)) {
    return 'Prometheus, Grafana, CloudWatch, structured logging, tracing, and alerting tied to SLOs and incident response.';
  }
  if (/knowledge of kubernetes|kubernetes.*container ecosystem|container ecosystem/i.test(label)) {
    return 'Working production knowledge of Kubernetes, containers, deployments, services, Helm-style packaging, monitoring, and operational troubleshooting.';
  }
  if (/which language.*proficient|language.*most proficient|proficient.*language|python or typescript|preferred programming language.*interview|interview.*python.*typescript/i.test(label)) return 'Python';
  if (/ideal job.*allocate your time|allocate your time.*ideal job/i.test(label)) {
    return '50% designing and building production systems, 25% implementation/debugging, 15% technical collaboration, 10% documentation and operational follow-through.';
  }
  if (/employee refer|employee referral|were you referred|current or former team member/i.test(label)) return 'No';
  if (/which computer type|mac, linux or pc|mac.*linux.*pc/i.test(label)) return 'Mac';
  if (/currently.*employed with this company|current employment with this company/i.test(label)) return 'No';
  if (/why.*(?:open to|looking for).*new opportunity|open to a new opportunity|looking for a new opportunity/i.test(label)) {
    return 'I am open to a new opportunity where I can apply backend, platform, and AI systems experience to production problems with strong engineering ownership, reliability expectations, and measurable product impact.';
  }
  if (/why did you leave|why are you thinking about leaving|why.*leaving/i.test(label)) {
    return 'I am employed and selectively exploring roles where my backend, platform, and AI systems experience can be applied to larger production engineering problems with clear ownership, reliability expectations, and measurable customer impact.';
  }
  if (/able to work onsite|work onsite|in-office required/i.test(label)) {
    const localOffice = /san francisco|sf bay area|bay area|palo alto|mountain view|sunnyvale|san mateo/i.test(`${label} ${(job.location && job.location.name) || ''} ${job.job_post_location || ''}`);
    return localOffice ? 'Yes' : 'No';
  }
  if (/willing to relocate.*(sf|san francisco|bay area)|if you are not located.*(sf|san francisco|bay area).*willing to relocate/i.test(label)) return 'Yes';
  if (/willing to relocate|relocat/i.test(label)) return 'No';
  if (/digital asset space|blockchain/i.test(label)) return 'I have backend/platform experience with secure APIs, distributed systems, authentication, data workflows, and production reliability; I can ramp quickly on digital-asset domain requirements.';
  if (/complex data model/i.test(label)) return 'I built production reporting and workflow data models that join customer activity, interview/session lifecycle events, billing and subscription state, and AI evaluation outputs into reliable product and operational views.';
  if (/managed ai agents|ai agents.*number|agents.*had them do/i.test(label)) {
    return 'I have used coding and QA agents to inspect repositories, implement scoped backend/frontend changes, run regression checks, summarize failures, and prepare review-ready diffs under human-defined constraints.';
  }
  if (/describe a system.*built|system you've built|system you have built/i.test(label)) {
    return 'I built production AI workflow and reporting systems that connect user-facing product flows, backend APIs, event/session data, LLM-assisted analysis, and verification gates so teams can trust outputs and debug failures end to end.';
  }
  if (/testing, documentation, and the materialization strategy/i.test(label)) return 'I use explicit metric definitions, unit and regression checks around transformations, documented assumptions, incremental materialization where freshness matters, and reviewable lineage so downstream consumers can trust the model.';
  if (/at least 4 years.*industry|4\+ years.*industry/i.test(label)) return 'Yes';
  if (/over 3 years.*software engineer|3\+ years.*software engineer|more than 3 years.*software engineer/i.test(label)) return 'Yes';
  if (/stem degree|professional experience as a software engineer|professional experience as a s/i.test(label)) return 'Yes';
  if (/5\+ years.*react and node|production experience.*react.*node/i.test(label)) return 'Yes';
  if (/moving fast.*shipping iteratively|a-to-z technical ownership|startup or scaleup/i.test(label)) return 'Yes';
  if (/years.*kubernetes|kubernetes.*years/i.test(label)) return '1+ years';
  if (/years.*(azure databricks|databricks|profisee|kubernetes|gitops|argo)|(?:azure databricks|databricks|profisee|kubernetes|gitops|argo).*years/i.test(label)) return '';
  if (/years|full-time work experience|industry experience/i.test(label)) return '5+ years';
  if (/engineering background/i.test(label)) return 'Backend, platform, and AI infrastructure engineering with production experience across APIs, reliability, data workflows, and AI tooling.';
  if (/rapid prototyping|direct customer engagement|working closely with customers/i.test(label)) return 'Yes';
  if (/authentication and authorization services|authorization services|auth services|identity provider|identity and access/i.test(label)) {
    return 'OAuth 2.0, OpenID Connect, JWT/session auth, RBAC-style authorization, and managed identity providers such as Auth0 or Clerk.';
  }
  if (/what ai tools|which ai tools|ai tools.*using|using ai today|last ai experiment/i.test(label)) {
    return 'I use Codex-style coding agents, OpenAI APIs, retrieval/evaluation workflows, and automated QA gates to prototype, review, and harden production AI and backend systems.';
  }
  if (/ai-enabled platforms|rag pipelines|vector databases|llm integrations|agentic ai frameworks|langchain|autogen/i.test(label)) {
    return 'I have built and operated AI workflow systems using LLM APIs, retrieval-style context, evaluation gates, agent-assisted development workflows, and production backend integrations. My strongest experience is in the application and platform layer around reliable AI outputs rather than low-level model training.';
  }
  if (/professional experience.*(backend|production|distributed|remote|written communication)|remote or distributed team|building and operating production backend|writing and shipping production-level backend/i.test(label)) return 'Yes';
  if (/salary|compensation/i.test(label)) return 'Open to market-competitive compensation based on level and location.';
  if (/accommodation|adjustment/i.test(label)) return '';
  if (/why.*apply|why.*interested|why.*company|why.*role|why.*work|tell us.*background|anything else|additional information/i.test(label)) {
    return `I am interested in ${job.company_name || 'this company'} because the role matches my recent work building production AI and backend platform systems. I bring hands-on experience with agent-style tooling, API contracts, evaluation gates, reporting integrity, OAuth and billing boundaries, deployment support, and reliability work. I am strongest where product needs, infrastructure constraints, and AI workflow quality meet, and I can contribute practical engineering judgment from prototype through production operations.`;
  }
  if (field.type === 'textarea' && question.required) {
    return 'I have relevant backend, platform, and AI workflow experience and can discuss concrete shipped systems in interviews.';
  }
  return '';
}

function selectAnswer(question, field, job) {
  const label = clean(question.label || '');
  const labelAndDesc = clean(`${question.label || ''} ${question.description || ''}`);
  const roleLoc = clean(`${(job.location && job.location.name) || ''} ${job.job_post_location || ''}`);
  if (/built products or features that integrate ai\/?ml models|integrate ai\/?ml models|integrate ai or ml models/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/stem degree|professional experience as a software engineer|professional experience as a s/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/rapid prototyping|direct customer engagement|research teams|ambiguous.*fast-moving|fast-moving.*ambiguous|define what to build/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /thrive.*ambiguous|fast-moving|define what to build/i.test(text),
      (text) => /comfortable with some ambiguity/i.test(text),
    ]);
  }
  if (/early-stage or growth-stage startup|worked at.*startup|growth-stage startup/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/engineering background/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /full-stack|generalist|frontend, backend, and infrastructure/i.test(text),
      (text) => /backend-focused/i.test(text),
    ]);
  }
  if (/currently.*live in the united states|currently.*located in the us|currently located in the united states|currently.*united states/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/will you.*require.*sponsorship|require sponsorship|require.*visa sponsorship|sponsorship to extend|sponsorship.*work authorization|h1-?b transfers/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b|do not require|not require/i.test(text)]);
  }
  if (/require.*support.*maintain.*authorization|support.*maintain.*authorization/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b|do not require|not require/i.test(text)]);
  }
  if (/legally eligible.*work.*without sponsorship|work for any employer.*without sponsorship|authorized.*work.*without sponsorship/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/authorized to work lawfully.*country/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/authorization to work in the country where you live/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /valid work permit.*do not need.*sponsor/i.test(text),
      (text) => /authorized.*do not need.*sponsor/i.test(text),
    ]);
  }
  if (/highest degree|highest (?:completed )?level of education|degree you have completed|completed or are currently pursuing/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /master/i.test(text), (text) => /bachelor/i.test(text)]);
  }
  if (/user onboarding flow|in-product education|product-led growth|plg initiative/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /^no\b/i.test(text)]);
  }
  if (/privacy, security, or data protection|focused on privacy|focused on.*security|focused on.*data protection/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /less than 5|under 5|fewer than 5/i.test(text), (text) => /^0|^1|^2|^3|^4/i.test(text)]);
  }
  if (/at least 6 years.*data\/analytics|at least six years.*data\/analytics|6 years.*data\/analytics engineering|six years.*data\/analytics engineering/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/how many years of industry experience/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^5$/.test(text), (text) => /^6$/.test(text), (text) => /5\+|5 years|5-6|5 to 6/i.test(text)]);
  }
  if (/minimum of 5 years.*professional experience|5 years.*applicable professional experience|five years.*professional experience/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/years of full-time industry experience|full-time work experience.*after graduation/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /4-7|5\+|5 years|5\s*\+|3-5/i.test(text), (text) => /^5$/.test(text)]);
  }
  if (/production-ready code.*industry setting|industry setting.*production-ready code/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /4\+|5\+|5 years|5\s*\+|4-7/i.test(text)]);
  }
  if (/over 3 years.*software engineer|3\+ years.*software engineer|more than 3 years.*software engineer/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/shipped production code end-to-end|owning projects from planning through implementation/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/do you have experience with python|experience with python/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/full-stack capacity.*python\/django.*react\/typescript|python\/django.*react\/typescript/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/at least 3-5 years of ml experience|3-5 years.*ml experience|ml experience/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/over 4 years.*(machine learning|ml).*applied ai|4 years.*applied ai.*production|engineering experience.*applied ai/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/currently based in the san francisco bay area|currently.*sf bay area/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/new york tri-state area|ny tri-state area|nyc tri-state area/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/where do you currently live|state of residence|current state of residence|please indicate your state of residence/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^california\b/i.test(text), (text) => /^ca$/i.test(text)]);
  }
  if (/where are you currently located|where.*currently located/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /^americas\b/i.test(text),
      (text) => /united states|usa|u\.s\.|north america/i.test(text),
      (text) => /california|san francisco|bay area/i.test(text),
      (text) => /^remote\b/i.test(text),
    ]);
  }
  if (/where are you located/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /california|san francisco|bay area/i.test(text),
      (text) => /^other\b/i.test(text),
    ]);
  }
  if (/how much experience.*using aws|experience.*with aws/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /4\+|5\+|5 years|more than 4|more than 5|3-5|3\+|several/i.test(text),
      (text) => /2-4|2\+|intermediate/i.test(text),
    ]);
  }
  if (/rate your experience managing aws rds|experience managing aws rds|aws rds/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /^7\b|^8\b/i.test(text),
      (text) => /^6\b/i.test(text),
      (text) => /advanced|strong|experienced/i.test(text),
    ]);
  }
  if (/familiar with linux fundamentals|linux fundamentals/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/hybrid schedule.*in-office three days|hybrid schedule.*3 weekdays onsite|minimum of 3 weekdays onsite|commit to being in-office three days/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/hybrid role.*requires.*2-3 days.*office|requires.*2-3 days.*office/i.test(labelAndDesc)) {
    const localOffice = /san francisco|sf bay area|bay area|palo alto|mountain view|sunnyvale|san mateo/i.test(roleLoc + ' ' + labelAndDesc);
    return pickOption(field, [(text) => localOffice ? /^yes\b/i.test(text) : /^no\b/i.test(text)]);
  }
  if (/before seeing this job posting.*familiar|how familiar were you with/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /somewhat familiar|had heard/i.test(text), (text) => /never heard/i.test(text)]);
  }
  if (/how did you hear about faire|how did you hear/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /job posting|linkedin|company.*website|career/i.test(text)]);
  }
  if (/terraform modules|provision or manage cloud infrastructure|defining resources.*state.*variables/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/professional experience in application security/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /^no\b/i.test(text)]);
  }
  if (/building a secrets manager product|secrets manager product/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text), (text) => /^yes\b/i.test(text)]);
  }
  if (/rate your level of skill programming in go|skill programming in go/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^2\b|^3\b/i.test(text), (text) => /^1\b/i.test(text)]);
  }
  if (/country in which you will be located if hired|current country of residence/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^united states\b|^usa$|^us$/i.test(text)]);
  }
  if (/18\+ years of age|are you 18|at least 18 years of age/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/comfortable.*nyc office.*3 days|work from our nyc office/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/7\+ years.*professional software engineering|seven\+ years.*professional software engineering/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/moving fast.*shipping iteratively|a-to-z technical ownership|startup or scaleup/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /^no\b/i.test(text)]);
  }
  if (/on-call rotation|24\/7 on-call|participates in.*on-call/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/willing to relocate.*sf bay area|willing to relocate.*san francisco|if not.*sf bay area.*relocat/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b|willing/i.test(text)]);
  }
  if (/fully on-?site work|open to.*on-?site|on-?site work|come onsite|in-?office|commute/i.test(labelAndDesc)) {
    const localOffice = /san francisco|sf bay area|bay area|palo alto|mountain view|sunnyvale|san mateo/i.test(roleLoc + ' ' + labelAndDesc);
    return pickOption(field, [(text) => localOffice ? /^yes\b|open to|willing/i.test(text) : /^no\b/i.test(text)]);
  }
  if (/able to.*without relocation assistance|without relocation assistance|without relocation support/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/open to relocation|willing to relocate|relocat/i.test(labelAndDesc)) {
    const localRelocation = /san francisco|sf bay area|bay area|palo alto/i.test(roleLoc + ' ' + labelAndDesc);
    return pickOption(field, [(text) => localRelocation ? /^yes\b|open to|willing/i.test(text) : /^no\b/i.test(text)]);
  }
  if (/currently still employed with this company|currently employed with this company|currently or have you ever worked for/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/which side.*lean|lean towards back-end|back-end development/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /back\s*end|backend/i.test(text)]);
  }
  if (/previously been employed by or worked directly for squarespace/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\s*-|^no\b/i.test(text)]);
  }
  if (/no plans to move|plan to move out/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /no plans to move/i.test(text)]);
  }
  if (/programming/i.test(label) && /language/i.test(label)) {
    return pickOption(field, [(text) => /^python$/i.test(text), (text) => /python/i.test(text)]);
  }
  if (/cloud providers|cloud platforms/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^aws\b|amazon web services/i.test(text), (text) => /google cloud|gcp/i.test(text), (text) => /azure/i.test(text)]);
  }
  if (/which languages do you speak|spoken languages|languages spoken/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^english\b/i.test(text), (text) => /english/i.test(text)]);
  }
  if (/monitoring stack|observability stack/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /prometheus/i.test(text), (text) => /grafana/i.test(text), (text) => /^other$/i.test(text)]);
  }
  if (/knowledge of kubernetes|kubernetes.*container ecosystem|container ecosystem/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /intermediate/i.test(text), (text) => /basic/i.test(text)]);
  }
  if (/timezone.*based|timezone.*reside|which timezone/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^pst\b|pacific/i.test(text)]);
  }
  if (/currently reside in the location specified|reside in.*location specified/i.test(labelAndDesc)) {
    const usRole = /remote|united states|usa|u\.s\.|san francisco|bay area|california|new york|\bnyc\b|seattle|austin|boston|washington|los angeles|mountain view|palo alto|sunnyvale|san mateo|chicago/i.test(roleLoc + ' ' + labelAndDesc);
    return pickOption(field, [(text) => usRole ? /^yes\b/i.test(text) : /^no\b/i.test(text)]);
  }
  if (/reside in one of the following states/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/gender|race|ethnic|veteran|disabil|protected/i.test(label)) {
    return pickOption(field, [
      (text) => /decline|do not want|don't wish|not wish|prefer not|not disclose/i.test(text),
      (text) => /i am not a protected veteran/i.test(text),
      (text) => /no, i do not have/i.test(text),
    ]);
  }
  if (isSourceQuestion(label)) {
    return pickOption(field, [
      (text) => /company.*career|career page|company website|website/i.test(text),
      (text) => /linkedin/i.test(text),
      (text) => /^other$/i.test(text),
    ]);
  }
  if (/where have you learned about|learned about.*select all/i.test(label)) {
    return pickOption(field, [
      (text) => /company.*career|career page|company website|website/i.test(text),
      (text) => /linkedin/i.test(text),
      (text) => /^other$/i.test(text),
    ]);
  }
  if (/multiple locations.*select.*location.*best applies|select the location that best applies/i.test(labelAndDesc)) {
    return pickOption(field, [
      (text) => /san francisco/i.test(roleLoc) && /san francisco/i.test(text),
      (text) => /seattle/i.test(roleLoc) && /seattle/i.test(text),
      (text) => /new york|\bnyc\b/i.test(roleLoc) && /new york|\bnyc\b/i.test(text),
      (text) => /remote|united states|u\.s\.|us\b/i.test(roleLoc) && /remote|united states|u\.s\.|us\b/i.test(text),
    ]);
  }
  if (/additional references beyond|contact additional references|validate your previous employment/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /agree|consent/i.test(text)]);
  }
  if (/aurthorized|authorized to work|work authorization|right to work/i.test(labelAndDesc) && !/require.*sponsorship|sponsorship to extend|h1-?b transfers/i.test(labelAndDesc) && /United States|U\.S\.|US/i.test(roleLoc + ' ' + labelAndDesc)) {
    return pickOption(field, [
      (text) => /^yes\b/i.test(text),
      (text) => /authorized to work for any employer|permanent resident|green card|u\.s\. person|us person/i.test(text),
      (text) => /united states citizen or permanent resident/i.test(text),
    ]);
  }
  if (/country|countries/i.test(labelAndDesc) && /authorized to work|work authorization|legally authorized/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /united states|usa|u\.s\./i.test(text)]);
  }
  if (/use of ai for evaluating my candidacy|consenting to the use of ai/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/consent.*collecting.*personal data|collecting and using your personal data|consent.*data.*recruit/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^yes\b|accept|consent|agree/i.test(text)]);
  }
  if (/text messages|sms|message and data rates/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/relocation assistance|require.*relocation|relocation support/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/accept.*salary|salary range|listed.*range|compensation range/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b|accept|agree/i.test(text)]);
  }
  if (/sponsor|sponsorship|visa|immigration.*support/i.test(label)) {
    return pickOption(field, [(text) => /^no\b|do not require|not require/i.test(text)]);
  }
  if (/authorized|eligible.*work|work.*authorization|right to work/i.test(label)) {
    if (!isUsRole(job)) return '';
    return pickOption(field, [
      (text) => /^yes\b/i.test(text),
      (text) => /permanent resident|green card|u\.s\. person|us person/i.test(text),
      (text) => /united states citizen or permanent resident/i.test(text),
    ]);
  }
  if (/citizen/i.test(label) && /permanent resident|green card/i.test((field.values || []).map(valueLabel).join(' '))) {
    return pickOption(field, [(text) => /permanent resident|green card|united states citizen or permanent resident/i.test(text)]);
  }
  if (/u\.s\. citizen|us citizen|security clearance|clearance/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text), (text) => /not applicable|n\/a/i.test(text)]);
  }
  if (/belarus|cuba|iran|north korea|dprk|syria|russia|ukrainian territories|sanction/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/previously applied.*this position|applied.*this position|applied.*within the last|within the last \d+ months/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/applied.*last|previously applied|applied.*before/i.test(label)) {
    return pickOption(field, [(text) => hasSubmittedCompany(job.company_name || '') ? /^yes\b/i.test(text) : /^no\b/i.test(text)]);
  }
  if (/current employee|contractor|previously worked|worked at|interviewed.*before|employed by okta|subsidiaries/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/capital one|company acquired by/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/referred|referral/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/family members|relatives|outside business|advisory|consulting|board role/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/employment agreement|non-compete|restrictive covenant|litigation|subject to any agreements|restrict your ability/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/processing of personal data|consent|privacy|data.*processing|acknowledge|certify|terms|accurate|complete/i.test(label)) {
    return pickOption(field, [(text) => /acknowledge|confirm|consent|yes|agree|certify|read/i.test(text)]);
  }
  if (/country.*based|country of residence|country.*located|where.*located|where.*based/i.test(label)) {
    return pickOption(field, [
      (text) => /^united states\b|^usa$|^us$|1\. united states/i.test(text),
      (text) => /california/i.test(text),
      (text) => /los angeles/i.test(text),
    ]);
  }
  if (/currently located in the us|currently.*united states/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/live\/work in the united states|live.*work.*united states/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/reside in canada|currently.*canada/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/currently based in the sf bay area|commutable distance.*san francisco|50 miles.*san francisco/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/willing to work remotely|open to remote work|work remotely/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/state|province/i.test(label)) {
    return pickOption(field, [(text) => /^california$/i.test(text), (text) => /^ca$/i.test(text)]);
  }
  if (/city|office|location|hybrid|onsite|on-site|relocat|in person|specified location|work.*from/i.test(label)) {
    return pickOption(field, [
      (text) => /los angeles/i.test(text),
      (text) => /san francisco|bay area/i.test(text) && /san francisco|bay area|california/i.test(roleLoc + ' ' + label),
      (text) => /california/i.test(text),
      (text) => /^yes\b|open to|willing/i.test(text) && /san francisco|bay area|california|remote.*(?:united states|us)|united states.*remote/i.test(roleLoc + ' ' + label),
      (text) => /remote.*united states|remote.*us|united states/i.test(text),
    ]);
  }
  if (/ai policy for application|discover what makes us different|ai safety matters/i.test(label)) {
    return pickOption(field, [(text) => /acknowledge/i.test(text), (text) => /^yes\b/i.test(text)]);
  }
  if (/collaborating with ai|ai partnership guidelines/i.test(label)) {
    return pickOption(field, [(text) => /agree/i.test(text)]);
  }
  if (/degree|education/i.test(label)) {
    return pickOption(field, [
      (text) => /master/i.test(text),
      (text) => /bachelor/i.test(text),
    ]);
  }
  if (/programming language|coding interview.*language|language.*interview|language.*proficient|proficient.*language|python or typescript|preferred programming language.*interview|interview.*python.*typescript/i.test(label)) {
    return pickOption(field, [(text) => /^python$/i.test(text), (text) => /python/i.test(text)]);
  }
  if (/highest degree/i.test(label)) {
    return pickOption(field, [(text) => /master/i.test(text), (text) => /bachelor/i.test(text)]);
  }
  if (/fullstack|full-stack|react|react native|professional work experience|professional experience.*(backend|production|distributed|remote|written communication)|remote or distributed team/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/typescript|type.?script|javascript/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/user onboarding|in-product education|product-led growth|plg|feature flags|a\/b testing|product analytics/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /^no\b/i.test(text)]);
  }
  if (/6\+ years.*data\/analytics|six\+ years.*data\/analytics|6\+ years.*analytics engineering|six\+ years.*analytics engineering/i.test(labelAndDesc)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/6\+ years.*software|six\+ years.*software/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/(?:7|8|9|10)\+ years.*software|over (?:7|8|9|10) years.*software|(?:seven|eight|nine|ten)\+ years.*software/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text)]);
  }
  if (/at least 4 years.*industry|4\+ years.*industry/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/years.*experience|work experience|professional experience/i.test(label)) {
    return pickOption(field, [
      (text) => /less than 10|under 10|fewer than 10/i.test(text),
      (text) => /privacy|security|data protection/i.test(label) && /less than 5|under 5|fewer than 5/i.test(text),
      (text) => /less than 12|under 12|fewer than 12/i.test(text),
      (text) => /\b5\s*(?:\+|-|to|\byears?\b)|5\s*-\s*8|5\s*to\s*8|6\s*-\s*8|2\s*-\s*6|3\s*-\s*5|4\s*-\s*6|5\s*-\s*6/i.test(text),
      (text) => /4\+|3\+/i.test(text),
    ]);
  }
  if (/experience with go|used go professionally|go programming/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text), (text) => /^no\b/i.test(text)]);
  }
  if (/golang|ruby|ruby on rails|written in go/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text), (text) => /^yes\b/i.test(text)]);
  }
  if (/terraform modules|kubernetes controllers|infrastructure tooling|terraform providers|internal automation/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/terraform|kubernetes|kubectl|helm|prometheus|grafana|observability|monitoring|on-call|incident|post-incident|multi-tenant|distributed systems|remote or distributed team|written communication|automated testing|developer tooling|testing frameworks|platform engineering|backend|api|rest|graphql|llm|openai|anthropic|ai policy|ai safety|mission/i.test(label)) {
    return pickOption(field, [(text) => /^yes\b/i.test(text)]);
  }
  if (/have you|do you|are you/i.test(label)) {
    return pickOption(field, [(text) => /^no\b/i.test(text), (text) => /^yes\b/i.test(text)]);
  }
  return '';
}

function buildAnswers(job) {
  const blockers = [];
  const answers = [];
  const questions = [
    ...(job.questions || []),
    ...((job.eeoc_sections || []).flatMap((section) => section.questions || [])),
  ];
  if (!isUsRole(job)) blockers.push('non-us-location');
  for (const question of questions) {
    const label = clean(`${question.label || ''} ${question.description || ''}`);
    if (isNoAiQuestion(label)) blockers.push(`authentic-human-answer-or-challenge:${clean(question.label).slice(0, 80)}`);
    const fields = question.fields || [];
    const hasResumeFile = fields.some((field) => field.name === 'resume' || field.type === 'input_file');
    for (const field of fields) {
      const name = field.name || '';
      let value = '';
      if (field.type === 'input_text' || field.type === 'textarea') value = textAnswer(question, field, job);
      else if (field.type === 'multi_value_single_select' || field.type === 'multi_value_multi_select') value = selectAnswer(question, field, job);
      else if (field.type === 'input_file') value = name === 'resume' ? '__resume__' : '';

      if (question.required && name === 'phone') blockers.push('phone-required-no-active-number');
      if (question.required && /cover letter/i.test(label)) blockers.push('cover-letter-required');
      if (question.required && name === 'resume_text' && !hasResumeFile) blockers.push('manual-resume-text-required');
      if (question.required && name !== 'phone' && name !== 'resume_text' && field.type !== 'input_file' && !value) {
        blockers.push(`unsupported-required:${name}:${clean(question.label).slice(0, 80)}`);
      }
      answers.push({
        name,
        type: field.type,
        value,
        label: clean(question.label),
        required: !!question.required,
      });
    }
  }
  return { answers, blockers: [...new Set(blockers)] };
}

async function fetchJson(url) {
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const res = await fetch(url, { redirect: 'follow' });
      if (!res.ok) throw new Error(`fetch failed ${res.status}: ${url}`);
      return res.json();
    } catch (err) {
      lastErr = err;
      await new Promise((resolve) => setTimeout(resolve, 1500 * (attempt + 1)));
    }
  }
  throw lastErr;
}

async function humanPause(min = 350, max = 1100) {
  const ms = min + Math.floor(Math.random() * (max - min + 1));
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function cssStringEscape(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function regexEscape(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function fillById(page, id, value) {
  if (!value || !id) return { ok: true, skipped: true };
  const locator = page.locator(`[id="${cssStringEscape(id)}"], [name="${cssStringEscape(id)}"]`).first();
  if (!(await locator.count())) return { ok: false, code: 'input-not-found', id };
  await locator.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
  await locator.click({ timeout: 10000 }).catch(() => {});
  await humanPause(120, 300);
  await locator.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A').catch(() => {});
  await locator.press('Backspace').catch(() => {});
  await locator.type(String(value), { delay: value.length > 160 ? 4 : 12, timeout: 30000 }).catch(async () => {
    await locator.fill(String(value), { timeout: 10000 });
  });
  await locator.evaluate((el) => {
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.blur();
  }).catch(() => {});
  await humanPause(160, 420);
  return { ok: true };
}

async function selectById(page, id, label) {
  if (!label || !id) return { ok: true, skipped: true };
  const baseId = String(id).replace(/\[\]$/, '');
  const checkboxResult = await page.evaluate(({ id, baseId, label }) => {
    const normalize = (text) => String(text || '').replace(/\s+/g, ' ').trim();
    const boxes = [...document.querySelectorAll('input[type="checkbox"]')]
      .filter((box) => box.name === id || box.name === baseId || box.id === id || box.id === baseId);
    if (!boxes.length) return null;
    const wanted = String(label).toLowerCase();
    let picked = null;
    for (const box of boxes) {
      const wrapper = box.closest('label')
        || box.closest('.checkbox__wrapper')
        || box.closest('[class*="checkbox"]')
        || box.parentElement;
      const text = normalize((wrapper && wrapper.innerText) || box.value || box.getAttribute('aria-label') || '');
      if (text.toLowerCase().includes(wanted) || String(box.value || '').toLowerCase() === wanted) {
        if (!box.checked) box.click();
        box.dispatchEvent(new Event('input', { bubbles: true }));
        box.dispatchEvent(new Event('change', { bubbles: true }));
        picked = { id: box.id || '', name: box.name || '', label: text, checked: box.checked };
        break;
      }
    }
    if (!picked || !picked.checked) return { ok: false, code: 'checkbox-option-not-found', id, label };
    for (const box of boxes) {
      if (box !== document.getElementById(picked.id) && !box.checked) box.required = false;
    }
    return { ok: true, checkbox: picked };
  }, { id, baseId, label }).catch(() => null);
  if (checkboxResult) return checkboxResult;
  const input = page.locator([
    `[id="${cssStringEscape(id)}"]`,
    `[name="${cssStringEscape(id)}"]`,
    `[id="${cssStringEscape(baseId)}"]`,
    `[name="${cssStringEscape(baseId)}"]`,
  ].join(', ')).first();
  if (!(await input.count())) return { ok: false, code: 'select-input-not-found', id, label };
  await input.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await input.click({ timeout: 10000 });
    await humanPause(200, 500);
    await input.fill('', { timeout: 5000 }).catch(() => {});
    await input.type(label, { delay: 25 + Math.floor(Math.random() * 35), timeout: 15000 }).catch(async () => {
      await input.fill(label, { timeout: 5000 });
    });
    await humanPause(450, 900);
    const option = page
      .locator('[role="option"], [id^="react-select-"][id*="-option-"], .select__option')
      .filter({ hasText: new RegExp(regexEscape(label), 'i') })
      .first();
    if (await option.count()) {
      await option.click({ timeout: 10000 }).catch(async () => {
        await page.keyboard.press('Enter');
      });
    } else {
      await page.keyboard.press('ArrowDown');
      await humanPause(120, 260);
      await page.keyboard.press('Enter');
    }
    await humanPause(400, 900);
    const selected = await page.evaluate(({ id, label }) => {
      const input = document.getElementById(id);
      const root = input && (input.closest('.select__container') || input.closest('.field-wrapper') || input.closest('.select') || input.parentElement);
      const text = (root ? root.innerText : document.body.innerText || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const requiredInvalid = root && [...root.querySelectorAll('input')]
        .some((el) => (el.required || el.getAttribute('aria-required') === 'true') && !el.checkValidity());
      return text.includes(String(label).toLowerCase()) || (!requiredInvalid && !/\bselect\.\.\./i.test(text));
    }, { id, label }).catch(() => false);
    if (selected) return { ok: true };
    await page.keyboard.press('Escape').catch(() => {});
    await humanPause(200, 500);
  }
  return { ok: false, code: 'select-option-not-verified', id, label };
}

async function selectByIdAny(page, id, labels) {
  let last = { ok: false, code: 'no-labels-tried', id };
  for (const label of labels.filter(Boolean)) {
    last = await selectById(page, id, label);
    if (last.ok) return { ...last, value: label };
  }
  return last;
}

async function selectLocationById(page, id) {
  const input = page.locator(`[id="${cssStringEscape(id)}"]`).first();
  if (!(await input.count())) return { ok: false, code: 'location-input-not-found', id };
  for (const query of ['San Francisco, CA', 'San Francisco']) {
    await input.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
    await input.click({ timeout: 10000 });
    await input.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A').catch(() => {});
    await input.press('Backspace').catch(() => {});
    await input.type(query, { delay: 35, timeout: 15000 });
    const option = page.locator('[role="option"], [id^="react-select-"][id*="-option-"], .select__option')
      .filter({ hasText: /San Francisco/i })
      .first();
    await option.waitFor({ timeout: 12000 }).catch(() => {});
    if (await option.count()) {
      await option.click({ timeout: 10000 }).catch(async () => {
        await page.keyboard.press('Enter');
      });
    } else {
      await page.keyboard.press('ArrowDown');
      await humanPause(300, 700);
      await page.keyboard.press('Enter');
    }
    await humanPause(900, 1600);
    const state = await page.evaluate((id) => {
      const input = document.getElementById(id);
      const root = input && (input.closest('.select__container') || input.closest('.field-wrapper') || input.closest('.select'));
      const text = (root && root.innerText || '').replace(/\s+/g, ' ').trim();
      const invalid = root && [...root.querySelectorAll('input')]
        .some((el) => (el.required || el.getAttribute('aria-required') === 'true') && !el.checkValidity());
      return { text, invalid: Boolean(invalid), html: root ? root.outerHTML.replace(/\s+/g, ' ').slice(0, 500) : '' };
    }, id).catch((err) => ({ error: String(err), invalid: true }));
    if (/San Francisco/i.test(state.text) && !state.invalid) return { ok: true, value: query, state };
  }
  return { ok: false, code: 'location-option-not-verified', id };
}

async function fillStandardGreenhouseFields(page) {
  const reports = [];
  if (await page.locator('[id="candidate-location"]').count()) {
    const location = await selectLocationById(page, 'candidate-location');
    reports.push({ name: 'candidate-location', label: 'Location (City)', type: 'standard_select', required: true, ...location });
  }

  const educationSelects = [
    { id: 'school--0', label: 'School', labels: ['Boston University'] },
    { id: 'degree--0', label: 'Degree', labels: ["Master's Degree", 'Masters', 'Master'] },
    { id: 'discipline--0', label: 'Discipline', labels: ['Mathematics', 'Finance', 'Physics'] },
  ];
  for (const item of educationSelects) {
    const shouldFill = await page.evaluate((id) => {
      const input = document.getElementById(id);
      if (!input) return false;
      const root = input.closest('.select__container, .field-wrapper, .select') || input.parentElement;
      if (!root) return false;
      const text = (root.innerText || '').replace(/\s+/g, ' ').trim();
      const required = Boolean(root.querySelector('input.remix-css-1a0ro4n-requiredInput')) || /\*/.test(text);
      const alreadySelected = text && !/\bSelect\.\.\./i.test(text);
      return required && !alreadySelected;
    }, item.id).catch(() => false);
    if (!shouldFill) continue;
    const selected = await selectByIdAny(page, item.id, item.labels);
    reports.push({ name: item.id, label: item.label, type: 'standard_education_select', required: true, ...selected });
    await humanPause(180, 420);
  }

  const demographicIds = await page.evaluate(() => {
    const visible = (el) => {
      const st = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    return [...document.querySelectorAll('.demographic--container input.select__input[id]')]
      .filter(visible)
      .map((input) => {
        const root = input.closest('.field-wrapper, .demographic--question, .demographic--container') || input.parentElement;
        const text = (root && root.innerText || '').replace(/\s+/g, ' ').trim();
        const mirror = root && root.querySelector('input.remix-css-1a0ro4n-requiredInput');
        return { id: input.id, label: text.replace(/\s*Select\.\.\..*$/, '').slice(0, 160), required: Boolean(mirror) || /\*/.test(text) };
      })
      .filter((item) => item.id && item.required);
  }).catch(() => []);
  const declineLabels = [
    "I don't wish to answer",
    "I don’t wish to answer",
    'I do not wish to answer',
    'Prefer not to say',
    'Prefer not to disclose',
    'Decline to self-identify',
    'Decline to self identify',
    'I do not want to answer',
  ];
  for (const item of demographicIds) {
    const selected = await selectByIdAny(page, item.id, declineLabels);
    reports.push({ name: item.id, label: item.label || 'Voluntary demographic question', type: 'standard_demographic_select', required: true, ...selected });
    await humanPause(180, 420);
  }
  return reports;
}

async function inspectPage(page) {
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await page.evaluate(() => {
        const text = (document.body && document.body.innerText || '').replace(/\s+/g, ' ').trim();
        return {
          url: location.href,
          title: document.title,
          text: text.slice(0, 1800),
          danger: /captcha|hcaptcha|possible spam|error verifying|verify your application|unusual traffic|automated queries|are you a robot|too many attempts|security verification|phone verification|sms verification/i.test(text),
          stale: /404|not found|no longer accepting|job is no longer available|position has been closed/i.test(text),
          confirmation: /application submitted|thank you for applying|we received your application|your application has been received/i.test(text) || /\/confirmation\/?$/.test(location.href),
          needsSecurityCode: /security code|verification code|check your email/i.test(text) && /code/i.test(text),
        };
      });
    } catch (err) {
      lastErr = err;
      await page.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => {});
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw lastErr;
}

async function visibleInvalid(page) {
  return page.evaluate(() => {
    const visible = (el) => {
      const st = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    return [...document.querySelectorAll('input,textarea,select')]
      .filter((el) => visible(el))
      .filter((el) => {
        if (el.type === 'hidden' || el.type === 'file') return false;
        if (/phone/i.test(`${el.id} ${el.name} ${el.getAttribute('aria-label') || ''}`)) return false;
        if (String(el.className || '').includes('select__input')) {
          const root = el.closest('.select') || el.closest('[class*="select"]');
          const text = (root && root.innerText || '').replace(/\s+/g, ' ').trim();
          if (text && !/^Select\.\.\.?$/i.test(text) && !/\bSelect\.\.\.\s*$/i.test(text)) return false;
        }
        return !el.checkValidity() || el.getAttribute('aria-invalid') === 'true';
      })
      .map((el) => ({
        id: el.id || '',
        name: el.name || '',
        type: el.type || el.tagName,
        required: el.required || el.getAttribute('aria-required') === 'true',
        className: String(el.className || ''),
        aria: el.getAttribute('aria-label') || '',
        label: ((el.closest('fieldset, label, div') || {}).innerText || '').replace(/\s+/g, ' ').trim().slice(0, 220),
        message: el.validationMessage || '',
        debug: (() => {
          const root = el.closest('.field-wrapper, .select, .select__container, .demographic--container, form') || el.parentElement;
          const prevSelect = root && root.querySelector('input.select__input[id]');
          return {
            rootClass: root ? String(root.className || '').slice(0, 120) : '',
            rootText: root ? (root.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 300) : '',
            selectId: prevSelect ? prevSelect.id || '' : '',
            html: root ? root.outerHTML.replace(/\s+/g, ' ').slice(0, 500) : '',
          };
        })(),
      }));
  });
}

async function waitForGreenhouseHydration(page) {
  await Promise.race([
    page.waitForResponse((response) => /\/presigned_fields/.test(response.url()), { timeout: 15000 }).catch(() => null),
    page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => null),
    new Promise((resolve) => setTimeout(resolve, 9000)),
  ]);
  await humanPause(800, 1600);
}

function isEmbeddedGreenhouseUrl(url) {
  return /[?&]gh_jid=/i.test(url) || !/greenhouse\.io/i.test(url);
}

function formLoadTimeout(url) {
  return isEmbeddedGreenhouseUrl(url) ? 60000 : 30000;
}

async function gotoJob(page, url) {
  const gotoTimeout = isEmbeddedGreenhouseUrl(url) ? 60000 : 45000;
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: gotoTimeout });
      return;
    } catch (err) {
      lastErr = err;
      await new Promise((resolve) => setTimeout(resolve, 2000 * (attempt + 1)));
    }
  }
  throw lastErr;
}

function embeddedGreenhouseApplicationUrl(board, jobId) {
  if (!board || !jobId) return null;
  return `https://boards.greenhouse.io/embed/job_app?for=${encodeURIComponent(board)}&token=${encodeURIComponent(jobId)}`;
}

async function gotoJobForm(page, url, board, jobId) {
  await gotoJob(page, url);
  try {
    await page.locator('#first_name').waitFor({ timeout: formLoadTimeout(url) });
    return { url, fallback: false };
  } catch (err) {
    const fallbackUrl = embeddedGreenhouseApplicationUrl(board, jobId);
    if (!fallbackUrl || normUrl(fallbackUrl) === normUrl(url)) throw err;
    await gotoJob(page, fallbackUrl);
    await page.locator('#first_name').waitFor({ timeout: formLoadTimeout(fallbackUrl) });
    return { url: fallbackUrl, fallback: true };
  }
}

async function uploadResume(page, resumePath) {
  const input = page.locator('input[type="file"]#resume').first();
  if (!(await input.count())) return { ok: false, code: 'resume-input-not-found' };
  const fileName = path.basename(resumePath);
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt) await input.setInputFiles([]).catch(() => {});
    await input.setInputFiles(resumePath);
    for (let i = 0; i < 18; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const state = await page.evaluate((fileName) => {
        const input = document.querySelector('input[type="file"]#resume');
        const files = input && input.files ? [...input.files].map((file) => file.name) : [];
        const text = (document.body && document.body.innerText || '').replace(/\s+/g, ' ');
        return {
          files,
          bodyHasFile: text.includes(fileName) || /Resume\/CV[^\n]{0,180}(Remove|Replace|Attached|Uploaded|\.pdf)/i.test(text),
          bodySnippet: (text.match(/Resume\/CV.{0,220}/i) || [''])[0],
        };
      }, fileName);
      if (state.bodyHasFile || state.files.includes(fileName)) return { ok: true, fileName, state, uploadAttempt: attempt + 1 };
    }
    await humanPause(800, 1600);
  }
  return {
    ok: false,
    code: 'resume-upload-not-reflected',
    state: await page.evaluate((fileName) => {
      const input = document.querySelector('input[type="file"]#resume');
      const files = input && input.files ? [...input.files].map((file) => file.name) : [];
      const text = (document.body && document.body.innerText || '').replace(/\s+/g, ' ');
      return { files, fileName, bodySnippet: (text.match(/Resume\/CV.{0,260}/i) || [''])[0] };
    }, fileName),
  };
}

function gmailCall(payload) {
  if (!fs.existsSync(GMAIL_PYTHON)) return { ok: false, error: `gmail python missing: ${GMAIL_PYTHON}` };
  const proc = spawnSync(GMAIL_PYTHON, ['scripts/gmail_call.py'], {
    cwd: GMAIL_WORKER,
    input: JSON.stringify(payload),
    encoding: 'utf8',
    timeout: 70000,
  });
  if (proc.status !== 0) return { ok: false, status: proc.status, stderr: proc.stderr, stdout: proc.stdout };
  try {
    return JSON.parse(proc.stdout);
  } catch (err) {
    return { ok: false, error: 'gmail-json-parse', stdout: proc.stdout };
  }
}

async function waitForSecurityCode(company, minEpochMs) {
  const minCodeEpochMs = Math.max(0, Number(minEpochMs || 0) - 180000);
  const queries = [
    `newer_than:1d from:no-reply@us.greenhouse-mail.io "Security code for your application to ${company}"`,
    'newer_than:30m from:no-reply@us.greenhouse-mail.io "Security code for your application"',
    'newer_than:2h from:no-reply@us.greenhouse-mail.io "Security code for your application"',
  ];
  for (let attempt = 0; attempt < 8; attempt += 1) {
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 6000));
    const threads = [];
    for (const query of queries) {
      const payload = gmailCall({
        op: 'snapshot_bundle',
        mailbox: 'yplmicro-gmail-com',
        query,
        max_threads: 10,
        messages_per_thread: 5,
        excerpt_chars: 1800,
      });
      threads.push(...((((payload || {}).bundle || {}).threads || [])));
    }
    const messages = threads.flatMap((thread) => thread.messages || []);
    messages.sort((a, b) => Number(b.internal_date_ms || 0) - Number(a.internal_date_ms || 0));
    for (const message of messages) {
      const ts = Number(message.internal_date_ms || 0);
      if (ts && ts < minCodeEpochMs) continue;
      const text = `${message.subject || ''} ${message.body_excerpt || ''}`;
      const match = text.match(/application:\s*([A-Za-z0-9]{8})\b/i)
        || text.match(/\bcode\b[^A-Za-z0-9]{0,120}([A-Za-z0-9]{8})\b/i);
      if (match) return match[1];
    }
    await new Promise((resolve) => setTimeout(resolve, 10000));
  }
  return '';
}

function record(payload) {
  const py = String.raw`
import csv, json, pathlib, re, subprocess, sys
payload=json.loads(sys.stdin.read())
tracker=pathlib.Path(payload["tracker"])
ledger=pathlib.Path(payload["ledger"])
skill=pathlib.Path(payload["skill"])
def norm(u):
    u=(u or "").strip()
    u=re.sub(r"[?#].*$","",u).rstrip("/")
    u=re.sub(r"/(?:application|confirmation|apply|thanks)$","",u)
    return u.replace("https://boards.greenhouse.io/","https://job-boards.greenhouse.io/")
rows=[]
fields=["Date","Company","Role","JD_URL","Channel","Referrer_Name","Referrer_LinkedIn","Message_Sent","Application_Submitted","Response_Status","Stage","Last_Updated","Notes"]
if tracker.exists():
    with tracker.open(newline="", encoding="utf-8") as f:
        reader=csv.DictReader(f)
        fields=reader.fieldnames or fields
        rows=list(reader)
base=norm(payload["url"])
idx=next((i for i,r in enumerate(rows) if norm(r.get("JD_URL",""))==base), None)
row={
    "Date":payload["stamp"],"Company":payload["company"],"Role":payload["role"],"JD_URL":base,
    "Channel":"Greenhouse official","Referrer_Name":"","Referrer_LinkedIn":"","Message_Sent":"No",
    "Application_Submitted":"Yes" if payload["submitted"] else "No","Response_Status":payload["status"],
    "Stage":payload["status"],"Last_Updated":payload["stamp"],"Notes":payload["notes"]+"; resume="+payload["variant"],
}
if idx is None:
    rows.append({k: row.get(k, "") for k in fields})
else:
    rows[idx].update({k:v for k,v in row.items() if k in rows[idx]})
with tracker.open("w", newline="", encoding="utf-8") as f:
    writer=csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
ledger.parent.mkdir(parents=True, exist_ok=True)
safe=(payload["company"]+" - "+payload["role"]).replace("|","/")
with ledger.open("a", encoding="utf-8") as f:
    f.write(f'- {payload["stamp"]} | {payload["status"]} | {safe} | {base} | {payload["notes"]}; resume={payload["variant"]}\n')
if payload["submitted"]:
    subprocess.run(["python3", str(skill/"scripts/job_archive.py"), "emit", "--channel", "Greenhouse official", "--date", payload["date"], "--status", "Submitted", "--company", payload["company"], "--role", payload["role"], "--jd-url", base], check=False)
`;
  const proc = spawnSync('python3', ['-c', py], {
    input: JSON.stringify(payload),
    encoding: 'utf8',
    timeout: 60000,
  });
  if (proc.status !== 0) {
    throw new Error(`record failed: ${proc.stderr || proc.stdout}`);
  }
}

function dedupe(company, role, url) {
  const proc = spawnSync('python3', [
    path.join(SKILL, 'scripts', 'job_dedupe_check.py'),
    '--company', company,
    '--role', role,
    '--url', normUrl(url),
  ], { encoding: 'utf8', timeout: 30000 });
  return { status: proc.status, stdout: proc.stdout, stderr: proc.stderr };
}

function duplicateIsRetryable(raw) {
  try {
    const payload = JSON.parse(raw || '{}');
    const text = JSON.stringify(payload);
    if (/"submitted":true|\|\s*Submitted\s*\||"status":"Submitted"|verified-greenhouse-confirmation|phone-required|platform-anti-bot|captcha|hcaptcha|possible spam|verify your application|danger-text/i.test(text)) {
      return false;
    }
    return /ManualFinish|submit-unverified|skip-email-verification|invalid-or-unhandled-required|precheck|form gap|fill/i.test(text);
  } catch (_) {
    return false;
  }
}

async function submitDiagnostics(page, responses, failures) {
  const state = await inspectPage(page);
  const invalid = await visibleInvalid(page).catch(() => []);
  const details = await page.evaluate(() => {
    const visible = (el) => {
      const st = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const short = (el) => (el.innerText || el.textContent || el.value || '').replace(/\s+/g, ' ').trim().slice(0, 240);
    return {
      alerts: [...document.querySelectorAll('[role="alert"], .error, .field-error, [class*="error"], [class*="Error"]')]
        .filter(visible)
        .map(short)
        .filter(Boolean)
        .slice(0, 20),
      submitButtons: [...document.querySelectorAll('button')]
        .filter((el) => /submit/i.test(short(el)))
        .map((el) => ({ text: short(el), disabled: el.disabled, ariaDisabled: el.getAttribute('aria-disabled') })),
      recaptchaFrames: [...document.querySelectorAll('iframe[src*="recaptcha"], iframe[src*="captcha"], textarea[name="g-recaptcha-response"]')]
        .map((el) => ({ tag: el.tagName, src: el.src || '', name: el.name || '', valueLen: (el.value || '').length })),
      visibleInputs: [...document.querySelectorAll('input')]
        .filter((el) => visible(el) && el.type !== 'hidden' && el.type !== 'file')
        .map((el) => ({
          id: el.id || '',
          name: el.name || '',
          type: el.type || '',
          aria: el.getAttribute('aria-label') || '',
          placeholder: el.placeholder || '',
          valueLen: (el.value || '').length,
          maxLength: el.maxLength,
          near: short(el.closest('label, div, fieldset, form') || el),
        }))
        .slice(-25),
    };
  }).catch((err) => ({ error: String(err) }));
  return { ...state, invalid, details, responses, failures };
}

async function fillSecurityCode(page, code) {
  const split = page.locator('input[id^="security-input-"]');
  const count = await split.count().catch(() => 0);
  if (count >= code.length) {
    for (let i = 0; i < code.length; i += 1) {
      const input = page.locator(`#security-input-${i}`).first();
      await input.click({ timeout: 5000 });
      await input.fill(code[i], { timeout: 5000 });
      await humanPause(60, 140);
    }
    await page.locator(`#security-input-${code.length - 1}`).first().press('Tab').catch(() => {});
    const values = await page.evaluate(() => [...document.querySelectorAll('input[id^="security-input-"]')].map((el) => el.value || ''));
    return { ok: values.slice(0, code.length).every((value) => value.length === 1), mode: 'split-locator-fill', count, valueLens: values.map((value) => value.length) };
  }
  const candidates = [
    'input[autocomplete="one-time-code"]',
    'input[aria-label*="code" i]',
    'input[name*="code" i]',
    'input[id*="code" i]',
  ];
  for (const selector of candidates) {
    const input = page.locator(selector).first();
    if (await input.count()) {
      await input.click({ timeout: 5000 });
      await input.fill(code, { timeout: 5000 });
      return { ok: true, mode: 'single-locator-fill', selector, codeLen: code.length };
    }
  }
  return { ok: false, code: 'security-code-input-not-found' };
}

async function cdpWindowId(context, page) {
  const session = await context.newCDPSession(page);
  try {
    const result = await session.send('Browser.getWindowForTarget');
    return result.windowId;
  } finally {
    await session.detach().catch(() => {});
  }
}

async function verifyYplmicroWindow(context, page) {
  const pages = context.pages();
  const gmail = pages.find((candidate) => /mail\.google\.com\/mail\/u\/0/i.test(candidate.url()));
  if (!gmail) {
    return { ok: false, code: 'gmail-window-not-found', pageCount: pages.length };
  }
  const [gmailTitle, pageWindowId, gmailWindowId] = await Promise.all([
    gmail.title().catch(() => ''),
    cdpWindowId(context, page),
    cdpWindowId(context, gmail),
  ]);
  if (!/yplmicro@gmail\.com/i.test(gmailTitle)) {
    return { ok: false, code: 'gmail-account-mismatch', gmailTitle };
  }
  if (pageWindowId !== gmailWindowId) {
    return { ok: false, code: 'wrong-window', pageWindowId, gmailWindowId, gmailTitle };
  }
  return { ok: true, windowId: pageWindowId, gmailTitle };
}

function resolveGreenhouseFromPython(url) {
  const resolver = path.join(HOME, '.codex', 'skills', 'daily-job-apply', 'scripts', 'greenhouse_url_resolver.py');
  const proc = spawnSync('python3', [resolver, '--url', url], { encoding: 'utf8', timeout: 30000 });
  if (proc.status !== 0) return null;
  try {
    const parsed = JSON.parse(proc.stdout || '{}');
    return parsed.ok ? parsed : null;
  } catch (_) {
    return null;
  }
}

function resolvedCanonicalUrl(url, resolvedBoard, resolvedJobId) {
  if (resolvedBoard && resolvedJobId) {
    return `https://job-boards.greenhouse.io/${resolvedBoard}/jobs/${resolvedJobId}`;
  }
  return url;
}

async function applyOne(args) {
  const company = args.company;
  const role = args.role;
  let board = args.board;
  let jobId = args['job-id'] || args.jobId;
  const location = args.location || '';
  const rawSourceUrl = args.url || `https://job-boards.greenhouse.io/${board}/jobs/${jobId}`;
  if ((!board || !jobId) && rawSourceUrl) {
    const resolved = resolveGreenhouseFromPython(rawSourceUrl);
    if (resolved) {
      board = board || resolved.board;
      jobId = jobId || resolved.job_id;
    }
  }
  const sourceUrl = normUrl(resolvedCanonicalUrl(rawSourceUrl, board, jobId));
  const variant = args.variant || roleVariant(company, role, sourceUrl);
  const resumePath = RESUMES[variant];
  if (!company || !role || !board || !jobId) throw new Error('--company --role --board --job-id are required');
  if (!fs.existsSync(resumePath)) throw new Error(`resume missing: ${resumePath}`);
  if (blockedCompany(company) || blockedCompany(board)) {
    return {
      ok: false,
      status: 'Skipped',
      code: 'company-blocked',
      company,
      board,
      role,
      url: sourceUrl,
      reason: 'hard-blocked-after-overapplication',
    };
  }

  const companyCap = Number(args['company-cap'] || 20);
  const submittedForCompany = companySubmittedCount(company);
  if (companyCap > 0 && submittedForCompany >= companyCap) {
    return {
      ok: false,
      status: 'Skipped',
      code: 'company-cap-reached',
      company,
      submitted_count: submittedForCompany,
      company_cap: companyCap,
      role,
      url: sourceUrl,
    };
  }

  const duplicate = dedupe(company, role, sourceUrl);
  if (duplicate.status === 20) {
    if (!args['allow-manual-retry'] || !duplicateIsRetryable(duplicate.stdout)) {
      return { ok: false, status: 'Skipped', code: 'duplicate-url', duplicate: duplicate.stdout.trim() };
    }
  } else if (duplicate.status !== 0) {
    return { ok: false, status: 'ManualFinish', code: `dedupe-error:${duplicate.status}`, duplicate: duplicate.stderr.trim() };
  }

  let detail;
  try {
    detail = await fetchJson(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs/${jobId}?questions=true`);
  } catch (err) {
    if (!/fetch failed 404/i.test(String(err && err.message || err))) throw err;
    detail = {
      company_name: company,
      location: { name: location },
      job_post_location: location,
      questions: [],
      eeoc_sections: [],
    };
  }
  if (location) {
    detail = {
      ...detail,
      job_post_location: detail.job_post_location || location,
      location: detail.location && detail.location.name ? detail.location : { name: location },
    };
  }
  const { answers, blockers } = buildAnswers(detail);
  if (args['precheck-security-only']) {
    let browser;
    let context;
    let page;
    try {
      browser = await chromium.launch({ headless: true, channel: 'chrome' });
      context = await browser.newContext({
        locale: 'en-US',
        timezoneId: 'America/Los_Angeles',
        viewport: { width: 1360, height: 1100 },
      });
      page = await context.newPage();
      page.setDefaultTimeout(20000);
      await gotoJob(page, rawSourceUrl);
      await page.locator('#first_name, #email, input[id^="security-input-"]').first().waitFor({ timeout: formLoadTimeout(rawSourceUrl) }).catch(() => {});
      await waitForGreenhouseHydration(page);
      const pageState = await inspectPage(page);
      const securityInputCount = await page.locator('input[id^="security-input-"]').count().catch(() => 0);
      const needsSecurityCode = Boolean(pageState.needsSecurityCode || securityInputCount >= 4);
      if (needsSecurityCode) {
        return {
          ok: false,
          status: 'Skipped',
          code: 'skip-email-verification',
          legacyCode: 'needsSecurityCode',
          company,
          role,
          board,
          jobId,
          url: sourceUrl,
          securityInputCount,
          page: pageState,
        };
      }
      return {
        ok: true,
        status: 'SecurityPrecheckOk',
        company,
        role,
        board,
        jobId,
        url: sourceUrl,
        securityInputCount,
      };
    } catch (err) {
      return {
        ok: false,
        status: 'Skipped',
        code: 'security-precheck-error',
        company,
        role,
        board,
        jobId,
        url: sourceUrl,
        error: String((err && err.stack) || err || '').slice(0, 1200),
      };
    } finally {
      if (context) await context.close().catch(() => {});
      if (browser) await browser.close().catch(() => {});
    }
  }
  if (args['precheck-only']) {
    if (blockers.length) {
      return {
        ok: false,
        status: blockers.includes('phone-required-no-active-number') ? 'Blocked' : 'ManualFinish',
        code: 'answer-blockers',
        company,
        role,
        board,
        jobId,
        url: sourceUrl,
        variant,
        blockers,
        answersPreview: answers,
      };
    }
    let browser;
    let context;
    let page;
    try {
      browser = await chromium.launch({ headless: true, channel: 'chrome' });
      context = await browser.newContext({
        locale: 'en-US',
        timezoneId: 'America/Los_Angeles',
        viewport: { width: 1360, height: 1100 },
      });
      page = await context.newPage();
      page.setDefaultTimeout(20000);
      await gotoJobForm(page, rawSourceUrl, board, jobId);
      await waitForGreenhouseHydration(page);
      const runtimeBlockers = await page.evaluate(() => {
        const visible = (el) => {
          const st = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
        };
        return [...document.querySelectorAll('input[id^="start-year--"], input[id^="end-year--"]')]
          .filter((el) => visible(el) && (el.required || el.getAttribute('aria-required') === 'true'))
          .map((el) => ({
            id: el.id || '',
            aria: el.getAttribute('aria-label') || '',
            label: ((el.closest('label, div, fieldset') || {}).innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120),
          }));
      });
      if (runtimeBlockers.length) {
        return {
          ok: false,
          status: 'ManualFinish',
          code: 'education-date-required-unverified',
          company,
          role,
          board,
          jobId,
          url: sourceUrl,
          variant,
          runtimeBlockers,
          answersPreview: answers,
        };
      }
    } catch (err) {
      return {
        ok: false,
        status: 'ManualFinish',
        code: 'runtime-precheck-error',
        company,
        role,
        board,
        jobId,
        url: sourceUrl,
        variant,
        error: String((err && err.stack) || err || '').slice(0, 1200),
        answersPreview: answers,
      };
    } finally {
      if (context) await context.close().catch(() => {});
      if (browser) await browser.close().catch(() => {});
    }
    return {
      ok: true,
      status: 'PrecheckReady',
      company,
      role,
      board,
      jobId,
      url: sourceUrl,
      variant,
      answersPreview: answers,
    };
  }
  if (blockers.length) {
    const result = { ok: false, status: blockers.includes('phone-required-no-active-number') ? 'Blocked' : 'ManualFinish', code: 'answer-blockers', company, role, board, jobId, url: sourceUrl, variant, blockers, answersPreview: answers };
    if (args.submit && !args['no-record']) {
      record({
        tracker: TRACKER, ledger: LEDGER, skill: SKILL, stamp: nowCst(), date: todayCst(),
        company, role, url: sourceUrl, submitted: false, status: result.status,
        notes: `${result.status === 'Blocked' ? 'blocked' : 'manual-finish-needed'}:${blockers.join(',')}`,
        variant,
      });
    }
    return result;
  }

  let browser;
  let context;
  let page;
  const connectedDebugChrome = Boolean(args['system-chrome']);
  if (connectedDebugChrome) {
    browser = await chromium.connectOverCDP(CHROME_CDP_ENDPOINT, { timeout: 120000 });
    context = browser.contexts()[0];
    if (!context) throw new Error(`Chrome Debug has no default context at ${CHROME_CDP_ENDPOINT}`);
    page = await context.newPage();
    await page.setViewportSize({ width: 1360, height: 1100 }).catch(() => {});
    const windowGuard = await verifyYplmicroWindow(context, page);
    if (!windowGuard.ok) {
      await page.close().catch(() => {});
      return { ok: false, status: 'ManualFinish', code: windowGuard.code, company, role, board, jobId, url: sourceUrl, windowGuard };
    }
  } else {
    const launchOptions = {
      headless: !args.headful,
      channel: args.channel || 'chrome',
    };
    browser = await chromium.launch(launchOptions);
    context = await browser.newContext({
      locale: 'en-US',
      timezoneId: 'America/Los_Angeles',
      viewport: { width: 1360, height: 1100 },
    });
    page = await context.newPage();
  }
  page.setDefaultTimeout(20000);
  let final;
  try {
    await gotoJobForm(page, rawSourceUrl, board, jobId);
    await waitForGreenhouseHydration(page);
    let pageState = await inspectPage(page);
    if (pageState.danger || pageState.stale) {
      final = { ok: false, status: pageState.danger ? 'ManualFinish' : 'Blocked', code: pageState.danger ? 'platform-anti-bot' : 'stale-job', page: pageState };
      return final;
    }

    const upload = await uploadResume(page, resumePath);
    if (!upload.ok) {
      final = { ok: false, status: 'ManualFinish', code: upload.code, upload, page: pageState };
      return final;
    }
    await humanPause(900, 1800);

    const reports = [];
    for (const item of answers) {
      if (item.name === 'phone' || item.name === 'resume' || item.name === 'cover_letter' || item.type === 'input_file') continue;
      if (item.name === 'resume_text' || item.name === 'cover_letter_text') continue;
      let report;
      if (item.type === 'multi_value_single_select' || item.type === 'multi_value_multi_select') {
        report = await selectById(page, item.name, item.value);
      } else {
        report = await fillById(page, item.name, item.value);
      }
      reports.push({ name: item.name, label: item.label, type: item.type, value: String(item.value || '').slice(0, 120), required: item.required, ...report });
      if (!report.ok && item.required) break;
      await humanPause(250, 700);
    }

    reports.push(...(await fillStandardGreenhouseFields(page)));

    const checkboxReports = await page.evaluate(() => {
      const visible = (el) => {
        const st = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      };
      const reports = [];
      for (const box of [...document.querySelectorAll('input[type="checkbox"]')]) {
        if (!visible(box) || !box.required || box.checked) continue;
        const label = ((box.closest('label, div, fieldset') || {}).innerText || box.value || '').replace(/\s+/g, ' ').trim();
        if ((/consent|privacy|processing of personal data|data will be processed|demographic data|certify|acknowledge|terms/i.test(label)
            || /gdpr_(demographic_data|processing)_consent_given/i.test(box.name || ''))
            && !/future job opportunities|talent community|marketing/i.test(label)) {
          box.click();
          box.dispatchEvent(new Event('input', { bubbles: true }));
          box.dispatchEvent(new Event('change', { bubbles: true }));
          reports.push({ id: box.id || '', name: box.name || '', label: label.slice(0, 160), checked: box.checked });
        }
      }
      return reports;
    });
    if (checkboxReports.length) reports.push({ name: '__required_checkboxes__', type: 'checkbox', label: 'required checkbox consent', value: '', required: true, ok: checkboxReports.every((item) => item.checked), checkboxReports });

    pageState = await inspectPage(page);
    const invalid = await visibleInvalid(page);
    const hardInvalid = invalid.filter((field) => field.required || /requiredInput/.test(field.className));
    const unhandledRequired = reports.filter((r) => r.required && !r.ok);
    const filled = {
      ok: !pageState.danger && hardInvalid.length === 0 && unhandledRequired.length === 0,
      status: 'Filled',
      company,
      role,
      board,
      jobId,
      url: sourceUrl,
      variant,
      reports,
      upload,
      invalid: hardInvalid,
      page: pageState,
    };
    if (!filled.ok) {
      final = {
        ...filled,
        status: pageState.danger ? 'ManualFinish' : 'ManualFinish',
        code: pageState.danger ? 'platform-anti-bot' : 'invalid-or-unhandled-required',
      };
      return final;
    }
    const securityInputCount = await page.locator('input[id^="security-input-"]').count().catch(() => 0);
    if (securityInputCount >= 4 || pageState.needsSecurityCode) {
      final = {
        ok: false,
        status: 'Skipped',
        code: 'skip-email-verification',
        company,
        role,
        board,
        jobId,
        url: sourceUrl,
        variant,
        securityInputCount,
        page: pageState,
      };
      if (args.submit && !args['no-record']) {
        record({
          tracker: TRACKER, ledger: LEDGER, skill: SKILL, stamp: nowCst(), date: todayCst(),
          company, role, url: sourceUrl, submitted: false, status: 'ManualFinish',
          notes: 'manual-finish-needed:skip-email-verification',
          variant,
        });
      }
      return final;
    }
    if (!args.submit || args['dry-run']) {
      final = { ...filled, status: 'DryRunReady' };
      return final;
    }

    const responses = [];
    const failures = [];
    page.on('response', (response) => {
      const req = response.request();
      if (req.method() === 'POST' || /greenhouse|recaptcha|captcha/i.test(response.url())) {
        responses.push({ method: req.method(), url: response.url().slice(0, 220), status: response.status() });
      }
    });
    page.on('requestfailed', (request) => {
      failures.push({ method: request.method(), url: request.url().slice(0, 220), error: request.failure() && request.failure().errorText });
    });
    await humanPause(1400, 3200);
    const submitStarted = Date.now();
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /submit application/i }).first();
    await submitButton.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
    await submitButton.click({ timeout: 20000 });
    await humanPause(6500, 10500);
    pageState = await inspectPage(page);
    if (pageState.needsSecurityCode) {
      const code = await waitForSecurityCode(company, submitStarted);
      if (code) {
        const codeFill = await fillSecurityCode(page, code);
        await humanPause(900, 1800);
        const codeSubmitEnabled = await page.waitForFunction(() => {
          const buttons = [...document.querySelectorAll('button')].filter((button) => /submit/i.test(button.innerText || button.textContent || ''));
          const button = buttons[buttons.length - 1];
          return button && !button.disabled && button.getAttribute('aria-disabled') !== 'true';
        }, { timeout: 15000 }).then(() => true).catch(() => false);
        if (!codeSubmitEnabled) {
          const diagnostic = await submitDiagnostics(page, responses, failures);
          final = { ok: false, status: 'ManualFinish', code: 'security-code-submit-disabled', codeFill: { ...codeFill, codeLen: code.length }, page: diagnostic };
          if (!args['no-record']) record({
            tracker: TRACKER, ledger: LEDGER, skill: SKILL, stamp: nowCst(), date: todayCst(),
            company, role, url: sourceUrl, submitted: false, status: final.status,
            notes: final.code,
            variant,
          });
          return final;
        }
        await page.locator('button[type="submit"], button:has-text("Submit")').last().click({ timeout: 20000 });
        await humanPause(4000, 8000);
        pageState = await inspectPage(page);
      }
    }
    if (pageState.confirmation) {
      if (!args['no-record']) record({
        tracker: TRACKER, ledger: LEDGER, skill: SKILL, stamp: nowCst(), date: todayCst(),
        company, role, url: sourceUrl, submitted: true, status: 'Submitted',
        notes: pageState.needsSecurityCode ? 'verified-greenhouse-confirmation-after-email-code-playwright' : 'verified-greenhouse-confirmation-playwright',
        variant,
      });
      final = { ok: true, status: 'Submitted', company, role, url: sourceUrl, variant, page: pageState };
      return final;
    }
    const diagnostic = await submitDiagnostics(page, responses, failures);
    const postSecurityInputs = (((diagnostic.details || {}).visibleInputs) || [])
      .filter((item) => /^security-input-/i.test(item.id || '')).length;
    const postNeedsSecurity = Boolean(pageState.needsSecurityCode || postSecurityInputs >= 4);
    final = {
      ok: false,
      status: postNeedsSecurity ? 'Skipped' : 'ManualFinish',
      code: postNeedsSecurity ? 'skip-email-verification' : (pageState.danger ? 'platform-anti-bot' : 'submit-unverified'),
      page: diagnostic,
    };
    if (!args['no-record']) record({
      tracker: TRACKER, ledger: LEDGER, skill: SKILL, stamp: nowCst(), date: todayCst(),
      company, role, url: sourceUrl, submitted: false, status: final.status,
      notes: final.code,
      variant,
    });
    return final;
  } finally {
    if (connectedDebugChrome) {
      await page.close().catch(() => {});
    } else {
      await context.close().catch(() => {});
      await browser.close().catch(() => {});
    }
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!process.env.NODE_PATH || !process.env.NODE_PATH.includes('node_modules')) {
    process.env.NODE_PATH = NODE_PATH_HINT;
  }
  const result = await applyOne(args);
  console.log(JSON.stringify(result, null, 2));
  if (result.status === 'Submitted') process.exit(0);
  if (result.status === 'DryRunReady') process.exit(0);
  if (result.status === 'PrecheckReady') process.exit(0);
  if (result.status === 'SecurityPrecheckOk') process.exit(0);
  if (result.status === 'Skipped') process.exit(20);
  if (result.status === 'Blocked') process.exit(30);
  process.exit(10);
}

main().catch((err) => {
  const message = String((err && err.stack) || err || '');
  const code = /Timeout|net::|ERR_|page\.goto|locator\.waitFor/i.test(message) ? 'page-load-or-form-timeout' : 'runner-exception';
  console.log(JSON.stringify({
    ok: false,
    status: 'Blocked',
    code,
    error: message.slice(0, 2000),
  }, null, 2));
  process.exit(30);
});
