# Sources and provenance

The rules in `SKILL.md` are distilled from the sources below and paraphrased, not quoted at length. Items under "Agent additions" are not from the sources.

## Primary source

Dawei XU (徐大伟), personal blog (site `fresky.github.io`, Hexo source `github.com/fresky/Blog`). All 421 posts were read on 2026-10-20. About fifteen touch asking or answering; the rest are technical notes. The central post:

- 《提问的艺术》, 2015-04-26: https://fresky.github.io/2015/04/26/how-to-ask-questions/ . A condensation of the three references below plus the author's own experience.

Its structure, which `SKILL.md` follows: before asking (search, read the docs and source, try it yourself) → how to ask (goal-versus-difference title, write it down and reread as the answerer, working code and correct input/output, formatting, symptoms apart from guesses, brevity, no hasty bug claims, the right venue, politeness) → what to include (background and real goal, environment, minimal repro, diagnostics and attempts, ruled-out options with reasons) → after the answer (post a summary; redo the homework before following up).

## Original references (read 2026-10-20)

- Eric S. Raymond and Rick Moen, *How To Ask Questions The Smart Way*, rev 3.10: http://www.catb.org/esr/faqs/smart-questions.html . Contributes the "object – deviation" subject header (the blog's "goal-versus-difference" is a loose rendering), symptoms rather than guesses, no hasty bug claims, reading terse replies (RTFM or STFW usually means do the homework, not an insult), staying calm with rude replies, never assuming you are entitled to an answer. Not carried over: the hacker-community norms and the list of questions not to ask.
- *The XY Problem*: https://xyproblem.info/ . Asking about your attempted solution instead of your actual problem; include the broader picture; share why you ruled options out.
- Jon Skeet, *Writing the perfect question*, 2010-08-29: https://codeblog.jonskeet.uk/2010/08/29/writing-the-perfect-question/ . The golden rule (imagine answering with only what is on screen), a title that stands alone, context and problem statement, standalone compilable code, "I expected X, got Y", be polite.

## Other posts on the same blog

Each post relays an external article; the originals were not read.

| Post | Contributes |
|---|---|
| 《如何做一个好的软件架构师》 2022-05-25, sections 6 and 7 | A good question proves you listened; "why" as the universal question (a requested feature is often a solution); a bad versus good cross-team bug report; lower the barrier to being helped; rubber-duck effect (stating the problem often solves it); frame for the audience, conclusion first |
| 《怎么回答哪个更快的问题》 2012-12-28 (Eric Lippert) | Six counter-questions: why ask, do you need it, is it the bottleneck, does it matter, what does "faster" mean, what else is in the big picture |
| 《如何寻求别人的反馈》 2021-04-28 (Radical Candor) | A comfortable prepared question; tolerate silence; listen to understand, not to reply; reward the person who gives feedback; ask for specific feedback right after a deliverable; propose your own guesses for confirmation |
| 《如何做老板和员工的一对一的沟通》 2020-03-16 (KnowYourTeam) | Specific beats generic; "How can I help?" is too broad, offer options; 15-minute prep (review notes, pick one to three focus areas, brainstorm five to ten questions, set a listening mindset); let the other person draft the agenda; eight good questions |
| 《听听Matt Rogish说怎么面试程序员》 2013-07-12 | Write down what to probe and how, compare with the team; never ask the same thing twice; do not lead the witness |
| 《技术面试中关于软能力的问题》 2020-02-07 (Dean Hume) | A list of soft-skill interview questions |
| 《代码审查（Code Review）的一些最佳实践》 2023-12-28 | Ask questions instead of issuing verdicts; "I think ..."; observation, impact, request; give context in the change description |
| 《如何和不好相处的人一起工作》 2018-03-02 | Ask about unclear points and paraphrase; frame feedback as "here is my understanding, did I miss anything?"; ask for their expectations first |
| 《远程办公的一些建议》 2020-05-05 | Pause after asking; ask one person at a time; confirm important information |
| 《参加技术会议的一些小窍门》 2017-06-02 | Ask the speaker when not to use their product; prepare one question per person you want to meet |

## Agent additions

Doing the homework with tools (Step 0) and the confirmed, ruled out, still unknown triage; ranking questions by what unblocks the most; Mode 2 (the agent asks the user); the interview-mode stopping rule; the draft-only, redaction and no-fabrication boundaries.

## Changelog

- 2026-10-20: initial version.
- 2026-10-20: revised after a four-scenario read-through (help request, handoff agenda, interview me, mid-task ask): unified the title form, split help request from agenda, added the default-or-ask rule, per-mode output, shape-only examples, and a handoff section in the question bank.

## Maintenance

- Keep `SKILL.md` short and operational; long lists and provenance live here and in `question-bank.md`.
- To add a lesson, put one concrete rule or example into the matching section, add a dated changelog line above, and mention which source or experience it came from.
- This repo is public. Keep examples generic: no company names, internal URLs, or private individuals. Public authors cited as sources are fine.
- To test a change, give a fresh agent only `SKILL.md` plus a realistic request, and review both its answer and its critique of the skill. The four scenarios above are a good starting set.
- Validate with `python3 scripts/validate.py` (needs pyyaml) or let the repo's CI do it, then commit to `main` as the rest of this repo does.
