(() => {
  const raw = document.body.innerText || "";
  const t = raw.replace(/\r/g, "\n");

  /** Try filter tabs or summary chips: "Pending (3)", "Rejected: 12", etc. */
  function pickTabCounts() {
    const out = { pending: null, rejects: null, applications: null };
    const pairs = [
      [/pending[^\d]{0,24}(\d+)/gi, "pending"],
      [/rejected[^\d]{0,24}(\d+)/gi, "rejects"],
      [/reject[^\d]{0,24}(\d+)/gi, "rejects"],
      [/declined[^\d]{0,24}(\d+)/gi, "rejects"],
      [/(\d+)[^\d]{0,8}pending/gi, "pending"],
      [/application[^\d]{0,24}(\d+)/gi, "applications"],
      [/submitted[^\d]{0,24}(\d+)/gi, "applications"],
      [/active[^\d]{0,24}(\d+)/gi, "applications"],
    ];
    for (const [re, key] of pairs) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(t)) !== null) {
        const n = parseInt(m[1], 10);
        if (!Number.isFinite(n)) continue;
        if (out[key] == null || n > out[key]) out[key] = n;
      }
    }
    return out;
  }

  /** Classify each distinct job link by nearby status text. */
  function countByCards() {
    const pending = new Set();
    const rejects = new Set();
    const applications = new Set();

    const rejectRe =
      /declined|rejected|withdrawn|not selected|unsuccessful|proposal\s*declined|application\s*declined/i;
    const pendingRe =
      /pending review|\bpending\b|in review|under review|reviewing|awaiting|submitted(?:\s+for)?\s+review/i;
    const appRe =
      /\bactive\b|\bapproved\b|\baccepted\b|shortlisted|\binvite|hired|working|ongoing/i;

    const links = [...document.querySelectorAll("a[href*='/job-detail/']")];
    for (const a of links) {
      const href = String(a.href || "").split("?")[0];
      if (!href || href.length < 30) continue;
      let node = a.closest("tr, article, li, [data-testid], [class*='card']") || a;
      let blob = "";
      for (let i = 0; i < 8 && node; i += 1) {
        blob += `${node.innerText || ""}\n`;
        node = node.parentElement;
      }
      const sample = blob.slice(0, 2500);
      if (rejectRe.test(sample)) {
        rejects.add(href);
        continue;
      }
      if (pendingRe.test(sample)) {
        pending.add(href);
        continue;
      }
      if (appRe.test(sample)) {
        applications.add(href);
        continue;
      }
    }
    return {
      pending: pending.size,
      rejects: rejects.size,
      applications: applications.size,
      distinct: pending.size + rejects.size + applications.size,
    };
  }

  function parseAllProposals(text) {
    const patterns = [
      /All Proposals\s*:?\s*(\d+)/i,
      /\bAll\s+Proposals\b[^\d]{0,6}(\d+)/i,
      /\bProposals\s*\((\d+)\)/i,
      /(\d+)\s+total\s+proposals/i,
      /\bTotal\s+Proposals\s*:?\s*(\d+)/i,
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (m) {
        const n = parseInt(m[1], 10);
        if (Number.isFinite(n)) return n;
      }
    }
    /** Heuristic: look for tablist / chip with exact label */
    const candidates = [...document.querySelectorAll("[role='tab'], button, a, span, div")];
    for (const el of candidates) {
      const s = (el.textContent || "").replace(/\s+/g, " ").trim();
      if (/^All Proposals\s*\(?(\d+)\)?$/i.test(s)) {
        const m = s.match(/(\d+)/);
        return m ? parseInt(m[1], 10) : null;
      }
    }
    return null;
  }

  const tabs = pickTabCounts();
  const cards = countByCards();

  let pending = tabs.pending != null ? tabs.pending : cards.pending;
  let rejects = tabs.rejects != null ? tabs.rejects : cards.rejects;
  let applications =
    tabs.applications != null ? tabs.applications : cards.applications;

  if (tabs.pending == null && tabs.rejects == null && tabs.applications == null) {
    pending = cards.pending;
    rejects = cards.rejects;
    applications = cards.applications;
  }

  const allProposals = parseAllProposals(t);

  return JSON.stringify(
    {
      url: location.href,
      pending,
      rejects,
      applications,
      allProposals,
      hint: { tabs, cardsFromLinks: cards, sample: t.slice(0, 280) },
    },
    null,
    2
  );
})();
