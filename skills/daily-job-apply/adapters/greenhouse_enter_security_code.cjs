const CDP = require('chrome-remote-interface');

const [targetId, code] = process.argv.slice(2);
if (!targetId || !code) {
  console.error('usage: node greenhouse_enter_security_code.cjs <targetId> <securityCode>');
  process.exit(2);
}

async function main() {
  const entry = (await CDP.List({ host: '127.0.0.1', port: 9222 })).find((t) => t.id === targetId);
  if (!entry) throw new Error(`target not found: ${targetId}`);
  const client = await CDP({ host: '127.0.0.1', port: 9222, target: entry });
  const { Runtime } = client;
  await Runtime.enable();
  const result = (await Runtime.evaluate({
    awaitPromise: true,
    returnByValue: true,
    expression: `(async () => {
      const code = ${JSON.stringify(code)};
      const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
      const visible = (el) => {
        const st = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return st.display !== 'none' && st.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      };
      const setNative = (el, value) => {
        const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
      };
      const inputs = [...document.querySelectorAll('input')].filter(visible);
      const splitFields = inputs
        .filter((el) => /^security-input-\\d+$/.test(el.id || ''))
        .sort((a, b) => Number((a.id || '').split('-').pop()) - Number((b.id || '').split('-').pop()));
      if (splitFields.length >= code.length) {
        splitFields.slice(0, code.length).forEach((field, index) => {
          field.focus();
          setNative(field, code[index]);
        });
        await new Promise((resolve) => setTimeout(resolve, 600));
        const buttons = [...document.querySelectorAll('button,input[type=submit]')]
          .filter(visible)
          .map((el) => ({ text: clean(el.innerText || el.value), disabled: !!el.disabled, aria: el.getAttribute('aria-disabled'), type: el.type || '' }));
        return { ok: true, url: location.href, field: { id: 'security-input-*', type: 'split-code', valueLength: code.length }, buttons };
      }
      const field = inputs.find((el) => /security|code|verification/i.test(clean((el.closest('label,div,fieldset') || {}).innerText) + ' ' + el.id + ' ' + el.name + ' ' + (el.placeholder || ''))) || inputs[inputs.length - 1];
      if (!field) {
        return {
          ok: false,
          code: 'field-not-found',
          inputs: inputs.map((el) => ({ id: el.id, name: el.name, type: el.type, placeholder: el.placeholder, label: clean((el.closest('label,div,fieldset') || {}).innerText).slice(0, 120) })),
        };
      }
      field.scrollIntoView({ block: 'center' });
      field.focus();
      setNative(field, code);
      await new Promise((resolve) => setTimeout(resolve, 600));
      const buttons = [...document.querySelectorAll('button,input[type=submit]')]
        .filter(visible)
        .map((el) => ({ text: clean(el.innerText || el.value), disabled: !!el.disabled, aria: el.getAttribute('aria-disabled'), type: el.type || '' }));
      return { ok: true, url: location.href, field: { id: field.id, name: field.name, type: field.type, valueLength: field.value.length }, buttons };
    })()`,
  })).result.value;
  await client.close();
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
