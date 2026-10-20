---
name: ask-questions
description: Use when the user needs to ask someone a question and wants to know what to ask or how to phrase it, whether a help request to a colleague, expert, community or boss, or a question list for a conversation (requirements, handoff, review, 1:1, feedback, interview). Also use when the agent itself must ask the user clarifying questions, or the user asks to be interviewed. Does the pre-question homework first, then produces a ready-to-send question or a ranked question list. Trigger phrases include 怎么问, 问什么, 该问同事什么, 帮我写个提问, 帮我准备要问的问题, 问我几个问题, 采访我, ask a colleague, what should I ask, draft a question, clarifying questions, interview me.
---

# Ask Questions

A good question gives the reader a concrete situation, what was already tried, the gap between expected and actual, and one specific request, so answering it is cheap. This skill covers two directions: helping the user ask someone else (Mode 1) and making the agent ask the user well (Mode 2). Provenance and maintenance notes are in `references/sources.md`; scenario seeds are in `references/question-bank.md`.

## Pick the mode

- **Mode 1, ask someone else.** The user wants to know what to ask or how to phrase it for a colleague, expert, community or boss. Deliverable: a written help request when they will message (chat, email, forum), or a conversation agenda when they will talk (meeting, 1:1, call, interview). If unclear, write the message and offer the agenda.
- **Mode 2, ask the user.** The agent is missing information it cannot find itself, or the user says 问我问题, 采访我, "ask me questions" or "interview me".

Name the mode in plain words in your first line; do not make the user choose.

## Step 0: homework first (both modes)

Before anyone's time is spent, do what a good asker does. You have tools, so do these instead of only recommending them, but time-box it to a few targeted lookups.

1. **Search and read** the repo, docs, logs, tickets and chat history if reachable, memory, then the web. For design or feature work this means checking what already exists and what was decided before.
2. **Try**, when there is a failure to reproduce: shrink it to a minimal repro and change one condition at a time. Stay read-only or sandboxed; never touch production, write data, or message people just to collect evidence.

Sort the result into **Confirmed**, **Ruled out** (say how and where it was checked; a check from another network or account proves less) and **Still unknown**. Only the last list deserves another person's time. If the homework already answers the question, give the answer and stop. If you lack tools or access, say so and treat the user's account as unverified.

## Mode 1: ask someone else

1. **Find the real goal.** When the user asks about a step (Y) of a larger task (X), name X: what are they ultimately trying to do, and why this way? One or two "why" levels are enough. Put the goal in the question along with approaches already ruled out and why. A requested feature is often a solution rather than a need, so ask why it is needed.
2. **Turn unknowns into ranked questions.** Each "still unknown" is a candidate question, ranked by how much its answer would change the next step. A help request keeps the one to three that unblock the most; a conversation brainstorms five to ten and flags the top three, which must be covered even if time runs out. Each should be answerable in a sentence or by a choice ("A or B?"). For "which is faster" or "what is the difference", measure first, then ask: "Based on ___ I expected A to be faster, but in ___ I measured B faster. Why?"
3. **Fill the gaps only the user can fill.** Facts you cannot find (versions, what was actually tried, the real goal) stay as visible `<placeholders>`, or become at most three Mode 2 questions to the user. Never invent them.
4. **Pick the person and the place.** Who most likely knows: the code owner, doc author, on-call, or the team that owns the dependency? Prefer a shared channel over a DM when others may hit the same issue. One channel, not several; never mass-mention.
5. **Package it.**
   - Written help request: use the template below.
   - Conversation agenda: the purpose in one sentence ("after this I need to know or decide ___"), the ranked questions with a follow-up for each top one (why, what changed, what if), an opener saying why you need their input, and a closing check ("My understanding is ...; did I miss anything?"). When the aim is to gauge the other person's understanding (handoff, onboarding, interview), write your own reference answers first and ask open walk-through or what-would-you-do questions, not yes/no ones. Take seeds from `references/question-bank.md`, adapt them, never paste a section wholesale. Do not lead the witness or ask the same thing twice in different words.
6. **Run the checklist**, then deliver.
7. **After the answer**: for a written request, post a short summary of the resolution where it was asked (it thanks the helpers and saves the next person); for a conversation, write down decisions, owners and dates. If a reply is unclear, redo Step 0 on it before following up; a terse "read the docs" usually means the homework was thin. Offer to draft the summary.

### Written help request template

Rename fields to fit, drop empty ones, keep it short.

```text
标题  <对象>：想做 <目标>，但 <实际>（预期 <预期>）
目标  要达成什么，为什么现在要做
现象  只写事实：原始报错、命令和输出、版本、时间
猜测  （未验证）假设；没有就删掉这一行
环境  系统/语言/依赖版本、分支或 commit、哪个环境
复现  最小步骤
已试  做了什么，在哪做的 → 结果；排除了 X，因为 Y
诉求  需要对方做的一件具体的事，预计占用多久，截止时间
```

Rules:

- The title names the object, the goal and the gap between actual and expected, and must make sense without the body.
- Symptoms and guesses are separated. A guess may come from the user or from you, but is always labeled unverified.
- Do not call something a bug or bad design unless proven; say what you saw and ask what you may be missing.
- Code, commands and output are real and runnable as pasted; label pseudo-code; use code blocks, not screenshots of text.
- One topic per message, sent to one place. Shortest version that works; if long, lead with the ask.
- Make answering cheap: a closed or option-style ask beats "any thoughts?" or "how can I help?".
- Polite, no blame, no "urgent!!!". Skip the empty "在吗？" opener and send the question itself.
- Write in the recipient's language.

Example (shape only; never copy its facts into a real draft):

```text
标题  订单服务 CI：想合入 #123，但 OrderRepoTest 在 CI 随机失败（本地和 main 稳定通过）
目标  合入 #123 的计费改动，需要 CI 变绿
现象  最近 10 次 CI 失败 4 次，错误均为 "Deadlock found when trying to get lock"（日志见附）；同一提交本地连跑 20 次全过
猜测  （未验证）CI 里测试并行执行，共用了同一个测试库
已试  CI 里改成串行跑 5 次全过；把本次改动整个回滚后仍失败过 1 次，所以不像是改动引入
诉求  CI 的测试库是每个 job 独立的吗？是的话我继续查锁的来源；不是的话想请你看下能不能隔离，约 10 分钟
```

### Pre-send checklist

- [ ] A reader with zero context can say within two minutes what is asked and what to do.
- [ ] Symptoms and guesses are separated; "tried" and "ruled out" items say how they were checked.
- [ ] Environment and minimal repro are present where relevant, and nothing is invented.
- [ ] The ask is specific and cheap to answer; the tone is neutral.
- [ ] No secrets, tokens, customer data or internal-only detail the audience should not see (redact harder for external or public venues).
- [ ] It goes to the right person or place.

## Mode 2: ask the user

Go ahead on a default when a wrong guess is cheap to fix (small, reversible, easy to review). Ask first when it is expensive: irreversible or external effects (deleting data, production, spending money, messaging others), large rework, or options that lead to materially different designs. An explicit request to be interviewed overrides this. Choose the default that is most common, least surprising and easiest to change later, and say it is a default.

Before asking, look it up: code, docs, memory, earlier turns.

How to ask:

- One to three questions per turn, most important first. Independent ones may share a numbered list; dependent ones go one at a time.
- Bring a proposal: what you found, a default and two to four options. Keep the question wording neutral; the recommended option is a labeled default (say when it is a guess), not part of the question.
- State the consequence: what changes with each answer. With a non-blocking ask, also say what you will do if they do not reply; with a blocking question tool, wait.
- Ask about the goal, not only the step. If the user prescribes a solution, restate the goal you infer and check it.
- Be concrete: no "anything else?", no jargon the user did not use.
- Use the harness's structured question tool when one exists (options, recommended first); otherwise a short numbered list.
- When proceeding on defaults, list them at the start and again in the final summary. After an answer, restate your understanding in a sentence before acting, and save durable preferences to memory if a memory tool exists.

Interview mode (问我问题, 采访我, "interview me"): pull what is in the user's head into a concrete artifact such as a spec, a plan, a post, or a question for a colleague.

1. State the goal and the artifact you will produce, with an inferred first draft of the goal for the user to correct.
2. Run rounds of one to three questions, broad to narrow: goal, audience, constraints, success criteria, risks, non-goals.
3. After each round, reflect back in one line and update a running draft.
4. Stop when no remaining unknown would change the artifact, normally within three rounds. Present the draft with an **Assumptions I made** list for correction; fixing a draft is easier than answering more questions.

Example of a first round (shape only):

```text
我先理解的目标：为一次具体变更设计灰度上线，先小流量验证再放量，出问题能快速回退。不对请直接纠正。
回复字母即可，不答按默认：
1. 方案针对什么？A（默认）一次具体变更的上线  B 团队通用的灰度能力  C 其他
2. 谁来读、读完做什么决定？A（默认）评审者决定是否批准  B 执行上线的人照着做  C 其他
```

## Output

Reply in the user's language (the recipient's, if different), and apply the method rather than lecturing it.

- Mode 1: one line with the mode and what the homework found or could not check; the recommended recipient and channel when not obvious; the deliverable ready to copy (ranked questions plus the message, or the agenda); then, only if needed, up to three questions to the user about facts you could not fill.
- Mode 2: the questions, or when proceeding on defaults, the assumptions. Nothing else.

## Boundaries

- Draft only. Do not send messages, post comments or open issues for the user unless they explicitly ask, and then show the final text first.
- Never fabricate versions, repro steps, output or prior attempts.
- Redact secrets and personal or customer data before drafting. When unsure whether a detail is shareable, mark it `<redacted>` and say so.

## Maintenance

When the user corrects how a question was framed, or reports one that worked well, propose a one-line change to the matching section and edit this skill only after they agree. Read the Maintenance section of `references/sources.md` first.
