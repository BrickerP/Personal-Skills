import assert from 'node:assert/strict';
import test from 'node:test';

import { getPlatformStatus, renderGalleryPage } from './gallery-page.mjs';

test('renders community-first gallery with same-origin catalog and install flows', () => {
  const html = renderGalleryPage({
    localThemes: [{ id: 'local-one', name: '本地主题', active: true, mime: 'image/jpeg' }],
    token: 'test-token',
    nonce: 'test-nonce',
  });

  assert.match(html, /class="tab active"[^>]+data-tab="community"/);
  assert.match(html, /社区全部/);
  assert.match(html, /本地已安装/);
  assert.match(html, /const PAGE_SIZE=48/);
  assert.match(html, /id="show-all"[^>]*>显示全部/);
  assert.match(html, /state\.visible=filteredItems\(\)\.length/);
  assert.match(html, /apiUrl\('\/catalog'\)/);
  assert.match(html, /id="refresh-catalog"[^>]*>刷新目录/);
  assert.match(html, /apiUrl\('\/catalog'\)\+\(force\?'&refresh=1':'\'\)/);
  assert.match(html, /retry-catalog'\)\.addEventListener\('click',\(\)=>loadCatalog\(true\)\)/);
  assert.match(html, /refresh-catalog'\)\.addEventListener\('click',\(\)=>loadCatalog\(true\)\)/);
  assert.match(html, /render\(\);loadCatalog\(\);/);
  assert.match(html, /'\/community-thumb\/'/);
  assert.match(html, /jsonFetch\('\/install'/);
  assert.match(html, /jsonFetch\(apiUrl\('\/local'\)\)/);
  assert.match(html, /submit\('\/select'/);
  assert.match(html, /loading='lazy'|image\.loading='lazy'/);
  assert.match(html, /textContent/);
  assert.doesNotMatch(html, /fetch\(['"]https?:/);

  const script = html.match(/<script nonce="[^"]+">([\s\S]*)<\/script>/)?.[1];
  assert.ok(script);
  assert.doesNotThrow(() => new Function(script));
});

test('keeps non-macOS catalog entries visible but blocks their installation', () => {
  const html = renderGalleryPage({ localThemes: [], token: 'token', nonce: 'nonce' });

  assert.match(html, /function supportsMacOs\(theme\)/);
  assert.match(html, /!supportsMacOs\(theme\)/);
  assert.match(html, /仅其他平台/);
  assert.match(html, /平台待确认/);
  assert.match(html, /button\.disabled=installing\|\|installed\|\|!macCompatible/);
  assert.doesNotMatch(html, /state\.catalog=.*filter\([^\n]*supportsMacOs/);
});

test('requires an exact macos platform declaration', () => {
  assert.equal(getPlatformStatus(['macos']), 'macos');
  assert.equal(getPlatformStatus(['windows', 'linux']), 'other');
  assert.equal(getPlatformStatus([]), 'unknown');
  assert.equal(getPlatformStatus(undefined), 'unknown');
  assert.equal(getPlatformStatus(['android']), 'unknown');
  assert.equal(getPlatformStatus(['MacOS']), 'unknown');
  assert.equal(getPlatformStatus('macos'), 'unknown');
});

test('serializes untrusted local metadata without creating markup or ending the script', () => {
  const attack = '</script><img src=x onerror=alert(1)>';
  const html = renderGalleryPage({
    localThemes: [{ id: 'evil', name: attack, active: false, mime: 'image/png' }],
    token: attack,
    nonce: 'nonce" onload="alert(1)',
  });

  assert.doesNotMatch(html, /<img src=x/);
  assert.doesNotMatch(html, /nonce="nonce" onload=/);
  assert.match(html, /\\u003c\/script\\u003e\\u003cimg/);
  assert.match(html, /nonce="nonce&quot; onload=&quot;alert\(1\)"/);
});

test('rejects invalid render inputs', () => {
  assert.throws(() => renderGalleryPage({ localThemes: null, token: 'x', nonce: 'y' }), /localThemes/);
  assert.throws(() => renderGalleryPage({ localThemes: [], token: null, nonce: 'y' }), /token/);
});
