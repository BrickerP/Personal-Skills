#!/usr/bin/env node
// wezterm-bg — WezTerm 壁纸选择器
// 用法: wezterm-bg list | current | set <名字> | off | brightness <0.05-1> | gallery
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import crypto from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';

const HOME = os.homedir();
const STATE = path.join(HOME, '.config/wezterm/background.conf');
const LOCAL_DIR = path.join(HOME, '.config/wezterm/backgrounds');
const DREAM_DIR = path.join(HOME, 'Library/Application Support/CodexDreamSkinStudio/themes');
const IMG_RE = /\.(jpe?g|png|webp|gif|bmp|tiff)$/i;

function readState() {
  const s = { file: '', display: '', brightness: 0.4, subtle: 'on' };
  try {
    for (const line of fs.readFileSync(STATE, 'utf8').split('\n')) {
      const m = line.match(/^(\w+)=(.*)$/);
      if (!m) continue;
      if (m[1] === 'file') s.file = m[2];
      if (m[1] === 'display') s.display = m[2];
      if (m[1] === 'subtle') s.subtle = m[2];
      if (m[1] === 'brightness') s.brightness = Number(m[2]) || s.brightness;
    }
  } catch {}
  return s;
}

function writeState(s) {
  fs.mkdirSync(path.dirname(STATE), { recursive: true });
  const body = `file=${s.file}\ndisplay=${s.display}\nbrightness=${s.brightness}\nsubtle=${s.subtle}\n`;
  fs.writeFileSync(STATE, body, 'utf8');
}

function themeLabel(dirName) {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(DREAM_DIR, dirName, 'theme.json'), 'utf8'));
    if (j && typeof j.name === 'string' && j.name.trim()) return j.name.trim();
  } catch {}
  return dirName;
}

function collect() {
  const items = [];
  // 1) 手动放的图
  try {
    for (const f of fs.readdirSync(LOCAL_DIR).sort()) {
      if (!IMG_RE.test(f)) continue;
      const p = path.join(LOCAL_DIR, f);
      try { if (!fs.statSync(p).isFile()) continue; } catch { continue; }
      items.push({ id: f.replace(IMG_RE, ''), name: f.replace(IMG_RE, ''), file: p, source: 'local' });
    }
  } catch {}
  // 2) Dream Skin 主题库（自动出现新主题）
  try {
    for (const d of fs.readdirSync(DREAM_DIR).sort()) {
      const dir = path.join(DREAM_DIR, d);
      let img = null;
      try { img = fs.readdirSync(dir).find((f) => IMG_RE.test(f)) || null; } catch { continue; }
      if (!img) continue;
      items.push({ id: d, name: themeLabel(d), file: path.join(dir, img), source: 'dreamskin' });
    }
  } catch {}
  return items;
}

const LUM_CACHE = path.join(HOME, '.cache/wezterm-bg/luminance.json');

function measureLuminance(file) {
  try {
    const st = fs.statSync(file);
    const key = `${file}|${st.size}|${Math.round(st.mtimeMs)}`;
    let cache = {};
    try { cache = JSON.parse(fs.readFileSync(LUM_CACHE, 'utf8')); } catch {}
    if (typeof cache[key] === 'number') return cache[key];
    const tmp = path.join(os.tmpdir(), `wezterm-bg-${process.pid}.bmp`);
    execFileSync('sips', ['-z', '1', '1', '-s', 'format', 'bmp', file, '--out', tmp], { stdio: 'ignore' });
    const buf = fs.readFileSync(tmp);
    fs.unlinkSync(tmp);
    const b = buf[54], g = buf[55], r = buf[56];
    const mean = (b + g + r) / 765;
    cache[key] = mean;
    fs.mkdirSync(path.dirname(LUM_CACHE), { recursive: true });
    fs.writeFileSync(LUM_CACHE, JSON.stringify(cache));
    return mean;
  } catch { return 0.4; }
}

// 让图片压暗到"平均亮度 ~0.08"，保证浅色图也能看清浅色文字
function suggestBrightness(mean, subtle) {
  const target = subtle ? 0.07 : 0.08;
  const cap = subtle ? 0.45 : 0.60;
  const v = target / Math.max(mean, 0.01);
  return Math.round(Math.min(cap, Math.max(0.06, v)) * 100) / 100;
}

function sha1short(str) {
  return crypto.createHash('sha1').update(str).digest('hex').slice(0, 16);
}

// 生成"柔和版"：强模糊 + 降对比/降饱和（ffmpeg），无 ffmpeg 时退回 sips 缩放模糊
function subtleImage(src) {
  try {
    const st = fs.statSync(src);
    const key = sha1short(`${src}|${st.size}|${Math.round(st.mtimeMs)}|v3`);
    const dir = path.join(HOME, '.cache/wezterm-bg/subtle');
    const out = path.join(dir, `${key}.jpg`);
    if (fs.existsSync(out)) return out;
    fs.mkdirSync(dir, { recursive: true });

    const ffmpeg = [
      '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', 'ffmpeg',
    ].find((p) => {
      try { execFileSync(p, ['-version'], { stdio: 'ignore' }); return true; } catch { return false; }
    });
    if (ffmpeg) {
      execFileSync(ffmpeg, ['-y', '-loglevel', 'error', '-i', src,
        '-vf', 'gblur=sigma=30,eq=contrast=0.55:brightness=-0.08:saturation=0.75',
        '-q:v', '3', out], { stdio: 'ignore' });
      return out;
    }

    // 退路：缩小再放大模拟模糊
    const info = execFileSync('sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', src], { encoding: 'utf8' });
    const w = Number((info.match(/pixelWidth:\s*(\d+)/) || [])[1]) || 1600;
    const h = Number((info.match(/pixelHeight:\s*(\d+)/) || [])[1]) || 900;
    const sw = Math.max(48, Math.round(w / 20));
    const sh = Math.max(27, Math.round(h / 20));
    const tmp = path.join(dir, `${key}.small.jpg`);
    execFileSync('sips', ['-z', String(sh), String(sw), src, '--out', tmp], { stdio: 'ignore' });
    execFileSync('sips', ['-z', String(h), String(w), tmp, '--out', out], { stdio: 'ignore' });
    try { fs.unlinkSync(tmp); } catch {}
    return out;
  } catch { return src; }
}

function findItem(query) {
  const items = collect();
  const q = query.toLowerCase();
  let m = items.filter((i) => i.id.toLowerCase() === q);
  if (m.length === 1) return m[0];
  m = items.filter((i) => i.name.toLowerCase() === q);
  if (m.length === 1) return m[0];
  m = items.filter((i) => i.name.toLowerCase().includes(q) || i.id.toLowerCase().includes(q));
  if (m.length === 1) return m[0];
  if (m.length > 1) throw new Error(`“${query}” 匹配到多个：\n` + m.map((i) => `  - ${i.name}  (${i.id})`).join('\n'));
  throw new Error(`找不到壁纸：${query}`);
}

function currentLine() {
  const s = readState();
  if (!s.file) return '当前壁纸：无（纯色背景）';
  const hit = collect().find((i) => i.file === s.file);
  return `当前壁纸：${hit ? hit.name + '  (' + hit.id + ')' : s.file}\n亮度：${s.brightness}`;
}

function usage() {
  console.log(`wezterm-bg — WezTerm 壁纸选择器

  wezterm-bg list                 列出所有可用壁纸
  wezterm-bg current              显示当前壁纸
  wezterm-bg set <名字或ID>        切换壁纸（支持唯一子串匹配）
  wezterm-bg off                  关闭壁纸（纯色背景）
  wezterm-bg brightness <0.05-1>  调亮度（0.2 很暗，0.7 很亮）
  wezterm-bg subtle on|off         柔和模式（模糊化，降低抢眼程度）
  wezterm-bg gallery              打开可视化选择器（浏览器画廊）

壁纸来源：
  ${LOCAL_DIR}
  ${DREAM_DIR}/*/background.*（Dream Skin 主题库，自动同步）`);
}

function openGallery() {
  const items = collect();
  const token = crypto.randomBytes(16).toString('hex');
  const state0 = readState();
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (!url.pathname.startsWith(`/${token}/`)) { res.writeHead(404); res.end('not found'); return; }
    const sub = url.pathname.slice(token.length + 2);
    if (req.method === 'GET' && sub === '') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(page(items, token, state0));
      return;
    }
    if (req.method === 'GET' && sub.startsWith('img/')) {
      const i = Number(sub.slice(4));
      const it = items[i];
      if (!it) { res.writeHead(404); res.end(); return; }
      const ext = path.extname(it.file).toLowerCase();
      const mime = ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : 'image/jpeg';
      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
      fs.createReadStream(it.file).pipe(res);
      return;
    }
    if (req.method === 'POST' && (sub === 'apply' || sub === 'brightness' || sub === 'off' || sub === 'subtle')) {
      let body = '';
      req.on('data', (c) => (body += c));
      req.on('end', () => {
        try {
          const s = readState();
          if (sub === 'off') { s.file = ''; s.display = ''; }
          else if (sub === 'subtle') {
            const on = !!JSON.parse(body || '{}').on;
            s.subtle = on ? 'on' : 'off';
            s.display = on && s.file ? subtleImage(s.file) : '';
            if (s.file) s.brightness = suggestBrightness(measureLuminance(s.file), on);
          }
          else if (sub === 'brightness') {
            const v = Number(JSON.parse(body || '{}').brightness);
            if (!(v >= 0.05 && v <= 1)) throw new Error('brightness out of range');
            s.brightness = Math.round(v * 100) / 100;
          } else {
            const i = Number(JSON.parse(body || '{}').index);
            const it = items[i];
            if (!it) throw new Error('bad index');
            s.file = it.file;
            s.brightness = suggestBrightness(measureLuminance(it.file), s.subtle !== 'off');
            s.display = s.subtle === 'off' ? '' : subtleImage(it.file);
          }
          writeState(s);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, state: s }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: false, error: String(e.message || e) }));
        }
      });
      return;
    }
    res.writeHead(404); res.end();
  });
  const idle = setTimeout(() => { console.log('画廊空闲 15 分钟，已关闭'); server.close(); process.exit(0); }, 15 * 60 * 1000);
  server.listen(0, '127.0.0.1', () => {
    const port = server.address().port;
    const url = `http://127.0.0.1:${port}/${token}/`;
    console.log(`壁纸画廊：${url}（Ctrl+C 退出）`);
    if (process.env.WEZTERM_BG_NO_OPEN !== '1') {
      spawn('open', [url], { stdio: 'ignore', detached: true }).unref();
    }
  });
  process.on('SIGINT', () => { clearTimeout(idle); server.close(); process.exit(0); });
}

function page(items, token, state0) {
  const data = items.map((i, idx) => ({ idx, name: i.name, id: i.id, source: i.source, file: i.file }));
  return `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>WezTerm 壁纸选择器</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0f1115; color: #e8e8e8; font: 14px/1.5 -apple-system, "PingFang SC", sans-serif; }
  header { position: sticky; top: 0; backdrop-filter: blur(12px); background: rgba(15,17,21,.82); padding: 14px 20px; display: flex; gap: 18px; align-items: center; border-bottom: 1px solid #262a33; z-index: 5; }
  h1 { font-size: 16px; margin: 0; font-weight: 600; }
  .muted { color: #8b93a3; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; padding: 20px; }
  .card { position: relative; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid transparent; background: #171a21; transition: transform .15s, border-color .15s; }
  .card:hover { transform: translateY(-2px); border-color: #3b6cf6; }
  .card.active { border-color: #4ade80; }
  .card img { width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; background: #222; }
  .meta { position: absolute; inset: auto 0 0 0; padding: 26px 12px 10px; background: linear-gradient(transparent, rgba(0,0,0,.85)); font-size: 13px; }
  .meta small { display: block; color: #9aa3b2; font-size: 11px; }
  .badge { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,.6); border: 1px solid #333; border-radius: 999px; padding: 2px 8px; font-size: 11px; color: #9aa3b2; }
  button { font: inherit; background: #232838; color: #e8e8e8; border: 1px solid #333a4d; border-radius: 8px; padding: 6px 12px; cursor: pointer; }
  button:hover { background: #2c3347; }
  input[type=range] { width: 160px; }
</style></head><body>
<header>
  <h1>WezTerm 壁纸</h1>
  <span class="muted" id="cur"></span>
  <label class="muted"><input id="subtle" type="checkbox"> 柔和（模糊化）</label>
  <label class="muted">亮度 <input id="bright" type="range" min="0.05" max="1" step="0.05" value="0.4"><span id="bv">0.4</span></label>
  <button id="off">关闭壁纸</button>
  <span class="muted">共 ${items.length} 张</span>
</header>
<div class="grid" id="grid"></div>
<script>
const items = ${JSON.stringify(data)};
let current = null;
const grid = document.getElementById('grid');
for (const it of items) {
  const el = document.createElement('div');
  el.className = 'card';
  el.innerHTML = '<img loading="lazy" src="/${token}/img/' + it.idx + '" alt=""><div class="meta">' + esc(it.name) + '<small>' + (it.source === 'dreamskin' ? 'Dream Skin' : '本地') + ' · ' + esc(it.id) + '</small></div>';
  el.onclick = () => apply(it.idx);
  grid.appendChild(el);
}
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
async function apply(idx) {
  const r = await fetch('/${token}/apply', { method: 'POST', body: JSON.stringify({ index: idx }) });
  const j = await r.json();
  if (!j.ok) { alert(j.error); return; }
  paint(j.state.file);
}
async function off() {
  const r = await fetch('/${token}/off', { method: 'POST', body: '{}' });
  const j = await r.json(); if (j.ok) paint('');
}
async function setBrightness(v) {
  await fetch('/${token}/brightness', { method: 'POST', body: JSON.stringify({ brightness: v }) });
}
function paint(file) {
  document.querySelectorAll('.card').forEach((c, i) => c.classList.toggle('active', !!file && items[i].file === file));
  document.getElementById('cur').textContent = file ? '当前：' + (items.find(i => i.file === file)?.name || '自定义') : '当前：纯色';
}
document.getElementById('off').onclick = off;
const sb = document.getElementById('subtle');
sb.checked = ${JSON.stringify(state0.subtle !== 'off')};
sb.onchange = async () => {
  await fetch('/${token}/subtle', { method: 'POST', body: JSON.stringify({ on: sb.checked }) });
};
const b = document.getElementById('bright');
b.oninput = () => { document.getElementById('bv').textContent = b.value; };
b.onchange = () => setBrightness(Number(b.value));
paint(${JSON.stringify(state0.file)});
</script></body></html>`;
}

// ---- CLI ----
try {
  const [cmd, ...rest] = process.argv.slice(2);
  switch (cmd) {
    case 'list': {
      const items = collect();
      const s = readState();
      if (!items.length) { console.log('没有壁纸。把图片放进 ' + LOCAL_DIR); break; }
      for (const i of items) {
        const mark = i.file === s.file ? '*' : ' ';
        console.log(`${mark} ${i.name}  (${i.id})${i.source === 'dreamskin' ? '' : '  [local]'}`);
      }
      console.log(`\n共 ${items.length} 张；* = 当前`);
      break;
    }
    case 'current': console.log(currentLine()); break;
    case 'set': {
      if (!rest[0]) { console.error('用法: wezterm-bg set <名字或ID>'); process.exit(1); }
      const it = findItem(rest.join(' '));
      const s = readState();
      s.file = it.file;
      if (!rest.includes('--keep')) {
        const mean = measureLuminance(it.file);
        s.brightness = suggestBrightness(mean, s.subtle !== 'off');
      }
      s.display = s.subtle === 'off' ? '' : subtleImage(it.file);
      writeState(s);
      console.log(`已切换到：${it.name}  (${it.id})  亮度 ${s.brightness}${s.display ? '  柔和模式' : ''}`);
      break;
    }
    case 'subtle': {
      const mode = rest[0];
      if (mode !== 'on' && mode !== 'off') { console.error('用法: wezterm-bg subtle on|off'); process.exit(1); }
      const s = readState();
      s.subtle = mode;
      s.display = mode === 'on' && s.file ? subtleImage(s.file) : '';
      if (s.file) s.brightness = suggestBrightness(measureLuminance(s.file), mode === 'on');
      writeState(s);
      console.log(`柔和模式已${mode === 'on' ? '开启' : '关闭'}`);
      break;
    }
    case 'off': {
      const s = readState();
      s.file = '';
      writeState(s);
      console.log('已关闭壁纸（纯色背景）');
      break;
    }
    case 'brightness': {
      const v = Number(rest[0]);
      if (!(v >= 0.05 && v <= 1)) { console.error('亮度范围 0.05 - 1'); process.exit(1); }
      const s = readState();
      s.brightness = v;
      writeState(s);
      console.log(`亮度已设为 ${v}`);
      break;
    }
    case 'gallery': openGallery(); break;
    case '':
    case '-h':
    case '--help':
    case 'help': usage(); break;
    default:
      console.error('未知命令：' + cmd); usage(); process.exit(1);
  }
} catch (e) {
  console.error('错误：' + (e.message || e));
  process.exit(1);
}
