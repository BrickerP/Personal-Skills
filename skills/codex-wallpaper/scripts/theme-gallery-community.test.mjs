import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { collectManifest, startGallery } from './theme-gallery.mjs';

test('serves the entire catalog, gates mutations, and refreshes installed themes without applying', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'wallpaper-community-server-'));
  const themesRoot = path.join(root, 'themes');
  const activeTheme = path.join(root, 'active');
  fs.mkdirSync(themesRoot); fs.mkdirSync(activeTheme);
  function save(id) {
    const dir = path.join(themesRoot, id);
    fs.mkdirSync(dir);
    fs.writeFileSync(path.join(dir, 'theme.json'), JSON.stringify({ id, name: id, image: 'background.jpg' }));
    fs.writeFileSync(path.join(dir, 'background.jpg'), Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
  }
  save('existing-theme');
  fs.writeFileSync(path.join(activeTheme, 'theme.json'), JSON.stringify({ id: 'existing-theme' }));
  const activeBefore = fs.readFileSync(path.join(activeTheme, 'theme.json'));
  const remote = Array.from({ length: 753 }, (_, index) => ({
    id: `ver_${index}`, name: `社区主题 ${index}`, themeId: index === 0 ? 'existing-theme' : `remote-${index}`,
    platforms: index === 2 ? ['windows'] : ['macos'], applyCompatible: true, thumbnailAvailable: true,
  }));
  let installs = 0;
  let listCalls = 0;
  const catalog = {
    list: async () => { listCalls++; return { themes: remote, total: remote.length, complete: true, cached: true }; },
    thumbnail: async id => {
      if (!remote.some(theme => theme.id === id)) throw new Error('unknown');
      return { bytes: Buffer.from([0xff, 0xd8, 0xff, 0xd9]), mime: 'image/jpeg' };
    },
  };
  const installer = { install: async () => { installs++; save('remote-1'); return { id: 'remote-1', name: '社区主题 1', duplicate: false }; } };
  const gallery = await startGallery({
    themes: collectManifest(themesRoot, activeTheme), timeoutMs: 5000, openBrowser: false,
    token: 'f'.repeat(64), catalog, installer,
    refreshThemes: () => collectManifest(themesRoot, activeTheme),
  });
  const get = route => fetch(`${gallery.origin}${route}${route.includes('?') ? '&' : '?'}token=${gallery.token}`);
  const post = (route, body, origin = gallery.origin) => fetch(gallery.origin + route, {
    method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json', 'X-Codex-Wallpaper-Token': gallery.token }, body: JSON.stringify(body),
  });
  try {
    assert.equal((await fetch(gallery.origin + '/catalog?token=wrong')).status, 403);
    const response = await get('/catalog');
    assert.equal(response.status, 200);
    const all = await response.json();
    assert.equal(all.total, 753); assert.equal(all.themes.length, 753); assert.equal(all.complete, true);
    assert.equal(all.themes[0].installed, true); assert.equal(all.themes[0].localId, 'existing-theme');
    assert.equal(all.themes[752].name, '社区主题 752');
    assert.equal((await get('/community-thumb/ver_missing')).status, 404);
    assert.equal((await get('/community-thumb/ver_752')).headers.get('content-type'), 'image/jpeg');
    assert.equal((await post('/install', { id: 'ver_1' }, 'http://evil.invalid')).status, 403);
    assert.equal((await post('/install', { id: '../outside' })).status, 400);
    assert.equal((await post('/install', { id: 'ver_missing' })).status, 400);
    assert.equal((await post('/install', { id: 'ver_2' })).status, 400);
    assert.equal(installs, 0);
    assert.equal((await post('/install', { id: 'ver_1' })).status, 200);
    const local = await (await get('/local')).json();
    assert.equal(local.length, 2);
    assert.equal(local.find(theme => theme.id === 'existing-theme').active, true);
    assert(!JSON.stringify(local).includes(root));
    assert.deepEqual(fs.readFileSync(path.join(activeTheme, 'theme.json')), activeBefore);
    assert.equal((await (await post('/install', { id: 'ver_1' })).json()).duplicate, true);
    assert.equal(installs, 1);
    assert.equal(listCalls, 1, 'install should use the displayed catalog without re-fetching all pages');
    assert.equal((await post('/select', { id: 'remote-1' })).status, 200);
    assert.equal(await gallery.result, 'remote-1');
  } finally {
    try { await post('/cancel', {}); } catch {}
    fs.rmSync(root, { recursive: true, force: true });
  }
});
