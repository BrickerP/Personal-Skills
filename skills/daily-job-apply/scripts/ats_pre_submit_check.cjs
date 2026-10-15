#!/usr/bin/env node
const CDP = require('/Users/yupeng/.codex/skills/chrome-read-write/scripts/.cdp-deps/node_modules/chrome-remote-interface');

const targetId = process.argv[2];
if (!targetId) {
  console.error('usage: ats_pre_submit_check.cjs <target_id>');
  process.exit(2);
}

const host = process.env.CHROME_CDP_HOST || '127.0.0.1';
const port = Number(process.env.CHROME_CDP_PORT || '9222');
const gmailNeedle = process.env.JOB_APPLY_GMAIL || 'yplmicro@gmail.com';

const dangerPatterns = [
  /possible spam/i,
  /couldn['’]?t submit your application/i,
  /could not submit/i,
  /error verifying your application/i,
  /verify your application/i,
  /security verification/i,
  /unusual traffic/i,
  /automated queries/i,
  /are you a robot/i,
  /too many attempts/i,
  /captcha/i,
  /hcaptcha/i,
  /sms verification/i,
  /phone verification/i,
];

function summarize(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().slice(0, 500);
}

async function windowIdFor(target) {
  const client = await CDP({ target, host, port });
  try {
    const win = await client.Browser.getWindowForTarget({ targetId: target.id || target });
    return win.windowId;
  } finally {
    await client.close();
  }
}

async function main() {
  const list = await CDP.List({ host, port });
  const pages = list.filter((t) => t.type === 'page');
  const target = pages.find((t) => t.id === targetId);
  if (!target) {
    console.error(JSON.stringify({ ok: false, code: 'target-not-found', targetId }));
    process.exit(2);
  }

  const gmail = pages.find(
    (t) =>
      t.url.includes('mail.google.com') &&
      t.title.includes(gmailNeedle),
  );
  if (!gmail) {
    console.error(JSON.stringify({ ok: false, code: 'gmail-window-not-found', gmailNeedle }));
    process.exit(11);
  }

  const [targetWindowId, gmailWindowId] = await Promise.all([
    windowIdFor(target),
    windowIdFor(gmail),
  ]);
  if (targetWindowId !== gmailWindowId) {
    console.error(
      JSON.stringify({
        ok: false,
        code: 'wrong-window',
        targetId,
        targetWindowId,
        gmailWindowId,
        targetTitle: target.title,
        targetUrl: target.url,
        gmailTitle: gmail.title,
      }),
    );
    process.exit(10);
  }

  const client = await CDP({ target, host, port });
  let page;
  try {
    const { Runtime } = client;
    await Runtime.enable();
    const result = await Runtime.evaluate({
      returnByValue: true,
      expression: `(() => {
        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const visible = (el) => {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
        };
        const checkboxGroupHasChecked = (el) => el.name
          && Array.from(document.querySelectorAll('input[type="checkbox"]')).some((other) => other.name === el.name && other.checked);
        const invalid = Array.from(document.querySelectorAll('input,textarea,select'))
          .filter((el) => el.type !== 'hidden' && visible(el) && !el.checkValidity())
          .filter((el) => !(el.type === 'checkbox' && checkboxGroupHasChecked(el)))
          .map((el) => ({
            name: el.name || '',
            id: el.id || '',
            type: el.type || el.tagName,
            required: !!el.required,
            message: el.validationMessage || '',
            label: clean((el.closest('label,li,div,section,fieldset') || {}).innerText).slice(0, 180),
          }));
        return {
          url: location.href,
          title: document.title,
          text: clean(document.body ? document.body.innerText : ''),
          invalid,
          submitButtons: Array.from(document.querySelectorAll('button,input[type="button"],input[type="submit"]'))
            .map((b) => clean(b.innerText || b.value || ''))
            .filter(Boolean)
            .slice(0, 20),
        };
      })()`,
    });
    if (result.exceptionDetails) {
      console.error(JSON.stringify({ ok: false, code: 'page-eval-error', details: result.exceptionDetails }));
      process.exit(3);
    }
    page = result.result.value;
  } finally {
    await client.close();
  }

  const matchedDanger = dangerPatterns
    .map((pattern) => pattern.exec(page.text || '')?.[0])
    .filter(Boolean);
  if (matchedDanger.length) {
    console.error(
      JSON.stringify({
        ok: false,
        code: 'danger-text',
        matchedDanger,
        targetId,
        targetWindowId,
        gmailWindowId,
        title: page.title,
        url: page.url,
        textSnippet: summarize(page.text),
      }),
    );
    process.exit(12);
  }

  if (page.invalid.length) {
    console.error(
      JSON.stringify({
        ok: false,
        code: 'invalid-required-fields',
        invalid: page.invalid,
        targetId,
        title: page.title,
        url: page.url,
      }),
    );
    process.exit(13);
  }

  console.log(
    JSON.stringify({
      ok: true,
      targetId,
      windowId: targetWindowId,
      title: page.title,
      url: page.url,
      submitButtons: page.submitButtons,
    }),
  );
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, code: 'exception', message: String(err && err.stack || err) }));
  process.exit(1);
});
