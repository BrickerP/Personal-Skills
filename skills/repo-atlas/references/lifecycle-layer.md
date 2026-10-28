# Lifecycle layer (optional, experimental)

Status: not yet run on a real repository. The output is a model of the code, not a proof about it. A passing health check means only that the model is self-consistent.

## When to build a machine

Only for an entity whose lifecycle is evidenced in code: a status field or enum, `switch status`, transition functions, the state pattern, XState. Skip pure libraries, stateless services and most CLIs, and record "no lifecycle entities" in `coverage`. At most 3 machines per repo and 12 states per machine. A machine hangs off the node that owns the state; it does not replace the map.

## What to record

- States (including initial and terminal) and where each is stored: DB column, cache key, memory, orchestrator object, or derived. If no single field holds the state, say so and list what it is derived from.
- Events and who fires them: API call, timer, background loop, external callback.
- Transitions: from state, event, guard, to state, actions, and the `path:line` where the state is set. Split multi-step actions: the intermediate states are states, so say who recovers if the process dies between the steps.
- Invariants that hold in every reachable state; timeouts, retries and reclaim paths.
- A state x event table. Annotate every empty cell as `impossible` (needs evidence such as a precondition check or a type constraint), `dropped` (the code explicitly discards the event) or `unknown` (not found). Never fill a cell with an invented reason; the number of `unknown` cells is the honest to-do list.

States and transitions without solid evidence are tagged `inferred`. Do not invent them to look complete.

Typical findings: a leader-election loop that never re-enters the candidate state after losing its lease; a two-step delete that leaves an orphan if the process dies between the steps; a state with no timeout transition.

## atlas.json addition

```json
"machines": [{
  "id": "", "entity": "", "owner_nodes": [""], "stored_in": "",
  "states": [{"id": "", "name": "", "kind": "initial|normal|terminal", "ref": "path:line", "tag": ""}],
  "events": [{"id": "", "name": "", "source": "api|timer|loop|callback|internal", "ref": ""}],
  "transitions": [{"from": "", "event": "", "guard": "", "to": "", "actions": [""], "ref": "path:line", "tag": ""}],
  "ignored": [{"state": "", "event": "", "why": "impossible|dropped|unknown", "ref": ""}],
  "invariants": [{"text": "", "ref": "", "tag": ""}]
}]
```

In flows, a step that touches a machine gets `"state": {"machine": "", "before": "", "after": ""}`.

## Model health check (computed by a script)

Report these numbers and lists verbatim in the final reply:

1. States unreachable from the initial state.
2. Non-terminal states with no outgoing transition.
3. States from which no terminal state is reachable.
4. (state, event) pairs with more than one target; list the guards so a human can judge whether they are mutually exclusive.
5. Empty cells in the state x event table that have neither a transition nor an `ignored` annotation.

Also check that every state and transition `path:line` exists at REF and that the state name appears near that line, and that each flow step's before and after states agree with the transition table.

## Page

Add a "lifecycle" tab with the state diagram (SVG). Clicking a transition shows its event, guard, actions and evidence; selecting a flow step highlights its transition. Next to it, a "model health check" panel with the five results above. Call it a health check, never "verification".

A single state machine does not cover concurrency (two actors racing for one state), partitions or retries: list those as questions or risks. Model checkers such as TLA+ are a different level of rigor and out of scope here.
