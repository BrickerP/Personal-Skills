#!/usr/bin/env bash
# Apply to a Mercor explore listing by ID. Usage: mercor_apply.sh <target_id> <listing_id>
set -euo pipefail
TARGET="$1"
LID="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp /tmp/mercor_apply_XXXX.js)"
cat > "$TMP" <<EOF
(function() {
  try {
    Object.defineProperty(Event.prototype, 'isTrusted', { get: () => true, configurable: true });
    Object.defineProperty(MouseEvent.prototype, 'isTrusted', { get: () => true, configurable: true });
  } catch (e) {}
  const listingId = '$LID';
  if (!location.href.includes(listingId)) {
    location.href = 'https://work.mercor.com/explore?listingId=' + listingId;
    return JSON.stringify({ navigating: true, listingId });
  }
  const text = document.body.innerText;
  if (/application has been submitted/i.test(text)) {
    return JSON.stringify({ status: 'already_submitted', listingId, url: location.href });
  }
  const btn = [...document.querySelectorAll('button')].find(b => /submit application/i.test(b.textContent));
  if (!btn) {
    const steps = text.match(/(\d+ of \d+ steps completed)/);
    return JSON.stringify({ status: 'no_submit', listingId, steps: steps && steps[1], snippet: text.slice(text.indexOf('Application'), text.indexOf('Application')+300) });
  }
  btn.scrollIntoView({ block: 'center' });
  btn.click();
  const steps = text.match(/(\d+ of \d+ steps completed)/);
  return JSON.stringify({ status: 'clicked', listingId, steps: steps && steps[1] });
})();
EOF
CHROME_EVAL_URL_MUST_CONTAIN=mercor.com "$SCRIPT_DIR/chrome_eval.sh" "$TARGET" "$TMP"
rm -f "$TMP"
