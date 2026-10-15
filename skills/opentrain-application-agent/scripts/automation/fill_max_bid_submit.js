(() => {
  const t = document.body.innerText || "";

  const rectOk = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 8 && r.height > 4;
  };

  const visibleEl = (el) => {
    if (!el || el.disabled || el.closest("[hidden],[aria-hidden='true']")) return false;
    const st = window.getComputedStyle(el);
    if (st.display === "none" || st.visibility === "hidden" || Number(st.opacity) === 0)
      return false;
    return rectOk(el);
  };

  /** Works for text/number/range-ish inputs React listens to */
  const setNativeValue = (input, str) => {
    input.focus();
    const ctor =
      input instanceof HTMLInputElement ? HTMLInputElement : HTMLTextAreaElement;
    const desc = Object.getOwnPropertyDescriptor(ctor.prototype, "value");
    if (desc && desc.set) desc.set.call(input, str);
    else input.value = str;
    input.dispatchEvent(new InputEvent("input", { bubbles: true, data: String(str) }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
  };

  const priceInputHeuristic = (i) => {
    if (!i || i.type === "hidden" || i.disabled) return false;
    if (!(i instanceof HTMLInputElement)) return false;
    const ty = (i.getAttribute("type") || "").toLowerCase();
    if (ty === "range") return rectOk(i) || parseFloat(i.max || "") > parseFloat(i.min || "0");
    const ph = (i.getAttribute("placeholder") || "").toLowerCase();
    const al = (i.getAttribute("aria-label") || "").toLowerCase();
    const nm = (i.getAttribute("name") || "").toLowerCase();
    const id = (i.getAttribute("id") || "").toLowerCase();
    const im = (i.getAttribute("inputmode") || "").toLowerCase();
    return (
      ph.includes("usd") ||
      ph.includes("price") ||
      ph.includes("hour") ||
      ph.includes("label") ||
      ph.includes("bid") ||
      ph.includes("rate") ||
      al.includes("price") ||
      al.includes("bid") ||
      al.includes("rate") ||
      al.includes("hour") ||
      nm.includes("price") ||
      nm.includes("bid") ||
      nm.includes("rate") ||
      id.includes("price") ||
      id.includes("rate") ||
      ty === "number" ||
      ty === "text" ||
      im === "decimal" ||
      im === "numeric"
    );
  };

  const visibleInputs = () =>
    [...document.querySelectorAll("input")].filter(
      (i) => !i.hidden && i.type !== "hidden" && !i.disabled && visibleEl(i)
    );

  const pickPriceTargets = () => {
    const vis = visibleInputs();
    let targets = vis.filter(priceInputHeuristic);
    if (!targets.length && vis.length) targets = vis;
    return targets;
  };

  const submitBtn = () => {
    const buttons = [...document.querySelectorAll("button,[role='button']")];
    let b = buttons.find((x) =>
      /^\s*Submit Proposal\s*$/i.test((x.textContent || "").replace(/\s+/g, " ").trim())
    );
    if (!b)
      b = buttons.find((x) => visibleEl(x) && /submit\s*proposal/i.test(x.textContent || ""));
    return b || null;
  };

  /** Extract a maximum rate from common OpenTrain / gig copy patterns. */
  const findHourlyOrBidMax = (text) => {
    const patterns = [
      /Rate range\s*\$?\s*([\d,.]+)\s*-\s*\$?\s*([\d,.]+)/i,
      /Rate range[^\$]*\$(\d+\.?\d*)[^\$]*\$(\d+\.?\d*)/i,
      /\$\s*([\d,.]+)\s*-\s*\$\s*([\d,.]+)/,
      /\$(\d+\.?\d*)\s*-\s*\$(\d+\.?\d*)/,
      /(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(?:USD|\$)?\s*(?:\/|per)\s*hr/i,
      /Pay\s+range[:\s]*\$?([\d,.]+)\s*-\s*\$?([\d,.]+)/i,
      /hourly\s+range[:\s]*\$?([\d,.]+)\s*-\s*\$?([\d,.]+)/i,
      /Estimated[^\d]{0,40}\$?([\d,.]+)\s*-\s*\$?([\d,.]+)/i,
      /\$?([\d,.]+)\s+to\s+\$?([\d,.]+)\s*(?:per\s*)?hour/i,
      /between\s*\$?([\d,.]+)\s+and\s+\$?([\d,.]+)/i,
      /Min(?:imum)?\.?\s*\$?([\d,.]+)[^\d]{0,48}Max(?:imum)?\.?\s*\$?([\d,.]+)/i,
      /Compensation[^\$]{0,40}\$\s*([\d,.]+)\s*-\s*\$\s*([\d,.]+)/i,
      /Estimated Total[^\d]{0,20}\$\s*([\d,.]+)\s*-\s*\$\s*([\d,.]+)/i,
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (!m) continue;
      const a = parseFloat(m[1].replace(/,/g, ""));
      const b = parseFloat(m[2].replace(/,/g, ""));
      if (Number.isFinite(a) && Number.isFinite(b)) return Math.max(a, b);
    }
    return null;
  };

  const findSingleMoney = (text) => {
    const singles = [
      text.match(/\$(\d+\.?\d*)\s*\/\s*label/i),
      text.match(/\$(\d+\.?\d*)\s*per\s*label/i),
      text.match(/Pay\s+per\s+Label[^\$]*\$(\d+\.?\d*)/i),
      text.match(/\$(\d+\.?\d*)\/label/i),
      text.match(/\$(\d+\.?\d*)\s*\/\s*hr/i),
      text.match(/\$(\d+\.?\d*)\s*per\s*hour/i),
      text.match(/USD\s+per\s+hour[^\d]{0,16}\$(\d+\.?\d*)/i),
      text.match(/fixed[^\$]{0,24}\$\s*(\d+\.?\d*)/i),
      text.match(/\b(?:pay|bid|rate|price)[:\s]*\$\s*(\d+\.?\d*)\b/i),
    ];
    for (const m of singles) {
      if (!m) continue;
      const v = parseFloat(m[1].replace(/,/g, ""));
      if (Number.isFinite(v)) return v;
    }
    return null;
  };

  /** When copy does not parse, use sliders / numeric input max hints from the DOM. */
  const inferMaxFromInputs = () => {
    let best = null;
    const consider = (v) => {
      if (!Number.isFinite(v)) return;
      if (best == null || v > best) best = v;
    };

    const ranges = [...document.querySelectorAll('input[type="range"]')].filter(visibleEl);
    for (const r of ranges) {
      consider(parseFloat(r.max || ""));
      consider(parseFloat(r.getAttribute("aria-valuemax") || ""));
    }

    const numbers = [...document.querySelectorAll('input[type="number"]')].filter(visibleEl);
    for (const n of numbers) {
      consider(parseFloat(n.max || ""));
      consider(parseFloat(n.getAttribute("max") || ""));
    }

    return best;
  };

  /** Last resort: scrape $numbers on lines mentioning pay/rate keywords. */
  const guessMaxFromAnchoredLines = (text) => {
    const lines = text.replace(/\r/g, "\n").split("\n");
    let best = null;
    const kw = /(rate|bid|hour|\$\/|\/hr|per hour|pay|compensation|label|usd)/i;
    const money = /\$\s*([\d,.]+)/g;
    for (const line of lines) {
      if (!kw.test(line)) continue;
      let m;
      while ((m = money.exec(line)) !== null) {
        const v = parseFloat(m[1].replace(/,/g, ""));
        if (Number.isFinite(v) && (!best || v > best)) best = v;
      }
    }
    return best;
  };

  const fillAllPricesAndSubmit = (numStr) => {
    const targets = pickPriceTargets();
    if (!targets.length) {
      return JSON.stringify({ ok: false, reason: "no_input", snippet: t.slice(0, 220) });
    }
    let filled = 0;
    for (const inp of targets) {
      const ty = (inp.getAttribute("type") || "").toLowerCase();
      if (ty === "range") {
        const mx = parseFloat(inp.max || "");
        const use =
          Number.isFinite(mx) && mx > 0
            ? mx.toFixed(2)
            : Number.isFinite(parseFloat(numStr))
              ? parseFloat(numStr).toFixed(2)
              : numStr;
        setNativeValue(inp, use);
        filled++;
        continue;
      }
      setNativeValue(inp, numStr);
      filled++;
    }
    const btn = submitBtn();
    if (!btn)
      return JSON.stringify({
        ok: true,
        filled: numStr,
        inputs: targets.length,
        filledCount: filled,
        submit: false,
      });
    btn.click();
    return JSON.stringify({
      ok: true,
      filled: numStr,
      inputs: targets.length,
      filledCount: filled,
      submit: true,
    });
  };

  let maxVal = findHourlyOrBidMax(t);
  if (maxVal == null) maxVal = findSingleMoney(t);
  if (maxVal == null) maxVal = inferMaxFromInputs();
  if (maxVal == null) maxVal = guessMaxFromAnchoredLines(t);

  if (maxVal != null && Number.isFinite(maxVal)) {
    return fillAllPricesAndSubmit(maxVal.toFixed(2));
  }

  const targets = pickPriceTargets();
  if (targets.some((x) => (x.getAttribute("type") || "").toLowerCase() === "range")) {
    return JSON.stringify({
      ok: false,
      reason: "range_without_max_attributes",
      snippet: t.slice(0, 220),
    });
  }

  return JSON.stringify({ ok: false, reason: "no_hourly_range", snippet: t.slice(0, 220) });
})();
