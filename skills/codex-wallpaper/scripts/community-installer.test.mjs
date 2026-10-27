import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { createCommunityInstaller } from './community-installer.mjs';

const id = 'ver_test-package';
const payload = Buffer.from('validated theme zip test fixture');
const info = {
  id, name: '测试主题', themeId: 'saved-test', bytes: payload.length,
  sha256: crypto.createHash('sha256').update(payload).digest('hex'),
  downloadUrl: `https://api.dreamskin.cc/v1/themes/${id}/download`,
};
const response = bytes => new Response(bytes, { headers: { 'content-type': 'application/zip', 'content-length': String(bytes.length) } });

test('verifies the exact package before import and removes the private download', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'wallpaper-installer-'));
  try {
    let imported = false;
    const installer = createCommunityInstaller({
      catalog: { packageInfo: async () => info }, cacheRoot: root,
      fetchImpl: async (url, options) => { assert.equal(url, info.downloadUrl); assert.equal(options.redirect, 'error'); return response(payload); },
      importImpl: async (archive, value) => {
        assert.deepEqual(await fs.readFile(archive), payload);
        assert.equal((await fs.stat(archive)).mode & 0o777, 0o600);
        assert.equal(value.sha256, info.sha256);
        imported = true;
        return { id: 'saved-test', name: info.name };
      },
    });
    assert.deepEqual(await installer.install(id), { id: 'saved-test', name: info.name });
    assert.equal(imported, true);
    assert.deepEqual(await fs.readdir(root), []);
    installer.close();
    await assert.rejects(installer.install(id), /已关闭/);
  } finally { await fs.rm(root, { recursive: true, force: true }); }
});

test('checksum errors and changed download locations never invoke the importer', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'wallpaper-installer-'));
  try {
    let imported = 0;
    let requested = 0;
    const base = { cacheRoot: root, importImpl: async () => { imported++; }, fetchImpl: async () => { requested++; return response(Buffer.alloc(payload.length)); } };
    await assert.rejects(createCommunityInstaller({ ...base, catalog: { packageInfo: async () => info } }).install(id), /完整性校验失败/);
    await assert.rejects(createCommunityInstaller({ ...base, catalog: { packageInfo: async () => ({ ...info, downloadUrl: 'https://evil.invalid/theme.zip' }) } }).install(id), /下载信息未通过校验/);
    assert.equal(imported, 0);
    assert.equal(requested, 1);
    assert.deepEqual(await fs.readdir(root), []);
  } finally { await fs.rm(root, { recursive: true, force: true }); }
});

test('serializes package writes and cancels an unfinished download when gallery closes', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'wallpaper-installer-'));
  try {
    let started;
    const ready = new Promise(resolve => { started = resolve; });
    const installer = createCommunityInstaller({
      cacheRoot: root, catalog: { packageInfo: async () => info },
      fetchImpl: async (_url, { signal }) => new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
        started();
      }),
      importImpl: async () => { assert.fail('cancelled download must never import'); },
    });
    const first = installer.install(id);
    await ready;
    await assert.rejects(installer.install(id), /另一个主题/);
    installer.close();
    await assert.rejects(first, /下载已取消/);
    assert.deepEqual(await fs.readdir(root), []);
  } finally { await fs.rm(root, { recursive: true, force: true }); }
});
