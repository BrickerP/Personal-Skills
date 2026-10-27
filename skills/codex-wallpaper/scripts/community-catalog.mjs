import fs from 'node:fs';
import path from 'node:path';

const API_ORIGIN = 'https://api.dreamskin.cc';
const SAFE_VERSION_ID = /^ver_[a-f0-9]{20}$/;
const SAFE_SHA256 = /^[a-f0-9]{64}$/;
const JSON_LIMIT = 4 * 1024 * 1024;
const IMAGE_LIMIT = 12 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 12_000;
const RETRY_DELAYS_MS = [0, 120, 400];
const CACHE_VERSION = 1;

// The catalog and thumbnail hosts are intentionally narrower than “any HTTPS URL”.
const LIST_URL = `${API_ORIGIN}/v1/themes`;
const PAGE_SIZE = 24;
const MAX_CATALOG_THEMES = 10_000;
const API_HOSTS = new Set(['api.dreamskin.cc']);

const FIXED_ERRORS = Object.freeze({
  catalog: '无法获取社区主题目录。',
  unknown: '社区主题不存在或尚未载入目录。',
  thumbnail: '无法获取社区主题缩略图。',
  metadata: '无法验证社区主题信息。',
  incompatible: '主题不兼容当前 macOS 客户端。',
});

class Semaphore {
  constructor(limit) {
    this.limit = limit;
    this.active = 0;
    this.waiters = [];
  }

  async run(task) {
    if (this.active >= this.limit) {
      await new Promise((resolve) => this.waiters.push(resolve));
    }
    this.active += 1;
    try {
      return await task();
    } finally {
      this.active -= 1;
      this.waiters.shift()?.();
    }
  }
}

function fixedError(kind) {
  return new Error(FIXED_ERRORS[kind]);
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function cleanText(value, maximum = 160) {
  if (typeof value !== 'string') return '';
  const cleaned = value.trim().replace(/[\r\n\t]+/g, ' ');
  return cleaned.length <= maximum ? cleaned : '';
}

function cleanStringList(value, allowed) {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((item) => typeof item === 'string' && allowed.has(item)))];
}

function validateOfficialUrl(rawUrl, allowedHosts) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error('unsafe-url');
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.port || !allowedHosts.has(url.hostname)) {
    throw new Error('unsafe-url');
  }
  return url;
}

function normalizeTheme(raw) {
  if (!isObject(raw)) return null;
  const id = cleanText(raw.id ?? raw.versionId, 40);
  const name = cleanText(raw.name, 160);
  const themeId = cleanText(raw.themeId, 160);
  const author = cleanText(raw.author ?? raw.authorDisplayName, 160);
  const displayMeta = isObject(raw.displayMeta) ? raw.displayMeta : {};
  const appearance = cleanText(raw.appearance ?? displayMeta.appearance, 20);
  const platforms = cleanStringList(raw.platforms ?? displayMeta.platforms, new Set(['macos', 'windows', 'linux']));
  if (!SAFE_VERSION_ID.test(id) || !name || !themeId) return null;
  return {
    id,
    name,
    themeId,
    author,
    appearance: ['light', 'dark'].includes(appearance) ? appearance : '',
    platforms,
    applyCompatible: raw.applyCompatible === true,
    thumbnailAvailable: true,
  };
}

function publicTheme(theme) {
  return { ...theme };
}

function normalizeSnapshot(raw) {
  if (!isObject(raw) || !Array.isArray(raw.themes)) throw new Error('invalid-snapshot');
  const seen = new Set();
  const themes = [];
  for (const entry of raw.themes) {
    const theme = normalizeTheme(entry);
    if (!theme || seen.has(theme.id)) continue;
    seen.add(theme.id);
    themes.push(theme);
  }
  const declaredTotal = Number(raw.total);
  if (themes.length > MAX_CATALOG_THEMES || declaredTotal > MAX_CATALOG_THEMES) throw new Error('catalog-too-large');
  const total = Number.isSafeInteger(declaredTotal) && declaredTotal >= themes.length
    ? declaredTotal
    : themes.length;
  return {
    version: CACHE_VERSION,
    savedAt: cleanText(raw.savedAt, 64) || new Date().toISOString(),
    themes,
    total,
    complete: raw.complete === true && themes.length === total,
  };
}

function ensureCacheRoot(cacheRoot) {
  if (typeof cacheRoot !== 'string' || !path.isAbsolute(cacheRoot)) throw new Error('缓存目录必须是绝对路径。');
  fs.mkdirSync(cacheRoot, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(cacheRoot);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('缓存目录无效。');
  return fs.realpathSync(cacheRoot);
}

function readJsonFile(filePath, maximum = JSON_LIMIT) {
  const stat = fs.lstatSync(filePath);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > maximum) throw new Error('invalid-file');
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readOptionalSnapshot(filePath) {
  if (!filePath) return null;
  try {
    return normalizeSnapshot(readJsonFile(filePath));
  } catch {
    return null;
  }
}

function atomicWriteJson(filePath, value) {
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(value)}\n`, { mode: 0o600, flag: 'wx' });
    fs.renameSync(temporary, filePath);
  } finally {
    try { fs.unlinkSync(temporary); } catch {}
  }
}

async function readLimited(response, maximum) {
  const declared = Number(response.headers.get('content-length'));
  if (Number.isFinite(declared) && declared > maximum) throw new Error('response-too-large');
  if (!response.body) return Buffer.alloc(0);
  const chunks = [];
  let size = 0;
  for await (const chunk of response.body) {
    const bytes = Buffer.from(chunk);
    size += bytes.length;
    if (size > maximum) throw new Error('response-too-large');
    chunks.push(bytes);
  }
  return Buffer.concat(chunks, size);
}

function shouldRetry(error) {
  return error?.name === 'AbortError' || error?.retryable === true || error instanceof TypeError;
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fetchOfficial(fetchImpl, rawUrl, {
  allowedHosts,
  expectedTypes,
  maximum,
  errorKind,
}) {
  for (let attempt = 0; attempt < RETRY_DELAYS_MS.length; attempt += 1) {
    if (RETRY_DELAYS_MS[attempt]) await sleep(RETRY_DELAYS_MS[attempt]);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    timer.unref?.();
    try {
      let url = validateOfficialUrl(rawUrl, allowedHosts);
      let redirects = 0;
      while (true) {
        const response = await fetchImpl(url, {
          headers: { Accept: expectedTypes.join(', ') },
          redirect: 'manual',
          signal: controller.signal,
        });
        if ([301, 302, 303, 307, 308].includes(response.status)) {
          if (redirects >= 2) throw new Error('too-many-redirects');
          const location = response.headers.get('location');
          if (!location) throw new Error('bad-redirect');
          try { await response.body?.cancel(); } catch {}
          url = validateOfficialUrl(new URL(location, url).href, allowedHosts);
          redirects += 1;
          continue;
        }
        if (!response.ok) {
          const error = new Error('request-failed');
          error.retryable = response.status === 408 || response.status === 429 || response.status >= 500;
          throw error;
        }
        const contentType = (response.headers.get('content-type') ?? '').split(';', 1)[0].trim().toLowerCase();
        if (!expectedTypes.includes(contentType)) throw new Error('unexpected-content-type');
        return { bytes: await readLimited(response, maximum), contentType };
      }
    } catch (error) {
      if (attempt + 1 >= RETRY_DELAYS_MS.length || !shouldRetry(error)) throw fixedError(errorKind);
    } finally {
      clearTimeout(timer);
    }
  }
  throw fixedError(errorKind);
}

function parseJson(bytes, errorKind) {
  try {
    return JSON.parse(bytes.toString('utf8'));
  } catch {
    throw fixedError(errorKind);
  }
}

function parseCatalogPage(raw, expectedOffset, expectedTotal = null) {
  if (!isObject(raw)
    || !Array.isArray(raw.items)
    || raw.limit !== PAGE_SIZE
    || raw.offset !== expectedOffset
    || !Number.isSafeInteger(raw.total)
    || raw.total < 0
    || raw.total > MAX_CATALOG_THEMES
    || (expectedTotal !== null && raw.total !== expectedTotal)) {
    throw fixedError('catalog');
  }
  const themes = raw.items.map(normalizeTheme).filter(Boolean);
  const expectedLength = Math.min(PAGE_SIZE, Math.max(0, raw.total - expectedOffset));
  return {
    themes,
    valid: themes.length === raw.items.length && raw.items.length === expectedLength,
    total: raw.total,
  };
}

async function mapWithConcurrency(values, concurrency, mapper) {
  const results = new Array(values.length);
  let nextIndex = 0;
  async function worker() {
    while (nextIndex < values.length) {
      const index = nextIndex;
      nextIndex += 1;
      results[index] = await mapper(values[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, values.length) }, () => worker()));
  return results;
}

function imageCachePaths(cacheRoot, id) {
  return {
    body: path.join(cacheRoot, `thumb-${id}.bin`),
    meta: path.join(cacheRoot, `thumb-${id}.json`),
  };
}

function readCachedThumbnail(cacheRoot, id) {
  const files = imageCachePaths(cacheRoot, id);
  try {
    const meta = readJsonFile(files.meta, 1024);
    if (!isObject(meta) || !['image/avif', 'image/jpeg', 'image/png', 'image/webp'].includes(meta.mime)) return null;
    const stat = fs.lstatSync(files.body);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size <= 0 || stat.size > IMAGE_LIMIT) return null;
    return { bytes: fs.readFileSync(files.body), mime: meta.mime };
  } catch {
    return null;
  }
}

function writeCachedThumbnail(cacheRoot, id, result) {
  const files = imageCachePaths(cacheRoot, id);
  const temporary = `${files.body}.${process.pid}.${Date.now()}.tmp`;
  try {
    fs.writeFileSync(temporary, result.bytes, { mode: 0o600, flag: 'wx' });
    fs.renameSync(temporary, files.body);
    atomicWriteJson(files.meta, { mime: result.mime });
  } finally {
    try { fs.unlinkSync(temporary); } catch {}
  }
}

function metadataUrl(id) {
  return `${API_ORIGIN}/v1/themes/${encodeURIComponent(id)}`;
}

function downloadUrl(id) {
  return `${API_ORIGIN}/v1/themes/${encodeURIComponent(id)}/download`;
}

function thumbnailUrl(id) {
  return `${API_ORIGIN}/v1/themes/${encodeURIComponent(id)}/preview/thumbnail?variant=home`;
}

export function createCommunityCatalog({ cacheRoot, seedFile = '', fetchImpl = globalThis.fetch } = {}) {
  if (typeof fetchImpl !== 'function') throw new Error('缺少可用的网络请求实现。');
  const root = ensureCacheRoot(cacheRoot);
  const catalogCacheFile = path.join(root, 'community-catalog.json');
  const seed = seedFile ? readOptionalSnapshot(seedFile) : null;
  let snapshot = readOptionalSnapshot(catalogCacheFile) ?? seed;
  let knownThemes = new Map(snapshot?.themes.map((theme) => [theme.id, theme]) ?? []);
  const imageGate = new Semaphore(4);
  const thumbnailInFlight = new Map();
  let listInFlight = null;

  async function fetchCatalogPage(offset, expectedTotal = null) {
    const url = new URL(LIST_URL);
    url.searchParams.set('limit', String(PAGE_SIZE));
    url.searchParams.set('offset', String(offset));
    const result = await fetchOfficial(fetchImpl, url.href, {
      allowedHosts: API_HOSTS,
      expectedTypes: ['application/json'],
      maximum: JSON_LIMIT,
      errorKind: 'catalog',
    });
    return parseCatalogPage(parseJson(result.bytes, 'catalog'), offset, expectedTotal);
  }

  function staleResult(warning = '社区目录联网更新失败，当前显示缓存内容。') {
    if (!snapshot) throw fixedError('catalog');
    knownThemes = new Map(snapshot.themes.map((theme) => [theme.id, theme]));
    return {
      themes: snapshot.themes.map(publicTheme),
      total: snapshot.total,
      complete: snapshot.complete,
      cached: true,
      stale: true,
      warning,
    };
  }

  async function refreshList() {
    let first;
    try {
      first = await fetchCatalogPage(0);
    } catch {
      return staleResult();
    }

    const offsets = [];
    for (let offset = PAGE_SIZE; offset < first.total; offset += PAGE_SIZE) offsets.push(offset);
    const pages = await mapWithConcurrency(offsets, 4, async (offset) => {
      try {
        return await fetchCatalogPage(offset, first.total);
      } catch {
        return null;
      }
    });
    const seen = new Set();
    const themes = [];
    let valid = first.valid;
    for (const page of [first, ...pages]) {
      if (!page) {
        valid = false;
        continue;
      }
      valid = valid && page.valid;
      for (const theme of page.themes) {
        if (seen.has(theme.id)) {
          valid = false;
          continue;
        }
        seen.add(theme.id);
        themes.push(theme);
      }
    }
    const complete = valid && themes.length === first.total && pages.every(Boolean);
    const remoteSnapshot = {
      version: CACHE_VERSION,
      savedAt: new Date().toISOString(),
      themes,
      total: first.total,
      complete,
    };
    if (!complete && snapshot?.complete) {
      return staleResult('部分社区数据更新失败，当前保留完整缓存目录。');
    }
    knownThemes = new Map(themes.map((theme) => [theme.id, theme]));
    if (complete) {
      snapshot = remoteSnapshot;
      try { atomicWriteJson(catalogCacheFile, remoteSnapshot); } catch {}
    }
    return {
      themes: themes.map(publicTheme),
      total: first.total,
      complete,
      cached: false,
      stale: false,
      warning: complete ? '' : '社区目录未完整载入，请稍后重试。',
    };
  }

  async function list({ refresh = false } = {}) {
    if (snapshot?.complete && refresh !== true) {
      return staleResult('当前显示本地社区目录，刷新后可获取最新主题。');
    }
    if (!listInFlight) listInFlight = refreshList().finally(() => { listInFlight = null; });
    return listInFlight;
  }

  async function thumbnail(id) {
    if (typeof id !== 'string' || !SAFE_VERSION_ID.test(id)) throw fixedError('unknown');
    const theme = knownThemes.get(id);
    if (!theme?.thumbnailAvailable) throw fixedError('unknown');
    const cached = readCachedThumbnail(root, id);
    if (cached) return cached;
    if (thumbnailInFlight.has(id)) return thumbnailInFlight.get(id);
    const request = imageGate.run(async () => {
      const result = await fetchOfficial(fetchImpl, thumbnailUrl(id), {
        allowedHosts: API_HOSTS,
        expectedTypes: ['image/avif', 'image/jpeg', 'image/png', 'image/webp'],
        maximum: IMAGE_LIMIT,
        errorKind: 'thumbnail',
      });
      const thumbnail = { bytes: result.bytes, mime: result.contentType };
      writeCachedThumbnail(root, id, thumbnail);
      return thumbnail;
    }).finally(() => thumbnailInFlight.delete(id));
    thumbnailInFlight.set(id, request);
    return request;
  }

  async function packageInfo(id) {
    if (typeof id !== 'string' || !SAFE_VERSION_ID.test(id) || !knownThemes.has(id)) throw fixedError('unknown');
    const result = await fetchOfficial(fetchImpl, metadataUrl(id), {
      allowedHosts: API_HOSTS,
      expectedTypes: ['application/json'],
      maximum: JSON_LIMIT,
      errorKind: 'metadata',
    });
    const raw = parseJson(result.bytes, 'metadata');
    const displayMeta = isObject(raw?.displayMeta) ? raw.displayMeta : {};
    const rawPlatforms = displayMeta.platforms;
    if (!isObject(raw)
      || raw.id !== id
      || !cleanText(raw.name, 160)
      || !cleanText(raw.themeId, 160)
      || !SAFE_SHA256.test(raw.packageSha256)
      || !Number.isSafeInteger(raw.packageBytes)
      || raw.packageBytes <= 0
      || (rawPlatforms !== undefined && (!Array.isArray(rawPlatforms) || rawPlatforms.some((item) => typeof item !== 'string')))) {
      throw fixedError('metadata');
    }
    if (raw.applyCompatible !== true
      || (Array.isArray(rawPlatforms) && rawPlatforms.length > 0 && !rawPlatforms.includes('macos'))) {
      throw fixedError('incompatible');
    }
    return {
      id,
      name: cleanText(raw.name, 160),
      themeId: cleanText(raw.themeId, 160),
      sha256: raw.packageSha256,
      bytes: raw.packageBytes,
      downloadUrl: downloadUrl(id),
    };
  }

  return Object.freeze({ list, thumbnail, packageInfo });
}

