(() => {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const dlg = document.querySelector("[role=dialog]");
  const scope = dlg || document;
  const btn = [...scope.querySelectorAll("button, [role=button]")].find((b) => {
    const x = norm(b.textContent);
    return /Start Live Chat Interview/i.test(x) && !b.disabled;
  });
  if (!btn) return "no_dialog_start_chat";
  try {
    btn.scrollIntoView({ block: "center", behavior: "instant" });
  } catch (_) {}
  const opts = { bubbles: true, cancelable: true, view: window };
  btn.dispatchEvent(new PointerEvent("pointerdown", opts));
  btn.dispatchEvent(new MouseEvent("click", opts));
  if (typeof btn.click === "function") btn.click();
  return "ok";
})();
