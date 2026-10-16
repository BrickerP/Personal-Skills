# Stealth rules

This job search is stealth. The goal is Bay Area / Remote US AI infrastructure job search while minimizing discovery by the current employer and current-employer network.

## Hard redlines

- Outbound resume, cover letters, recruiter messages, referral messages, LinkedIn fields, and application answers must not mention: Cookiy AI, internal project codenames, specific client names, revenue numbers, organization/person names, internal URLs, private repository names, or non-public metrics.
- Technical work must be truthful but redacted. Prefer labels like `VC-backed Voice AI Platform Startup`, `AI research platform`, `agent-native workflow platform`, or `production AI platform` when an employer name is unnecessary.
- Never connect with, follow, message, endorse, or profile-view-bomb current or former Cookiy AI employees.
- Beijing time 09:00-19:00: LinkedIn is read-only. No writing, sending, saving, submitting, following, connecting, or profile editing.
- Before any LinkedIn profile modification, confirm Settings -> Visibility -> `Share profile updates with your network` is OFF.
- Every private message, application, profile change, Send, Submit, Save, Follow, Connect, or Open-to-Work change requires a dry-run and explicit user confirmation.
- Stop immediately on CAPTCHA, bot checks, verification prompts, account mismatch, current-company discovery risk, or legally sensitive uncertainty.

## Chrome rule

For authenticated LinkedIn/profile/application work, use `chrome-use`, which drives the user's real, already-logged-in Chrome (profile: `Lu` / `yplmicro@gmail.com`). Do not rely on a sandbox browser for LinkedIn state, logged-in identity, applications, or profile writes.

## LinkedIn privacy checklist

Check these before profile maintenance or application batches:

1. Settings -> Visibility -> Share profile updates with your network: OFF.
2. Settings -> Visibility -> Profile viewing options: Private Mode during research/profile views.
3. Settings -> Visibility -> Who can see your connections: Only you.
4. Settings -> Visibility -> Followers: restrict to connections only where available.
5. Settings -> Visibility -> Notify connections when you're in the news: OFF.
6. Settings -> Visibility -> Edit your public profile: no current-company-sensitive detail in public sections.
7. Settings -> Data privacy -> Job seeking preferences -> Signal interest to recruiters at companies where you created job alerts: OFF unless explicitly approved.
8. Settings -> Data privacy -> Job seeking preferences -> Share your profile when you click Apply: OFF or conservative; never share with current-company-linked entities.
9. Open to Work: recruiter-only if enabled; exclude current company; never public photo frame.
10. Ad/data personalization and partner visibility: keep conservative defaults; do not sync address books or expose contacts.

## Redaction checklist

Before anything leaves the machine, scan for:

- Current employer legal name.
- Product or project codenames.
- Client/customer names.
- Revenue, pricing, or deal details.
- Internal org chart or person names.
- Private repo names, branch names, internal URLs, screenshots, tokens, or environment values.
- Private customer data, report content, transcripts, or interview responses.
- Metrics that are not public, approved, or safely generalized.

If found, replace with truthful high-level wording or stop for review.

## Time-window rule

- Preferred outbound LinkedIn write windows: Tue-Thu 06:00-10:00 Pacific Time, if outside BJT 09:00-19:00.
- BJT 09:00-19:00 always overrides PT preference and makes LinkedIn read-only.
- File preparation, local resume editing, tracker updates, and JD reading are allowed during BJT work hours if no LinkedIn write action occurs.
