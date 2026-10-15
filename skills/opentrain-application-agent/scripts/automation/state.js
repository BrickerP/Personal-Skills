(() => {
  const raw = document.body.innerText || "";
  const t = raw.replace(/\r/g, "\n");
  const lines = t
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  const idxChat = lines.findIndex((s) => s.includes("Live Chat Screening Interview"));
  const chatRegion = idxChat >= 0 ? lines.slice(idxChat) : lines;

  let lastBot = null;
  for (let i = chatRegion.length - 1; i >= 0; i -= 1) {
    if (chatRegion[i] === "OpenTrain AI Interviewer" && i + 1 < chatRegion.length) {
      const after = [];
      for (let j = i + 1; j < chatRegion.length; j += 1) {
        const line = chatRegion[j];
        if (line === "You" || line === "Send a message") break;
        if (line === "Send") break;
        if (line === "Just now" || /^Today\b|^Yesterday\b/i.test(line)) continue;
        after.push(line);
      }
      lastBot = after.join(" ").trim();
      if (lastBot) break;
    }
  }

  const hasTextarea = !!document.querySelector("textarea");
  const sendVisible = [...document.querySelectorAll("button")].some(
    (b) => (b.textContent || "").trim() === "Send" && b.getBoundingClientRect().height > 0
  );

  let phase = "unknown";
  if (!location.pathname.includes("/job-detail/")) phase = "not_job";
  else if (
    /you have already submitted|already submitted a proposal|your proposal has been submitted/i.test(t)
  )
    phase = "already_applied";
  else if (/withdrawn proposal|this job is no longer accepting/i.test(t)) phase = "closed";
  else if (
    /\bdeclined\b/i.test(t) &&
    /job-detail/.test(location.pathname)
  )
    phase = "closed";
  else if (/Pending Review|Under Review|Shortlisted/i.test(t)) phase = "pending_review";
  else if (
    /Country not eligible/i.test(t) ||
    (/not eligible/i.test(t) && /country/i.test(t))
  )
    phase = "geo_ineligible";
  else if (
    document.querySelector("[role=dialog]") &&
    /Submit a Proposal/i.test(t) &&
    [...document.querySelectorAll("[role=dialog] button")].some((b) =>
      /Submit Proposal/i.test((b.textContent || "").trim())
    )
  )
    phase = "proposal_dialog";
  else if (
    (/successfully completed your AI live chat interview/i.test(t) ||
      /everything we need for review/i.test(t)) &&
    [...document.querySelectorAll("button")].some((b) =>
      /Go to Next Step/i.test(b.textContent || "")
    )
  )
    phase = "chat_done";
  else if (
    lastBot &&
    (/everything we need for review/i.test(lastBot) ||
      /successfully completed your AI live chat interview/i.test(lastBot))
  )
    phase = "chat_done";
  else if (hasTextarea && sendVisible && idxChat >= 0) phase = "chat";
  else if (
    idxChat >= 0 &&
    lastBot &&
    !hasTextarea &&
    /choose one:|which option best matches/i.test(lastBot.toLowerCase())
  )
    phase = "chat_options";
  else if (/Resume confirmation/i.test(t) && /Continue the process/i.test(t)) phase = "resume_confirm";
  else if (
    /Live Chat Screening Interview\s+Available Now/i.test(t) &&
    /Start Live Chat Interview/i.test(t) &&
    !/You(['’])ve passed the AI Chat interview/i.test(t)
  )
    phase = "chat_start";
  else if (
    /Enter your price/i.test(t) ||
    (/Your price per hour/i.test(t) && /Rate range/i.test(t)) ||
    (/USD per hour bid/i.test(t) && /Rate range/i.test(t)) ||
    /\b(enter|set)\s+your\s+(hourly\s+)?(bid|rate|price)\b/i.test(t) ||
    /\b(hourly|your)\s+bid\b/i.test(t) ||
    (/Rate range/i.test(t) && /(?:USD|per hour|\/\s*hr)/i.test(t) && /Enter/i.test(t)) ||
    (/Submit Proposal/i.test(t) && /\$\s*[\d.]+\s*-\s*\$\s*[\d.]+/i.test(t))
  )
    phase = "proposal";
  else if (
    /Submit Proposal/i.test(t) &&
    !/Live Chat Screening Interview\s+Available Now/i.test(t)
  )
    phase = "proposal_click_submit_only";
  else if (/Submit a Proposal/i.test(t) || /\bContinue Proposal\b/i.test(t))
    phase = "job_detail";
  else if (
    [...document.querySelectorAll("button, a")].some((b) =>
      /submit\s+a\s*proposal|continue\s+proposal/i.test((b.textContent || "").trim())
    )
  )
    phase = "job_detail";
  else if (
    location.pathname.includes("/job-detail/") &&
    t.length > 350 &&
    /Save Job/i.test(t) &&
    /Estimated Total Earnings/i.test(t) &&
    idxChat < 0 &&
    !hasTextarea
  )
    phase = "job_detail";

  const hasPropCta = [...document.querySelectorAll("button, [role='button'], a")].some((b) =>
    /submit\s+a\s*proposal|continue\s+proposal/i.test((b.textContent || "").replace(/\s+/g, " ").trim())
  );
  if (phase === "job_detail" && !hasPropCta && location.pathname.includes("/job-detail/")) {
    phase = "proposal_blocked";
  }

  const rangeMatch =
    t.match(/Rate range\s*\$?\s*([\d,.]+)\s*-\s*\$?\s*([\d,.]+)/i) ||
    t.match(/Rate range[^\$]*\$(\d+\.\d{2})[^\$]*\$(\d+\.\d{2})/i) ||
    t.match(/\$(\d+\.\d{2})\s*-\s*\$(\d+\.\d{2})/);

  let rateMin = null;
  let rateMax = null;
  if (rangeMatch) {
    rateMin = parseFloat(rangeMatch[1].replace(/,/g, ""));
    rateMax = parseFloat(rangeMatch[2].replace(/,/g, ""));
  }

  const hourly = /per hour|\/hr|Hourly/i.test(t) && rateMax != null;
  const fixed = /Fixed Price/i.test(t) && !hourly;

  return JSON.stringify(
    {
      url: location.href,
      title: document.title,
      phase,
      lastBot: (lastBot || "").slice(0, 2000),
      hasTextarea,
      sendVisible,
      rateMin,
      rateMax,
      hourly,
      fixed,
      head: t.slice(0, 400),
    },
    null,
    2
  );
})();
