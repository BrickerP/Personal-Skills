import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const source = readFileSync(new URL('./codex-wallpaper.zsh', import.meta.url), 'utf8');
const listener = source.slice(source.indexOf('validate_cdp_listener() {'), source.indexOf('listener_state() {'));
const readyTarget = {
  type: 'page', id: 'test', url: 'app://codex/index.html',
  webSocketDebuggerUrl: 'ws://127.0.0.1:9341/devtools/page/test',
};

function classify({ records = 'p123\nn127.0.0.1:9341', owned = true,
  targets = JSON.stringify([readyTarget]) } = {}) {
  const result = spawnSync('/bin/zsh', ['-c', `
    emulate -LR zsh
    setopt nounset pipefail
    PORT=9341
    NODE="$1"
    function /usr/sbin/lsof() { print -rn -- "$RECORDS"; }
    function /usr/bin/curl() { print -rn -- "$TARGETS"; }
    upstream_owns_port() { [[ "$OWNED" == 1 ]]; }
    ${listener}
    validate_cdp_listener
  `, 'test', process.execPath], {
    encoding: 'utf8',
    env: { ...process.env, RECORDS: records, OWNED: owned ? '1' : '0', TARGETS: targets },
  });
  assert.equal(result.signal, null, result.stderr);
  assert.equal(result.stderr, '');
  return result.status;
}

test('trusted listener waits for its app page to appear', () => {
  assert.equal(classify({ targets: '[]' }), 30);
  assert.equal(classify({ targets: '' }), 30);
  assert.equal(classify({ targets: JSON.stringify([{ type: 'page', url: 'about:blank' }]) }), 30);
  assert.equal(classify(), 0);
  assert.equal(classify({ records: 'p123\nn[::1]:9341',
    targets: JSON.stringify([{ ...readyTarget, webSocketDebuggerUrl: 'ws://[::1]:9341/devtools/page/test' }]) }), 0);
});

test('readiness uses the same target identity and URL constraints as the injector', () => {
  for (const id of [undefined, '', '../test', 'other', 'x'.repeat(201)]) {
    assert.equal(classify({ targets: JSON.stringify([{ ...readyTarget, id }]) }), 20);
  }
  for (const url of ['ws://user:pass@127.0.0.1:9341/devtools/page/test',
    'ws://127.0.0.1:9341/devtools/page/test?query=1',
    'ws://127.0.0.1:9341/devtools/page/test#fragment']) {
    assert.equal(classify({ targets: JSON.stringify([{ ...readyTarget, webSocketDebuggerUrl: url }]) }), 20);
  }
});

test('missing, unowned, and non-loopback listeners remain distinct', () => {
  assert.equal(classify({ records: '' }), 10);
  assert.equal(classify({ owned: false }), 20);
  assert.equal(classify({ records: 'p123\nn*:9341' }), 20);
});

test('malformed and unsafe app targets fail closed', () => {
  assert.equal(classify({ targets: '{' }), 20);
  assert.equal(classify({ targets: '{}' }), 20);
  for (const url of ['ws://example.com:9341/devtools/page/test',
    'ws://127.0.0.1:9000/devtools/page/test', 'wss://127.0.0.1:9341/devtools/page/test']) {
    assert.equal(classify({ targets: JSON.stringify([{ ...readyTarget, webSocketDebuggerUrl: url }]) }), 20);
    assert.equal(classify({ targets: JSON.stringify([readyTarget, { ...readyTarget, webSocketDebuggerUrl: url }]) }), 20);
  }
});
