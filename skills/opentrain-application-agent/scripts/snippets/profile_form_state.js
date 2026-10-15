(() => {
  const fields = [...document.querySelectorAll("input, textarea, select, [contenteditable=true]")].map((el, i) => {
    const rect = el.getBoundingClientRect();
    const label =
      el.labels?.[0]?.innerText ||
      el.getAttribute("aria-label") ||
      el.getAttribute("placeholder") ||
      el.getAttribute("name") ||
      el.getAttribute("id") ||
      "";
    return {
      i,
      tag: el.tagName,
      type: el.getAttribute("type") || "",
      label: String(label).replace(/\s+/g, " ").trim(),
      value: String(el.value || el.innerText || "").slice(0, 1000),
      checked: "checked" in el ? el.checked : undefined,
      visible: rect.width > 0 && rect.height > 0,
      rect: [rect.x, rect.y, rect.width, rect.height].map(Math.round).join(","),
    };
  });
  const buttons = [...document.querySelectorAll("button,a")].map((el, i) => {
    const rect = el.getBoundingClientRect();
    return {
      i,
      tag: el.tagName,
      text: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 160),
      href: el.href || "",
      visible: rect.width > 0 && rect.height > 0,
      rect: [rect.x, rect.y, rect.width, rect.height].map(Math.round).join(","),
    };
  }).filter((x) => x.visible || x.text || x.href).slice(0, 220);
  return JSON.stringify({ title: document.title, url: location.href, fields, buttons }, null, 2);
})();
