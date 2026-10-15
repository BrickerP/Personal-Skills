(() => {
  const btn = [...document.querySelectorAll("button, a")].find((b) =>
    (b.textContent || "").includes("Go to Next Step")
  );
  if (!btn) return "no_next";
  btn.click();
  return "ok";
})();
