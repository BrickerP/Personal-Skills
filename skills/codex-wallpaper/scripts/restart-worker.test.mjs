import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const scriptPath = new URL('./codex-wallpaper.zsh', import.meta.url);
const source = readFileSync(scriptPath, 'utf8');

function extractFunction(name, nextName) {
  const start = source.indexOf(`\n${name}() {`);
  const end = source.indexOf(`\n${nextName}() {`, start + 1);
  assert.notEqual(start, -1, `${name} must exist in codex-wallpaper.zsh`);
  assert.notEqual(end, -1, `${nextName} must follow ${name}`);
  return source.slice(start + 1, end);
}

const restartWorker = extractFunction('restart_worker', 'restart_worker_exit');
const restartWorkerExit = extractFunction('restart_worker_exit', 'schedule_restart_apply')
  .replace(
    /  \/usr\/bin\/osascript -e 'display notification[^\n]+\n      >\/dev\/null 2>&1 \|\| true\n/,
    '  : # notification suppressed by isolated test\n',
  );
const showRestartStatus = extractFunction('show_restart_status', 'show_status');

test('nested worker failure records one cleanup with the live worker identity', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'codex-wallpaper-restart-test-'));
  try {
    const nonce = path.join(root, 'nonce');
    const events = path.join(root, 'events');
    const operation = 'a'.repeat(32);
    const token = 'b'.repeat(32);
    const theme = 'test-theme';
    writeFileSync(nonce, `${operation}\n${theme}\n${token}\nscheduler\n999\ntest-birth`, { mode: 0o600 });

    const harness = `
emulate -LR zsh
setopt errexit nounset pipefail
typeset -g RESTART_WORKER_ID=''
typeset -g RESTART_LOCK_TOKEN=''
typeset -g RESTART_OPERATION_ID=''
typeset -g RESTART_OWNER_TUPLE=''
typeset -g APPLY_RESULT_NOTE=''

die() { return 1 }
claim_restart_lock() { RESTART_OWNER_TUPLE="worker-owner-$$" }
worker_wait_for_go() { return 0 }
write_restart_state() { print -r -- "state:$2" >> "$TEST_EVENTS" }
require_mutation_runtime() { return 0 }
archive_dir() { print -r -- /isolated/theme }
fail_before_switch() { die 'isolated failure before switch' }
validate_payload() { fail_before_switch }
find_chatgpt_main() { print -r -- 999 }
switch_without_apply() { return 0 }
inject_active_once() { return 0 }
read_theme_name() { print -r -- test }

restart_worker_exit() {
  print -r -- "cleanup:$1:$RESTART_OWNER_TUPLE:$$" >> "$TEST_EVENTS"
}

${restartWorker}
restart_worker "$TEST_THEME" "$TEST_NONCE" "$TEST_OPERATION" "$TEST_TOKEN"
`;

    const result = spawnSync('/bin/zsh', ['-c', harness], {
      encoding: 'utf8',
      env: {
        PATH: '/usr/bin:/bin:/usr/sbin:/sbin',
        TEST_EVENTS: events,
        TEST_NONCE: nonce,
        TEST_OPERATION: operation,
        TEST_THEME: theme,
        TEST_TOKEN: token,
      },
    });

    assert.equal(result.status, 1, result.stderr);
    const lines = readFileSync(events, 'utf8').trim().split('\n');
    assert.deepEqual(lines.slice(0, 2), ['state:scheduled', 'state:running']);
    assert.equal(lines.length, 3, `cleanup must run exactly once; events: ${lines.join(', ')}`);
    assert.match(lines[2], /^cleanup:1:worker-owner-(\d+):\1$/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('worker cleanup writes failure and releases its lock only once', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'codex-wallpaper-cleanup-test-'));
  try {
    const events = path.join(root, 'events');
    const harness = `
emulate -LR zsh
setopt errexit nounset pipefail
typeset -g RESTART_WORKER_CLEANED=0
typeset -g RESTART_OWNER_TUPLE="worker-owner-$$"
typeset -g RESTART_WORKER_ID=test-theme
write_restart_state() { print -r -- "state:$2:$1:$$" >> "$TEST_EVENTS" }
release_restart_lock() { print -r -- "release:$1:$$" >> "$TEST_EVENTS" }
${restartWorkerExit}
restart_worker_exit 1
restart_worker_exit 1
`;
    const result = spawnSync('/bin/zsh', ['-c', harness], {
      encoding: 'utf8',
      env: { PATH: '/usr/bin:/bin:/usr/sbin:/sbin', TEST_EVENTS: events },
    });

    assert.equal(result.status, 0, result.stderr);
    const lines = readFileSync(events, 'utf8').trim().split('\n');
    assert.equal(lines.length, 2, `cleanup must be idempotent; events: ${lines.join(', ')}`);
    assert.match(lines[0], /^state:failed:worker-owner-(\d+):\1$/);
    assert.match(lines[1], /^release:worker-owner-(\d+):\1$/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

for (const [label, separator] of [['actual tabs', '\t'], ['legacy escaped tabs', '\\t']]) {
test(`status derives a failure for a dead worker recorded with ${label}`, () => {
  const root = mkdtempSync(path.join(tmpdir(), 'codex-wallpaper-status-test-'));
  try {
    const state = path.join(root, 'restart-status');
    const owner = path.join(root, 'owner');
    const operation = 'c'.repeat(32);
    const token = 'd'.repeat(32);
    const theme = 'test-theme';
    const originalState = ['running', '2026-10-17T00:00:00Z', theme, 'working'].join(separator) + '\n';
    writeFileSync(state, originalState, { mode: 0o600 });
    writeFileSync(owner, `${operation}\n${theme}\n${token}\nworker\n999999\ndead-birth`, { mode: 0o600 });

    const harness = `
emulate -LR zsh
setopt nounset pipefail
RESTART_STATE="$TEST_STATE"
RESTART_LOCK_OWNER="$TEST_OWNER"
read_owner_tuple() { /bin/cat "$RESTART_LOCK_OWNER" }
valid_owner_tuple() { return 0 }
process_birth() { return 1 }
${showRestartStatus}
show_restart_status
`;
    const result = spawnSync('/bin/zsh', ['-c', harness], {
      encoding: 'utf8',
      env: {
        PATH: '/usr/bin:/bin:/usr/sbin:/sbin',
        TEST_OWNER: owner,
        TEST_STATE: state,
      },
    });

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /最近一次重启任务：failed\t2026-10-17T00:00:00Z\ttest-theme\t任务进程已退出，未记录应用成功/);
    assert.equal(readFileSync(state, 'utf8'), originalState, 'status must not rewrite restart state');
    assert.equal(readFileSync(owner, 'utf8'), `${operation}\n${theme}\n${token}\nworker\n999999\ndead-birth`);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
}

test('status keeps running when the recorded worker identity is still live', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'codex-wallpaper-live-status-test-'));
  try {
    const state = path.join(root, 'restart-status');
    const owner = path.join(root, 'owner');
    const operation = 'e'.repeat(32);
    const token = 'f'.repeat(32);
    const originalState = 'running\t2026-10-17T00:00:00Z\ttest-theme\tworking\n';
    writeFileSync(state, originalState, { mode: 0o600 });
    writeFileSync(owner, `${operation}\ntest-theme\n${token}\nworker\n12345\nlive-birth`, { mode: 0o600 });
    const harness = `
emulate -LR zsh
setopt nounset pipefail
RESTART_STATE="$TEST_STATE"
RESTART_LOCK_OWNER="$TEST_OWNER"
read_owner_tuple() { /bin/cat "$RESTART_LOCK_OWNER" }
valid_owner_tuple() { return 0 }
process_birth() { print -r -- live-birth }
${showRestartStatus}
show_restart_status
`;
    const result = spawnSync('/bin/zsh', ['-c', harness], {
      encoding: 'utf8',
      env: { PATH: '/usr/bin:/bin:/usr/sbin:/sbin', TEST_OWNER: owner, TEST_STATE: state },
    });

    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, `最近一次重启任务：${originalState}`);
    assert.equal(readFileSync(state, 'utf8'), originalState);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
