#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { renderGalleryPage } from './gallery-page.mjs';
import { createCommunityCatalog } from './community-catalog.mjs';
import { createCommunityInstaller } from './community-installer.mjs';

const DEFAULT_IDLE_TIMEOUT_MS = 10 * 60 * 1000;
const COMMUNITY_GALLERY_URL = 'https://dreamskin.cc/gallery';
const SCRIPT_ROOT = path.dirname(fileURLToPath(import.meta.url));
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
const SAFE_IMAGE = /^[A-Za-z0-9][A-Za-z0-9._-]*\.(?:avif|gif|jpe?g|png|webp)$/i;
const MIME = new Map([
  ['.avif', 'image/avif'],
  ['.gif', 'image/gif'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.png', 'image/png'],
  ['.webp', 'image/webp'],
]);

function fail(message) {
  process.stderr.write(`错误：${message}\n`);
  process.exitCode = 1;
}

function parseArgs(argv) {
  const options = { mode: '', themesRoot: '', activeTheme: '', timeoutMs: DEFAULT_IDLE_TIMEOUT_MS };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (['--serve', '--manifest', '--render-html', '--self-test'].includes(arg)) {
      if (options.mode) throw new Error('只能选择一种运行模式。');
      options.mode = arg.slice(2);
    } else if (arg === '--themes-root') {
      options.themesRoot = argv[++index] ?? '';
    } else if (arg === '--active-theme') {
      options.activeTheme = argv[++index] ?? '';
    } else if (arg === '--timeout-ms') {
      options.timeoutMs = Number(argv[++index]);
    } else {
      throw new Error(`未知参数：${arg}`);
    }
  }
  if (!options.mode) throw new Error('缺少运行模式。');
  if (!Number.isInteger(options.timeoutMs) || options.timeoutMs < 50 || options.timeoutMs > 3_600_000) {
    throw new Error('timeout-ms 必须是 50 到 3600000 之间的整数。');
  }
  return options;
}

function readRegularFile(filePath) {
  const stat = fs.lstatSync(filePath);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('不是普通文件');
  return fs.readFileSync(filePath, 'utf8');
}

function readThemeJson(filePath) {
  const value = JSON.parse(readRegularFile(filePath));
  if (!value || typeof value !== 'object') throw new Error('主题 JSON 无效');
  return value;
}

function realDirectory(dirPath) {
  const stat = fs.lstatSync(dirPath);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('不是普通目录');
  return fs.realpathSync(dirPath);
}

export function collectManifest(themesRoot, activeTheme) {
  if (!path.isAbsolute(themesRoot)) throw new Error('主题库路径必须是绝对路径。');
  const rootReal = realDirectory(themesRoot);
  let activeThemeId = '';
  try {
    if (activeTheme && path.isAbsolute(activeTheme)) {
      activeThemeId = String(readThemeJson(path.join(activeTheme, 'theme.json')).id ?? '');
    }
  } catch {
    activeThemeId = '';
  }

  const themes = [];
  for (const id of fs.readdirSync(rootReal).sort()) {
    if (!SAFE_ID.test(id)) continue;
    const themeDir = path.join(rootReal, id);
    try {
      const dirReal = realDirectory(themeDir);
      if (path.dirname(dirReal) !== rootReal) continue;
      const config = readThemeJson(path.join(dirReal, 'theme.json'));
      const imageName = typeof config.image === 'string' ? config.image : '';
      if (!SAFE_IMAGE.test(imageName) || path.basename(imageName) !== imageName) continue;
      const imagePath = path.join(dirReal, imageName);
      const imageStat = fs.lstatSync(imagePath, { bigint: true });
      if (!imageStat.isFile() || imageStat.isSymbolicLink()) continue;
      const imageReal = fs.realpathSync(imagePath);
      if (path.dirname(imageReal) !== dirReal) continue;
      const extension = path.extname(imageReal).toLowerCase();
      const mime = MIME.get(extension);
      if (!mime) continue;
      const name = typeof config.name === 'string' && config.name.trim()
        ? config.name.trim().replace(/[\r\n]+/g, ' ')
        : id;
      themes.push({
        id,
        themeId: String(config.id ?? id),
        name,
        active: Boolean(activeThemeId && String(config.id ?? '') === activeThemeId),
        imagePath: imageReal,
        mime,
        device: imageStat.dev,
        inode: imageStat.ino,
      });
    } catch {
      // Skip malformed, missing, or symlinked themes.
    }
  }
  return themes;
}

export function renderHtml(themes, token, nonce) {
  return renderGalleryPage({ localThemes: publicManifest(themes), token, nonce });
}

function jsonResponse(response, status, body) {
  response.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  response.end(JSON.stringify(body));
}

function requestBody(request) {
  return new Promise((resolve, reject) => {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      body += chunk;
      if (Buffer.byteLength(body) > 4096) reject(new Error('请求过大'));
    });
    request.on('end', () => resolve(body));
    request.on('error', reject);
  });
}

function openVerifiedImage(theme) {
  if (typeof fs.constants.O_NOFOLLOW !== 'number') throw new Error('当前系统不支持 O_NOFOLLOW');
  let fd;
  try {
    fd = fs.openSync(theme.imagePath, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    const stat = fs.fstatSync(fd, { bigint: true });
    if (!stat.isFile() || stat.dev !== theme.device || stat.ino !== theme.inode) {
      throw new Error('缩略图文件身份已改变');
    }
    return { fd, size: stat.size };
  } catch (error) {
    if (fd !== undefined) fs.closeSync(fd);
    throw error;
  }
}

export async function startGallery({ themes, timeoutMs, openBrowser = true, token = crypto.randomBytes(32).toString('hex'), catalog, installer, refreshThemes }) {
  if (!Array.isArray(themes) || themes.length === 0) throw new Error('没有带有效缩略图的主题。');
  let localThemes = themes;
  let catalogSnapshot;
  const themeMap = new Map(themes.map((theme) => [theme.id, theme]));
  if (themeMap.size !== themes.length || [...themeMap.keys()].some((id) => !SAFE_ID.test(id))) {
    throw new Error('主题清单包含无效或重复 ID。');
  }
  function refreshLocal() {
    if (refreshThemes) localThemes = refreshThemes();
    themeMap.clear();
    for (const theme of localThemes) themeMap.set(theme.id, theme);
    return localThemes;
  }
  function localForThemeId(themeId) {
    return localThemes.find(theme => (theme.themeId ?? theme.id) === themeId);
  }
  const nonce = crypto.randomBytes(18).toString('base64');
  let origin = '';
  let settled = false;
  let idleTimer;
  let resolveResult;
  const activeStreams = new Set();
  const result = new Promise((resolve) => { resolveResult = resolve; });

  const finish = (value) => {
    if (settled) return;
    settled = true;
    clearTimeout(idleTimer);
    installer?.close?.();
    for (const stream of activeStreams) stream.destroy();
    server.close(() => resolveResult(value));
    server.closeAllConnections?.();
  };

  const server = http.createServer(async (request, response) => {
    const remote = request.socket.remoteAddress;
    if (!['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(remote)) {
      response.writeHead(403).end(); return;
    }
    if (request.headers.host !== origin.slice('http://'.length)) {
      response.writeHead(400).end(); return;
    }
    const requestOrigin = request.headers.origin;
    if (requestOrigin && requestOrigin !== origin) {
      response.writeHead(403).end(); return;
    }
    const rawUrl = request.url ?? '/';
    if (/%(?:2e|2f|5c)/i.test(rawUrl) || rawUrl.includes('\\')) {
      response.writeHead(400).end(); return;
    }
    const url = new URL(rawUrl, origin);
    const suppliedToken = request.method === 'POST'
      ? request.headers['x-codex-wallpaper-token']
      : url.searchParams.get('token');
    if (suppliedToken !== token) {
      response.writeHead(403, { 'Cache-Control': 'no-store' }).end(); return;
    }

    idleTimer?.refresh?.();

    if (request.method === 'GET' && url.pathname === '/') {
      const html = renderHtml(refreshLocal(), token, nonce);
      response.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Content-Security-Policy': `default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`,
        'Cache-Control': 'no-store',
        'Referrer-Policy': 'no-referrer',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
      });
      response.end(html); return;
    }

    if (request.method === 'GET' && url.pathname === '/local') {
      jsonResponse(response, 200, publicManifest(refreshLocal())); return;
    }
    if (request.method === 'GET' && url.pathname === '/catalog') {
      if (!catalog) { jsonResponse(response, 503, { error: '社区目录暂时不可用。' }); return; }
      try {
        const snapshot = await catalog.list({ refresh: url.searchParams.get('refresh') === '1' });
        catalogSnapshot = snapshot;
        refreshLocal();
        const items = snapshot.themes.map(theme => {
          const local = localForThemeId(theme.themeId);
          return { ...theme, installed: Boolean(local), localId: local?.id ?? null };
        });
        jsonResponse(response, 200, { ...snapshot, themes: items });
      } catch { jsonResponse(response, 502, { error: '社区连接失败，请稍后重试。' }); }
      return;
    }
    const communityThumb = request.method === 'GET' && url.pathname.match(/^\/community-thumb\/(ver_[A-Za-z0-9_-]{1,72})$/);
    if (communityThumb) {
      if (!catalog) { response.writeHead(404).end(); return; }
      try {
        const thumbnail = await catalog.thumbnail(communityThumb[1]);
        response.writeHead(200, {
          'Content-Type': thumbnail.mime,
          'Content-Length': String(thumbnail.bytes.length),
          'Cache-Control': 'private, max-age=86400',
          'X-Content-Type-Options': 'nosniff',
        });
        response.end(thumbnail.bytes);
      } catch { response.writeHead(404).end(); }
      return;
    }
    if (request.method === 'POST' && url.pathname === '/install') {
      if (requestOrigin !== origin || request.headers['content-type'] !== 'application/json') {
        response.writeHead(403).end(); return;
      }
      if (!catalog || !installer) { jsonResponse(response, 503, { error: '社区安装暂时不可用。' }); return; }
      try {
        const body = JSON.parse(await requestBody(request) || '{}');
        if (typeof body.id !== 'string' || !/^ver_[A-Za-z0-9_-]{1,72}$/.test(body.id)) {
          jsonResponse(response, 400, { error: '主题标识无效。' }); return;
        }
        const snapshot = catalogSnapshot ??= await catalog.list();
        const theme = snapshot.themes.find(theme => theme.id === body.id);
        if (!theme) { jsonResponse(response, 400, { error: '该主题不在当前社区目录中，请刷新目录。' }); return; }
        refreshLocal();
        const existing = localForThemeId(theme.themeId);
        if (existing) { jsonResponse(response, 200, { id: existing.id, name: existing.name, duplicate: true }); return; }
        if (theme.applyCompatible !== true || !theme.platforms.includes('macos')) {
          jsonResponse(response, 400, { error: '该主题未标记为适用于当前 macOS 引擎。' }); return;
        }
        const saved = await installer.install(body.id);
        refreshLocal();
        if (!themeMap.has(saved.id)) throw new Error('安装结果未能在本地确认。');
        jsonResponse(response, 200, saved);
      } catch (error) {
        const message = error instanceof Error && /^(主题|社区|下载|图库|另一个|安装)/.test(error.message)
          ? error.message : '安装失败，请稍后重试。';
        jsonResponse(response, 400, { error: message });
      }
      return;
    }

    const thumbMatch = request.method === 'GET' && url.pathname.match(/^\/thumb\/([^/]+)$/);
    if (thumbMatch) {
      let id;
      try { id = decodeURIComponent(thumbMatch[1]); } catch { response.writeHead(400).end(); return; }
      const theme = SAFE_ID.test(id) ? themeMap.get(id) : undefined;
      if (!theme) { response.writeHead(404).end(); return; }
      let opened;
      try {
        opened = openVerifiedImage(theme);
      } catch {
        response.writeHead(404).end(); return;
      }
      let stream;
      try {
        response.writeHead(200, {
          'Content-Type': theme.mime,
          'Content-Length': String(opened.size),
          'Cache-Control': 'no-store',
          'X-Content-Type-Options': 'nosniff',
        });
        stream = fs.createReadStream(null, { fd: opened.fd, autoClose: true });
        opened = undefined;
        activeStreams.add(stream);
        stream.once('close', () => activeStreams.delete(stream));
        stream.once('error', () => response.destroy());
        response.once('close', () => stream.destroy());
        stream.pipe(response);
      } catch {
        if (opened !== undefined) fs.closeSync(opened.fd);
        response.destroy();
      }
      return;
    }

    if (request.method === 'POST' && ['/select', '/cancel'].includes(url.pathname)) {
      if (requestOrigin !== origin || request.headers['content-type'] !== 'application/json') {
        response.writeHead(403).end(); return;
      }
      try {
        const body = JSON.parse(await requestBody(request) || '{}');
        if (url.pathname === '/select') {
          refreshLocal();
          if (typeof body.id !== 'string' || !SAFE_ID.test(body.id) || !themeMap.has(body.id)) {
            jsonResponse(response, 400, { ok: false }); return;
          }
          jsonResponse(response, 200, { ok: true });
          finish(body.id); return;
        }
        jsonResponse(response, 200, { ok: true });
        finish('__CANCEL__'); return;
      } catch {
        jsonResponse(response, 400, { ok: false }); return;
      }
    }
    response.writeHead(404).end();
  });

  await new Promise((resolve, reject) => {
    const onError = (error) => reject(error);
    server.once('error', onError);
    server.listen(0, '127.0.0.1', () => {
      server.off('error', onError);
      resolve();
    });
  });
  server.on('error', () => finish('__SERVER_ERROR__'));
  const address = server.address();
  origin = `http://127.0.0.1:${address.port}`;
  idleTimer = setTimeout(() => finish('__TIMEOUT__'), timeoutMs);
  idleTimer.unref?.();

  if (openBrowser) {
    const opened = spawnSync('/usr/bin/open', [`${origin}/?token=${token}`], { stdio: 'ignore' });
    if (opened.status !== 0 || opened.error) {
      finish('__OPEN_FAILED__');
    }
  }
  return { origin, token, result };
}

function publicManifest(themes) {
  return themes.map(({ id, name, active, mime, themeId }) => ({ id, name, active, mime, themeId }));
}

function httpRequest(origin, method, route, { token = '', requestOrigin = origin, body } = {}) {
  return new Promise((resolve, reject) => {
    const target = new URL(origin);
    const payload = body === undefined ? '' : JSON.stringify(body);
    const request = http.request({
      hostname: target.hostname,
      port: target.port,
      path: route,
      method,
      headers: {
        ...(method === 'POST' ? {
          Origin: requestOrigin,
          'Content-Type': 'application/json',
          'X-Codex-Wallpaper-Token': token,
          'Content-Length': Buffer.byteLength(payload),
        } : {}),
      },
    }, (response) => {
      response.resume();
      response.on('end', () => resolve(response.statusCode));
    });
    request.on('error', reject);
    request.end(payload);
  });
}

function httpGetBody(origin, route) {
  return new Promise((resolve, reject) => {
    const target = new URL(origin);
    const request = http.request({ hostname: target.hostname, port: target.port, path: route, method: 'GET' }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => resolve({ status: response.statusCode, body: Buffer.concat(chunks) }));
    });
    request.on('error', reject);
    request.end();
  });
}

async function selfTest() {
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-wallpaper-gallery-'));
  try {
    const themesRoot = path.join(root, 'themes');
    const activeTheme = path.join(root, 'active');
    fs.mkdirSync(themesRoot);
    fs.mkdirSync(activeTheme);
    const makeTheme = (id, name, configId = id) => {
      const dir = path.join(themesRoot, id);
      fs.mkdirSync(dir);
      fs.writeFileSync(path.join(dir, 'theme.json'), JSON.stringify({ id: configId, name, image: 'background.jpg' }));
      fs.writeFileSync(path.join(dir, 'background.jpg'), Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
      return dir;
    };
    makeTheme('theme-one', '<安全名称>', 'active-config');
    makeTheme('theme-two', '第二张');
    fs.writeFileSync(path.join(activeTheme, 'theme.json'), JSON.stringify({ id: 'active-config' }));
    fs.symlinkSync(path.join(themesRoot, 'theme-one'), path.join(themesRoot, 'theme-link'));
    const linked = makeTheme('linked-image', '链接图片');
    fs.unlinkSync(path.join(linked, 'background.jpg'));
    fs.symlinkSync(path.join(themesRoot, 'theme-one', 'background.jpg'), path.join(linked, 'background.jpg'));

    const themes = collectManifest(themesRoot, activeTheme);
    assert(themes.length === 2, 'manifest 应排除符号链接');
    assert(themes.find((theme) => theme.id === 'theme-one')?.active, 'manifest 应标记当前主题');
    const diagnostics = JSON.stringify(publicManifest(themes));
    assert(!diagnostics.includes(root) && !diagnostics.includes('imagePath'), '公开诊断不得暴露绝对图片路径');
    const html = renderHtml(themes, 'test-token', 'test-nonce');
    assert(html.includes('\\u003c安全名称\\u003e') && !html.includes('<安全名称>'), 'HTML 应转义主题名');
    assert(html.includes(`href="${COMMUNITY_GALLERY_URL}" target="_blank" rel="noopener noreferrer"`), 'HTML 应提供安全的新标签页社区入口');
    assert(html.includes('社区全部') && html.includes('本地已安装'), 'HTML 应区分完整社区与本地库');
    assert(!/https?:\/\/(?!127\.0\.0\.1)/.test(html.replace(COMMUNITY_GALLERY_URL, '')), 'HTML 不应引用其他外部资源');

    const first = await startGallery({ themes, timeoutMs: 2000, openBrowser: false, token: 'a'.repeat(64) });
    assert(await httpRequest(first.origin, 'GET', '/?token=wrong') === 403, '错误 token 应被拒绝');
    assert(await httpRequest(first.origin, 'GET', '/thumb/%2e%2e?token=' + first.token) === 400, '路径穿越应被拒绝');
    assert(await httpRequest(first.origin, 'POST', '/select', { token: first.token, requestOrigin: 'http://evil.invalid', body: { id: 'theme-one' } }) === 403, '无关 Origin 应被拒绝');
    assert(await httpRequest(first.origin, 'POST', '/select', { token: first.token, body: { id: 'unknown' } }) === 400, '未知主题 ID 应被拒绝');
    assert(await httpRequest(first.origin, 'POST', '/select', { token: first.token, body: { id: 'theme-two' } }) === 200, '已知主题 ID 应可选择');
    assert(await first.result === 'theme-two', '选择后应返回 ID 并关闭服务器');
    await new Promise((resolve) => setTimeout(resolve, 30));
    let closed = false;
    try { await httpRequest(first.origin, 'GET', `/?token=${first.token}`); } catch { closed = true; }
    assert(closed, '选择后服务器应退出');

    const second = await startGallery({ themes, timeoutMs: 2000, openBrowser: false, token: 'b'.repeat(64) });
    assert(await httpRequest(second.origin, 'POST', '/cancel', { token: second.token, body: {} }) === 200, '取消请求应成功');
    assert(await second.result === '__CANCEL__', '取消后应返回取消标记并关闭服务器');

    const third = await startGallery({ themes, timeoutMs: 50, openBrowser: false, token: 'c'.repeat(64) });
    assert(await third.result === '__TIMEOUT__', '空闲超时应关闭服务器');

    const raceImage = path.join(themesRoot, 'theme-one', 'background.jpg');
    const safeImage = path.join(root, 'approved-image.jpg');
    const secretImage = path.join(root, 'must-not-leak.jpg');
    fs.linkSync(raceImage, safeImage);
    fs.writeFileSync(secretImage, Buffer.from('SECRET_IMAGE_MUST_NOT_LEAK'));
    const fourth = await startGallery({ themes, timeoutMs: 3000, openBrowser: false, token: 'd'.repeat(64) });
    const togglerCode = `
      const fs = require('node:fs');
      const [target, approved, secret] = process.argv.slice(1);
      const end = Date.now() + 1200;
      let index = 1;
      const first = target + '.swap';
      try { fs.unlinkSync(first); } catch {}
      fs.symlinkSync(secret, first);
      fs.renameSync(first, target);
      process.stdout.write('READY\\n');
      while (Date.now() < end) {
        const next = target + '.swap';
        try { fs.unlinkSync(next); } catch {}
        if (index++ % 2) fs.symlinkSync(secret, next); else fs.linkSync(approved, next);
        fs.renameSync(next, target);
      }
    `;
    const toggler = spawn(process.execPath, ['-e', togglerCode, raceImage, safeImage, secretImage], {
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    await new Promise((resolve, reject) => {
      toggler.stdout.once('data', (chunk) => chunk.toString().includes('READY') ? resolve() : reject(new Error('换链进程未就绪')));
      toggler.once('error', reject);
    });
    assert(toggler.exitCode === null, '换链进程应与缩略图请求并发运行');
    const raceResponses = await Promise.all(Array.from({ length: 120 }, () =>
      httpGetBody(fourth.origin, `/thumb/theme-one?token=${fourth.token}`)));
    await new Promise((resolve) => {
      if (toggler.exitCode !== null) resolve();
      else { toggler.once('close', resolve); toggler.kill('SIGTERM'); }
    });
    assert(raceResponses.every(({ status, body }) =>
      status === 404 || (status === 200 && body.equals(Buffer.from([0xff, 0xd8, 0xff, 0xd9])))),
    '并发换链时不得返回链向文件内容');
    assert(await httpRequest(fourth.origin, 'POST', '/cancel', { token: fourth.token, body: {} }) === 200, '换链测试后应可取消');
    assert(await fourth.result === '__CANCEL__', '换链测试服务器应正常退出');
    process.stdout.write('theme-gallery self-test: PASS\n');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === 'self-test') {
    await selfTest();
    return;
  }
  if (!options.themesRoot) throw new Error('缺少 --themes-root。');
  const themes = collectManifest(options.themesRoot, options.activeTheme);
  if (options.mode === 'manifest') {
    process.stdout.write(`${JSON.stringify(publicManifest(themes), null, 2)}\n`);
    return;
  }
  if (options.mode === 'render-html') {
    process.stdout.write(renderHtml(themes, 'TEST_TOKEN', 'TEST_NONCE'));
    return;
  }
  const cacheRoot = path.join(os.homedir(), 'Library', 'Application Support', 'CodexWallpaper', 'community');
  const catalog = createCommunityCatalog({ cacheRoot, seedFile: path.join(SCRIPT_ROOT, 'community-catalog.seed.json') });
  const installer = createCommunityInstaller({ catalog, cacheRoot, wrapperPath: path.join(SCRIPT_ROOT, 'codex-wallpaper.zsh') });
  const gallery = await startGallery({
    themes, timeoutMs: options.timeoutMs, catalog, installer,
    refreshThemes: () => collectManifest(options.themesRoot, options.activeTheme),
  });
  const selected = await gallery.result;
  if (selected === '__OPEN_FAILED__') throw new Error('无法打开壁纸缩略图页面。');
  if (selected === '__SERVER_ERROR__') throw new Error('壁纸缩略图服务器异常退出。');
  process.stdout.write(`${selected}\n`);
}

let directExecution = false;
try { directExecution = fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url); } catch {}
if (directExecution) {
  main().catch((error) => fail(error instanceof Error ? error.message : String(error)));
}
