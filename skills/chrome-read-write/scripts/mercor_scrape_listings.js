(function() {
  window.scrollTo(0, document.body.scrollHeight);
  const links = [...document.querySelectorAll('a[href*="listingId="]')].map(a => {
    const m = a.href.match(/listingId=(list_[A-Za-z0-9_-]+)/);
    return {
      id: m ? m[1] : null,
      text: a.textContent.replace(/\s+/g, ' ').trim().slice(0, 100),
      href: a.href
    };
  }).filter(x => x.id);
  const uniq = [];
  const seen = new Set();
  for (const l of links) {
    if (seen.has(l.id)) continue;
    seen.add(l.id);
    uniq.push(l);
  }
  return JSON.stringify({ count: uniq.length, listings: uniq }, null, 2);
})();
