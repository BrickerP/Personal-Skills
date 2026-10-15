(() => {
  const nodes = [...document.querySelectorAll("button, [role='button']")];
  const labels = [];
  const seen = new Set();
  for (const x of nodes) {
    const r = x.getBoundingClientRect();
    if (r.height < 3 || r.width < 3) continue;
    const s = (x.textContent || "").replace(/\s+/g, " ").trim();
    if (!s || s.length > 120) continue;
    if (seen.has(s)) continue;
    seen.add(s);
    labels.push(s);
  }
  return JSON.stringify({ labels: labels.slice(0, 48) });
})();
