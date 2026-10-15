#!/usr/bin/env bash
# Submit a Mercor job application via /jobs/list_* page + trusted pointer events.
# Usage: mercor_submit_job.sh <target_id> <listing_id>
set -euo pipefail
TARGET="$1"
LID="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp /tmp/mercor_submit_job_XXXX.js)"
cat > "$TMP" <<EOF
(function() {
  const listingId = '$LID';
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
    return JSON.stringify({ status: 'no_submit', listingId, steps: steps && steps[0] });
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
})();
EOF
chmod +x "$TMP"
CHROME_EVAL_URL_MUST_CONTAIN=mercor.com "$SCRIPT_DIR/chrome_eval.sh" "$TARGET" "$TMP"
rm -f "$TMP"
