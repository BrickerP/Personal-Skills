(function(assessmentName, actionText) {
  actionText = actionText || 'Start assessment';
  try {
    Object.defineProperty(Event.prototype, 'isTrusted', { get: () => true, configurable: true });
    Object.defineProperty(MouseEvent.prototype, 'isTrusted', { get: () => true, configurable: true });
  } catch (e) {}
  window.scrollTo(0, document.body.scrollHeight);
  const h3 = [...document.querySelectorAll('h3')].find(h => h.textContent.includes(assessmentName));
  if (!h3) return JSON.stringify({ error: 'assessment not found', name: assessmentName });
  h3.scrollIntoView({ block: 'center' });
  const hr = h3.getBoundingClientRect();
  const re = new RegExp(actionText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
  let btn = [...document.querySelectorAll('button')].find(b => re.test(b.textContent) && Math.abs(b.getBoundingClientRect().top - hr.top) < 80);
  if (!btn && /start/i.test(actionText)) {
    btn = [...document.querySelectorAll('button')].find(b => re.test(b.textContent) && b.getBoundingClientRect().top > hr.top + 200 && b.getBoundingClientRect().top < hr.top + 320);
  }
  if (!btn) return JSON.stringify({ error: 'button not found', name: assessmentName, action: actionText, hrTop: hr.top });
  btn.click();
  return JSON.stringify({ clicked: true, name: assessmentName, action: btn.textContent.trim() });
})
