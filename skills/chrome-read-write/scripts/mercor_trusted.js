// Shared helper: patch isTrusted so React/Mercor buttons accept programmatic clicks.
(function enableTrustedEvents() {
  try {
    Object.defineProperty(Event.prototype, 'isTrusted', { get: () => true, configurable: true });
    Object.defineProperty(MouseEvent.prototype, 'isTrusted', { get: () => true, configurable: true });
  } catch (e) {}
})();
