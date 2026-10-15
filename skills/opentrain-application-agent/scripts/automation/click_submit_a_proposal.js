(() => {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const candidates = [...document.querySelectorAll("button, [role='button'], a")];
  const matches = candidates.filter((b) => {
    const x = norm(b.textContent);
    if (!x) return false;
    if (/submit\s+a\s*proposal|continue\s+proposal/i.test(x)) return true;
    if (/^\s*Submit a Proposal/i.test(x) || /^\s*Continue Proposal/i.test(x)) return true;
    return false;
  });
  let btn =
    matches.find((b) => {
      const r = b.getBoundingClientRect();
      return r.width > 4 && r.height > 4 && r.top < innerHeight + 600 && r.bottom > -400;
    }) || matches[0];
  if (!btn) return "no_submit_a_proposal";

  const firePointerClick = (el) => {
    try {
      el.scrollIntoView({ block: "center", behavior: "instant" });
    } catch (_) {}
    try {
      el.focus({ preventScroll: true });
    } catch (_) {}
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const opts = {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: cx,
      clientY: cy,
      button: 0,
    };
    el.dispatchEvent(new PointerEvent("pointerdown", opts));
    el.dispatchEvent(new MouseEvent("mousedown", opts));
    el.dispatchEvent(new PointerEvent("pointerup", opts));
    el.dispatchEvent(new MouseEvent("mouseup", opts));
    el.dispatchEvent(new MouseEvent("click", opts));
    if (typeof el.click === "function") el.click();
  };

  firePointerClick(btn);
  // Some layouts nest the handler on a wrapper
  if (btn.parentElement && btn.parentElement !== document.body) {
    firePointerClick(btn.parentElement);
  }

  return "ok";
})();
