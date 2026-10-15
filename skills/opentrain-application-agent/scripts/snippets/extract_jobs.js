(() => {
  const links = [...document.querySelectorAll("a[href*='/job-detail/']")];
  const cards = [];
  const seen = new Set();
  for (const link of links) {
    const href = link.href;
    if (seen.has(href)) continue;
    seen.add(href);
    const title = link.innerText.replace(/\s+/g, " ").trim();
    let node = link.closest("article, li, [class*='card'], div") || link.parentElement;
    for (let i = 0; i < 4 && node && (node.innerText || "").length < 250; i += 1) {
      node = node.parentElement;
    }
    const text = (node?.innerText || link.parentElement?.innerText || "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 1200);
    cards.push({ title, href, text });
  }
  return JSON.stringify({ url: location.href, count: cards.length, cards: cards.slice(0, 30) }, null, 2);
})();
