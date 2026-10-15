(() => {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const dlg = document.querySelector("[role=dialog]");
  if (!dlg) return "no_dialog";
  const btn = [...dlg.querySelectorAll("button, [role=button]")].find((b) => {
    const x = norm(b.textContent);
    return /^(Cancel|Go back|Close)$/i.test(x) && !b.disabled;
  });
  if (!btn) return "no_dismiss";
  btn.click();
  return "ok";
})();
