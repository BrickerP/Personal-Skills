(() => {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const dlg = document.querySelector("[role=dialog]");
  const scope = dlg || document;
  const buttons = [...scope.querySelectorAll("button, [role=button]")].map((b) => ({
    text: norm(b.textContent).slice(0, 60),
    disabled: !!b.disabled,
  }));
  return JSON.stringify(
    { phase_hint: norm(document.body.innerText).slice(0, 120), hasDialog: !!dlg, buttons },
    null,
    2
  );
})();
