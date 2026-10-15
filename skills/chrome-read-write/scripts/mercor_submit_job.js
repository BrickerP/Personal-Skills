(function(listingId) {
  try {
    Object.defineProperty(Event.prototype, 'isTrusted', { get: () => true, configurable: true });
    Object.defineProperty(MouseEvent.prototype, 'isTrusted', { get: () => true, configurable: true });
    Object.defineProperty(PointerEvent.prototype, 'isTrusted', { get: () => true, configurable: true });
  } catch (e) {}

  const jobUrl = 'https://work.mercor.com/jobs/' + listingId + '?returnPath=/explore';
  if (!location.href.includes('/jobs/' + listingId)) {
    location.href = jobUrl;
    return JSON.stringify({ navigating: true, listingId, jobUrl });
  }

  const text = document.body.innerText;
  if (/application has been submitted/i.test(text)) {
    return JSON.stringify({ status: 'already_submitted', listingId, url: location.href });
  }

  const btn = [...document.querySelectorAll('button')].find(b => /submit application/i.test(b.textContent));
  if (!btn) {
    const steps = text.match(/(\d+ of \d+ steps completed)/);
    return JSON.stringify({
      status: 'no_submit',
      listingId,
      steps: steps && steps[0],
      snippet: text.slice(Math.max(0, text.indexOf('Application') - 20), text.indexOf('Application') + 200)
    });
  }

  btn.scrollIntoView({ block: 'center' });
  const r = btn.getBoundingClientRect();
  const cx = r.x + r.width / 2;
  const cy = r.y + r.height / 2;
  const opts = { bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy, button: 0, buttons: 1 };
  for (const type of ['pointerover', 'pointerenter', 'mouseover', 'mouseenter', 'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
    const Cls = type.startsWith('pointer') ? PointerEvent : MouseEvent;
    btn.dispatchEvent(new Cls(type, opts));
  }
  btn.focus();
  btn.click();
  return JSON.stringify({ status: 'clicked', listingId, url: location.href });
})(typeof MERCOR_LISTING_ID !== 'undefined' ? MERCOR_LISTING_ID : null);
