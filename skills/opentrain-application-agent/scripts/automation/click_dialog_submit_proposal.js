(() => {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const dlg = document.querySelector("[role=dialog]");
  const scope = dlg || document;
  const btn = [...scope.querySelectorAll("button, [role=button]")].find((b) => {
    const x = norm(b.textContent);
    return /^Submit Proposal$/i.test(x) && !b.disabled;
  });
  if (!btn) return "no_dialog_submit";
  const opts = { bubbles: true, cancelable: true, view: window };
  try {
    btn.scrollIntoView({ block: "center", behavior: "instant" });
  } catch (_) {}
  btn.dispatchEvent(new PointerEvent("pointerdown", opts));
  btn.dispatchEvent(new MouseEvent("click", opts));
  if (typeof btn.click === "function") btn.click();
  return "ok";
})();
