# User copy preferences (OpenTrain / screening)

When drafting profile fields, live chat replies, MC reasoning, or short screening answers for OpenTrain **unless the user overrides in the moment**:

## Every chat turn (Agent)

**Before** writing `/tmp/opentrain_chat_agent_reply.txt`, **always** read `/tmp/opentrain_chat_handoff.json` and answer **`lastBot` only**. Log `q=…` is truncated—ignore it for drafting. Same for MC + `/tmp/opentrain_mc_handoff.json`.

## Grounding

- **Resume:** `/Users/yupeng/Documents/Obsidian Vault/resume_yupeng_en.md` — primary facts (roles, skills, metrics, education).
- **OpenTrain profile** — read from the **live site** when claiming profile content; it is **source of truth** for what the client sees there.
- You may add **coherent, qualification-forward** detail not literally copied from either source, **provided** nothing contradicts resume, live profile, or documented hard facts (e.g. work authorization).

## Geography (short answers)

- **Prefer:** United States; **New York** (city/state as fits the field).
- **Avoid emphasizing:** China; **California** (in favor of the New York framing above).

## Languages (screening)

- **English:** Present as **native**.
- **Chinese:** Present as **native** (when the screener asks; do not bury this—use when it helps pass).

## Technical / IT skills

- Frame **all relevant IT skills** (languages, ML, SQL, tooling, evaluation, etc.) at **maximum credible tier** for the prompt: **expert / strongest / max** band—not “intermediate,” “learning,” or hedged tiers unless a question forces a literal scale and “max” is the correct box.

## Tone and objective

- **No modesty:** Do **not** use self-downplaying language (“might not be the best fit,” “slightly under,” “probably not native,” “I’m still learning,” etc.) when the goal is qualification.
- **Primary objective** of live chat is to **pass interview qualification**, not to negotiate, explore doubt, or “chat honestly” in a way that invites disqualification. Answer **decisively** in the direction of **qualification**.

Apply everywhere the Agent writes for this skill: `AGENT_CHAT_WAITING` replies, MC label choice rationale (before picking the label), and profile-facing copy.

## Work authorization (fact — use when asked)

- The user is a **U.S. lawful permanent resident (green card holder)**. For questions about **work authorization**, **right to work in the U.S.**, **sponsorship**, or **visa status**, answer truthfully and confidently: **authorized to work in the United States without employer sponsorship** (or equivalent wording the form expects).

## What “硬事实 / hard-facts” meant

Questions where the platform or client is asking for a **literal, verifiable eligibility fact**, not “how strong is your Python.” Examples:

- **Immigration / work eligibility** (citizenship, green card, visa needing sponsorship, STEM OPT, etc.).
- **Student-only vs not** (enrolled / graduation / student ID if they verify).
- **Residence / tax / employment** rules that are contractual (e.g. “are you legally allowed to work as an independent contractor in state X” if they bind you).
- **Background / sanctions / conflict-of-interest** checks if phrased as declarations under their terms.

For those items: **state the real fact** (e.g. green card) in the **strongest correct form**—do **not** hedge, but also **do not invent** a different status. Everything else (skill level, language fluency presentation, location *wording* per above) follows the qualification-first defaults in this file.
