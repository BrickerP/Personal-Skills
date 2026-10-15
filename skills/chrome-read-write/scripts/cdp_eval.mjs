#!/usr/bin/env node
import CDP from 'chrome-remote-interface';
import fs from 'fs';
import path from 'path';

const [, , targetId, jsPath] = process.argv;
if (!targetId || !jsPath) {
  console.error('usage: cdp_eval.mjs <target_id> <js_file>');
  process.exit(2);
}

const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222', 10);
const mustContain = process.env.CHROME_EVAL_URL_MUST_CONTAIN || '';
const activate = process.env.CHROME_EVAL_ACTIVATE === '1';

const absJs = path.resolve(jsPath);
if (!fs.existsSync(absJs)) {
  console.error(`js file not found: ${absJs}`);
  process.exit(2);
}
const jsText = fs.readFileSync(absJs, 'utf8');

const list = await CDP.List({ host, port });
const entry =
  list.find((t) => t.id === targetId) ||
  list.find((t) => t.type === 'page' && t.id === targetId);
if (!entry) {
  console.error(`cdp_eval: target not found: ${targetId}`);
  process.exit(2);
}

const client = await CDP({ target: entry, host, port });
try {
  const { Runtime, Page } = client;
  await Runtime.enable();
  if (activate && Page) {
    try {
      await Page.bringToFront();
    } catch {
      /* optional */
    }
  }

  if (mustContain) {
    const check = await Runtime.evaluate({
      expression: 'location.href',
      returnByValue: true,
    });
    const href = String(check.result?.value ?? '');
    if (!href.includes(mustContain)) {
      console.error(
        `cdp_eval: refusing JS: URL must contain '${mustContain}', got: ${href}`,
      );
      process.exit(3);
    }
  }

  const result = await Runtime.evaluate({
    expression: jsText,
    awaitPromise: true,
    returnByValue: true,
  });

  if (result.exceptionDetails) {
    console.error(JSON.stringify(result.exceptionDetails, null, 2));
    process.exit(1);
  }

  const value = result.result?.value;
  if (typeof value === 'string') {
    process.stdout.write(value);
    if (!value.endsWith('\n')) process.stdout.write('\n');
  } else if (value === undefined) {
    process.stdout.write('\n');
  } else {
    console.log(JSON.stringify(value));
  }
} finally {
  await client.close();
}
