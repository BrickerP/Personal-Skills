(() => {
  const btn = [...document.querySelectorAll("button")].find((b) =>
    /Continue the process/i.test(b.textContent || "")
  );
  if (!btn) return "no_continue_process";
  btn.click();
  return "ok";
})();
