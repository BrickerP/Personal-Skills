(() => {
  return [
    `URL: ${location.href}`,
    `TITLE: ${document.title}`,
    `BODY: ${document.body.innerText.replace(/\s+/g, " ").slice(0, 2000)}`,
  ].join("\n");
})();
