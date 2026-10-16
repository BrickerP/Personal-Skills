// Pre-submit gate for ATS application forms. Run it in the page right before the final Submit click:
//   chrome-use --session <name> eval --stdin < ~/.codex/skills/daily-job-apply/scripts/ats_pre_submit_gate.js
// It prints one JSON verdict. Submit only when `ok` is true. Anything else is ManualFinish or Blocked,
// never a retry loop. `warnings` do not fail the gate; read each one before submitting.
(() => {
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

  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };
  const labelOf = (el) => clean((el.closest('label,li,div,section,fieldset') || {}).innerText).slice(0, 180);
  const describe = (el) => ({
    name: el.name || '',
    id: el.id || '',
    type: el.type || el.tagName,
    label: labelOf(el),
  });
  const checkboxGroupHasChecked = (el) =>
    el.name &&
    Array.from(document.querySelectorAll('input[type="checkbox"]')).some((o) => o.name === el.name && o.checked);

  const fields = Array.from(document.querySelectorAll('input,textarea,select')).filter(
    (el) => el.type !== 'hidden' && visible(el),
  );

  const invalid = fields
    .filter((el) => !el.checkValidity())
    .filter((el) => !(el.type === 'checkbox' && checkboxGroupHasChecked(el)))
    .map((el) => ({ ...describe(el), required: !!el.required, message: el.validationMessage || '' }));

  const invalidSet = new Set(invalid.map((i) => i.id + '|' + i.name));
  const ariaInvalid = Array.from(document.querySelectorAll('[aria-invalid="true"]'))
    .filter((el) => visible(el))
    .map((el) => describe(el))
    .filter((d) => !invalidSet.has(d.id + '|' + d.name));

  // Custom comboboxes keep their chosen value in a sibling node, so an empty aria-required input is a hint, not proof.
  const emptyAriaRequired = fields
    .filter((el) => el.getAttribute('aria-required') === 'true' && !el.required && !String(el.value || '').trim())
    .map((el) => describe(el));

  const text = clean(document.body ? document.body.innerText : '');
  const matchedDanger = dangerPatterns.map((p) => (p.exec(text) || [])[0]).filter(Boolean);

  const blockers = [];
  if (matchedDanger.length) blockers.push({ code: 'danger-text', matchedDanger });
  if (!fields.length) blockers.push({ code: 'no-form-fields' });
  if (invalid.length) blockers.push({ code: 'invalid-required-fields', invalid });
  if (ariaInvalid.length) blockers.push({ code: 'aria-invalid-fields', ariaInvalid });

  const warnings = [];
  if (emptyAriaRequired.length) warnings.push({ code: 'empty-aria-required', fields: emptyAriaRequired });

  return {
    ok: blockers.length === 0,
    blockers,
    warnings,
    url: location.href,
    title: document.title,
    submitButtons: Array.from(document.querySelectorAll('button,input[type="button"],input[type="submit"]'))
      .map((b) => clean(b.innerText || b.value || ''))
      .filter(Boolean)
      .slice(0, 20),
    textSnippet: blockers.length ? text.slice(0, 500) : undefined,
  };
})()
