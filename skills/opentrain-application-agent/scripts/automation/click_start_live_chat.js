(() => {
  const btn = [...document.querySelectorAll("button")].find((b) =>
    /Start Live Chat Interview/i.test(b.textContent || "")
  );
  if (!btn) return "no_start_live_chat";
  btn.click();
  return "ok";
})();
