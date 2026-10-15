(() => {
  /** Best-effort: open filter UI on /find-job and tick English + STEM-ish tags. */
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const want = [
    /^english$/i,
    /^ai$/i,
    /programming/i,
    /evaluation/i,
    /computer code/i,
    /data science/i,
    /machine learning/i,
  ];
  const clicked = [];
  const nodes = [...document.querySelectorAll("button, [role='button'], label, span, div")];
  for (const el of nodes) {
    const t = norm(el.textContent);
    if (!t || t.length > 40) continue;
    if (!want.some((re) => re.test(t))) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    try {
      el.click();
      clicked.push(t);
    } catch (_) {}
  }
  return JSON.stringify(
    { url: location.href, clicked: [...new Set(clicked)].slice(0, 20) },
    null,
    2
  );
})();
