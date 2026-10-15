(() => {
  const visible = (el) => {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  };
  const text = (el) => (el?.innerText || el?.textContent || el?.value || el?.ariaLabel || "").replace(/\s+/g, " ").trim();
  const list = (selector, limit, mapper) =>
    Array.from(document.querySelectorAll(selector)).filter(visible).slice(0, limit).map(mapper);

  return JSON.stringify({
    url: location.href,
    title: document.title,
    headings: list("h1,h2,h3", 30, (el) => ({ tag: el.tagName.toLowerCase(), text: text(el) })),
    textExcerpt: text(document.body).slice(0, 5000),
    inputs: list("input,textarea,select,[contenteditable='true']", 80, (el) => ({
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute("type") || "",
      name: el.getAttribute("name") || "",
      id: el.id || "",
      placeholder: el.getAttribute("placeholder") || "",
      ariaLabel: el.getAttribute("aria-label") || "",
      value: (el.value || el.textContent || "").slice(0, 300)
    })),
    buttons: list("button,[role='button'],input[type='button'],input[type='submit'],a", 120, (el) => ({
      tag: el.tagName.toLowerCase(),
      text: text(el).slice(0, 300),
      href: el.href || ""
    })),
    focused: document.activeElement ? {
      tag: document.activeElement.tagName.toLowerCase(),
      id: document.activeElement.id || "",
      name: document.activeElement.getAttribute("name") || "",
      text: text(document.activeElement).slice(0, 300)
    } : null
  });
})();
