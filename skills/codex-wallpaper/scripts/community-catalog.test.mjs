import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createCommunityCatalog } from './community-catalog.mjs';

const ID = 'ver_eed14dc8b609177f1649';
const SHA256 = '36715df6b934daa067c636efe5c28c55ce3beb41922d61ba204661430d43d7c2';

function fixture(overrides = {}) {
  return {
    id: ID,
    name: 'Alpha Lock',
    themeId: 'alpha-lock',
    authorDisplayName: 'Alpha',
    applyCompatible: true,
    displayMeta: { platforms: ['macos'], appearance: 'light' },
    packageSha256: SHA256,
    packageBytes: 2311530,
    ...overrides,
  };
}

function makeWorkspace(t, { seed = true, themes = [fixture()] } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'community-catalog-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const cacheRoot = path.join(root, 'cache');
  const seedFile = path.join(root, 'seed.json');
  if (seed) {
    fs.writeFileSync(seedFile, JSON.stringify({
      total: themes.length,
      complete: true,
      themes,
    }));
  }
  return { root, cacheRoot, ...(seed ? { seedFile } : {}) };
}

function jsonResponse(value, init = {}) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    ...init,
  });
}

function themeAt(index, overrides = {}) {
  const suffix = index.toString(16).padStart(20, '0');
  return fixture({
    id: `ver_${suffix}`,
    name: `Theme ${index}`,
    themeId: `theme-${index}`,
    ...overrides,
  });
}

function pageAt(offset, total, overrides = {}) {
  const count = Math.min(24, Math.max(0, total - offset));
  return {
    items: Array.from({ length: count }, (_, index) => themeAt(offset + index)),
    limit: 24,
    offset,
    total,
    ...overrides,
  };
}

test('seed catalog remains usable offline and is clearly marked stale', async (t) => {
  const workspace = makeWorkspace(t);
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => { throw new TypeError('offline'); },
  });
  const result = await catalog.list();
  assert.equal(result.total, 1);
  assert.equal(result.themes.length, 1);
  assert.equal(result.themes[0].id, ID);
  assert.equal(result.complete, true);
  assert.equal(result.cached, true);
  assert.equal(result.stale, true);
  assert.match(result.warning, /本地/);
});

test('packageInfo fetches only the fixed official metadata endpoint', async (t) => {
  const workspace = makeWorkspace(t);
  const requests = [];
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (url, options) => {
      requests.push({ url: String(url), options });
      return jsonResponse(fixture());
    },
  });
  const info = await catalog.packageInfo(ID);
  assert.deepEqual(info, {
    id: ID,
    name: 'Alpha Lock',
    themeId: 'alpha-lock',
    sha256: SHA256,
    bytes: 2311530,
    downloadUrl: `https://api.dreamskin.cc/v1/themes/${ID}/download`,
  });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, `https://api.dreamskin.cc/v1/themes/${ID}`);
  assert.equal(requests[0].options.redirect, 'manual');
});

test('unknown IDs and arbitrary URLs are rejected before network access', async (t) => {
  const workspace = makeWorkspace(t);
  let requests = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => { requests += 1; return jsonResponse(fixture()); },
  });
  await assert.rejects(catalog.packageInfo('ver_00000000000000000000'), /不存在/);
  await assert.rejects(catalog.packageInfo('https://127.0.0.1/private'), /不存在/);
  await assert.rejects(catalog.thumbnail('https://evil.invalid/image.png'), /不存在/);
  assert.equal(requests, 0);
});

test('metadata redirects to non-allowlisted hosts are rejected', async (t) => {
  const workspace = makeWorkspace(t);
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => new Response('', {
      status: 302,
      headers: { Location: 'https://127.0.0.1/private', 'Content-Type': 'text/plain' },
    }),
  });
  await assert.rejects(catalog.packageInfo(ID), /无法验证/);
});

test('incompatible and malformed packages fail closed', async (t) => {
  const workspace = makeWorkspace(t);
  const replies = [
    fixture({ displayMeta: { platforms: ['windows'], appearance: 'light' } }),
    fixture({ applyCompatible: false }),
    fixture({ packageSha256: 'bad' }),
  ];
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => jsonResponse(replies.shift()),
  });
  await assert.rejects(catalog.packageInfo(ID), /不兼容/);
  await assert.rejects(catalog.packageInfo(ID), /不兼容/);
  await assert.rejects(catalog.packageInfo(ID), /无法验证/);
});

test('a complete local catalog is reused until refresh is explicitly requested', async (t) => {
  const workspace = makeWorkspace(t);
  let requests = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl) => {
      requests += 1;
      const offset = Number(new URL(rawUrl).searchParams.get('offset'));
      return jsonResponse(pageAt(offset, 1));
    },
  });
  assert.equal((await catalog.list()).cached, true);
  assert.equal((await catalog.list()).cached, true);
  assert.equal(requests, 0);
  const refreshed = await catalog.list({ refresh: true });
  assert.equal(refreshed.cached, false);
  assert.equal(refreshed.complete, true);
  assert.equal(requests, 1);
});

test('an incomplete refresh preserves the full browsable cache', async (t) => {
  const themes = Array.from({ length: 48 }, (_, index) => themeAt(index));
  const workspace = makeWorkspace(t, { themes });
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async rawUrl => {
      const offset = Number(new URL(rawUrl).searchParams.get('offset'));
      return offset === 0 ? jsonResponse(pageAt(0, 48)) : new Response('', { status: 404 });
    },
  });
  const result = await catalog.list({ refresh: true });
  assert.equal(result.themes.length, 48);
  assert.equal(result.total, 48);
  assert.equal(result.complete, true);
  assert.equal(result.cached, true);
  assert.match(result.warning, /保留完整缓存/);
  assert.equal((await catalog.list()).themes[47].name, 'Theme 47');
});

test('rejects an excessive catalog total before constructing pagination work', async (t) => {
  const workspace = makeWorkspace(t, { seed: false });
  let requests = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => {
      requests++;
      return jsonResponse(pageAt(0, 24, { total: Number.MAX_SAFE_INTEGER }));
    },
  });
  await assert.rejects(catalog.list(), /无法获取社区主题目录/);
  assert.equal(requests, 1);
});

test('metadata response type and size are validated without exposing response data', async (t) => {
  const workspace = makeWorkspace(t);
  const secret = 'DO_NOT_EXPOSE_RESPONSE';
  let attempt = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => {
      attempt += 1;
      if (attempt === 1) {
        return new Response(secret, { status: 200, headers: { 'Content-Type': 'text/html' } });
      }
      return new Response('{}', {
        status: 200,
        headers: { 'Content-Type': 'application/json', 'Content-Length': String(5 * 1024 * 1024) },
      });
    },
  });
  await assert.rejects(catalog.packageInfo(ID), (error) => {
    assert.equal(error.message, '无法验证社区主题信息。');
    assert.ok(!error.message.includes(secret));
    return true;
  });
  await assert.rejects(catalog.packageInfo(ID), /无法验证/);
});

test('list loads every page, deduplicates by ID, and reports a complete catalog', async (t) => {
  const workspace = makeWorkspace(t, { seed: false });
  const offsets = [];
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl) => {
      const url = new URL(rawUrl);
      assert.equal(url.origin + url.pathname, 'https://api.dreamskin.cc/v1/themes');
      assert.equal(url.searchParams.get('limit'), '24');
      const offset = Number(url.searchParams.get('offset'));
      offsets.push(offset);
      return jsonResponse(pageAt(offset, 50));
    },
  });
  const result = await catalog.list();
  assert.deepEqual(offsets.sort((left, right) => left - right), [0, 24, 48]);
  assert.equal(result.themes.length, 50);
  assert.equal(new Set(result.themes.map(({ id }) => id)).size, 50);
  assert.equal(result.total, 50);
  assert.equal(result.complete, true);
  assert.equal(result.cached, false);
  assert.equal(result.stale, false);
  assert.equal(result.warning, '');
  assert.equal('thumbnailUrl' in result.themes[0], false);
});

test('a failed page returns a partial catalog and never claims completeness', async (t) => {
  const workspace = makeWorkspace(t, { seed: false });
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl) => {
      const offset = Number(new URL(rawUrl).searchParams.get('offset'));
      if (offset === 24) throw new TypeError('network failure');
      return jsonResponse(pageAt(offset, 50));
    },
  });
  const result = await catalog.list();
  assert.equal(result.themes.length, 26);
  assert.equal(result.total, 50);
  assert.equal(result.complete, false);
  assert.equal(result.cached, false);
  assert.match(result.warning, /未完整/);
});

test('catalog page requests never exceed four concurrent fetches', async (t) => {
  const workspace = makeWorkspace(t, { seed: false });
  let active = 0;
  let maximumActive = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl) => {
      const offset = Number(new URL(rawUrl).searchParams.get('offset'));
      active += 1;
      maximumActive = Math.max(maximumActive, active);
      await new Promise((resolve) => setTimeout(resolve, 15));
      active -= 1;
      return jsonResponse(pageAt(offset, 121));
    },
  });
  const result = await catalog.list();
  assert.equal(result.complete, true);
  assert.equal(result.themes.length, 121);
  assert.ok(maximumActive <= 4, `observed ${maximumActive} concurrent requests`);
});

test('duplicates and inconsistent totals make the result incomplete', async (t) => {
  const workspace = makeWorkspace(t, { seed: false });
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl) => {
      const offset = Number(new URL(rawUrl).searchParams.get('offset'));
      const page = pageAt(offset, 25);
      if (offset === 24) page.items[0] = themeAt(0);
      return jsonResponse(page);
    },
  });
  const result = await catalog.list();
  assert.equal(result.complete, false);
  assert.equal(result.themes.length, 24);
});

test('thumbnail derives a fixed official URL and uses the disk cache', async (t) => {
  const workspace = makeWorkspace(t);
  const image = Buffer.from([0x52, 0x49, 0x46, 0x46]);
  const requests = [];
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async (rawUrl, options) => {
      requests.push({ url: String(rawUrl), options });
      return new Response(image, { status: 200, headers: { 'Content-Type': 'image/webp' } });
    },
  });
  const first = await catalog.thumbnail(ID);
  const second = await catalog.thumbnail(ID);
  assert.deepEqual(first, { bytes: image, mime: 'image/webp' });
  assert.deepEqual(second, first);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, `https://api.dreamskin.cc/v1/themes/${ID}/preview/thumbnail?variant=home`);
  assert.equal(requests[0].options.redirect, 'manual');
});

test('thumbnail rejects redirects outside the official API host', async (t) => {
  const workspace = makeWorkspace(t);
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => new Response('', {
      status: 302,
      headers: { Location: 'https://localhost/private.png' },
    }),
  });
  await assert.rejects(catalog.thumbnail(ID), /无法获取社区主题缩略图/);
});

test('thumbnail requests never exceed four concurrent fetches', async (t) => {
  const themes = Array.from({ length: 9 }, (_, index) => themeAt(index));
  const workspace = makeWorkspace(t, { themes });
  let active = 0;
  let maximumActive = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => {
      active += 1;
      maximumActive = Math.max(maximumActive, active);
      await new Promise((resolve) => setTimeout(resolve, 15));
      active -= 1;
      return new Response(Buffer.from([1, 2, 3]), {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      });
    },
  });
  await Promise.all(themes.map(({ id }) => catalog.thumbnail(id)));
  assert.ok(maximumActive <= 4, `observed ${maximumActive} concurrent requests`);
});

test('concurrent requests for one thumbnail share a single fetch', async (t) => {
  const workspace = makeWorkspace(t);
  let requests = 0;
  const catalog = createCommunityCatalog({
    ...workspace,
    fetchImpl: async () => {
      requests += 1;
      await new Promise((resolve) => setTimeout(resolve, 10));
      return new Response(Buffer.from([1]), {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      });
    },
  });
  await Promise.all(Array.from({ length: 8 }, () => catalog.thumbnail(ID)));
  assert.equal(requests, 1);
});

