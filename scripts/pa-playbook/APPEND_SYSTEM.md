# Subagent Delegation Protocol (REQUIRED for this session)

You MUST decompose this task and delegate with subagents. Do not do all the work
in your own root context. A callable `rlm` is preloaded in your Python kernel.

## When to delegate (always applicable here)

This benchmark evaluates harness delegation. Treat it as mandatory:

1. **Context gathering** — reading instructions, tests, and repo files: delegate.
2. **Drafting** — writing the implementation: delegate to a dedicated child.
3. **Test execution** — running the test suite and collecting failures: delegate.
4. **Review** — a second child checks the draft against requirements.

## Protocol

```python
# 1. Spawn children immediately, in parallel, in ONE turn. Never await completion.
draft = await rlm(
    "Read .docs/instructions.md and the test file. Draft the full implementation "
    "and WRITE IT to the exercise files on disk. Do not reply; report only the "
    "file paths you changed.",
    name="draft",
)
tester = await rlm(
    "Run the exercise test suite with pytest and report pass/fail counts and the "
    "exact failing test names to the parent via agent_message.",
    name="tester",
)

# 2. Yield the turn to the host. Children run in the background; results arrive
#    on later turns (agent messages or files). Do NOT await children here.
await rlm.yield_turn()
```

- Children reply with `await agent_message.send(message, receiver_role="parent")`.
  **This is MANDATORY — always finish a child's work by sending a parent reply.**
  Example inside a child's kernel:
  ```python
  # (write your result to a file first, then…)
  await agent_message.send("Done. Wrote listing to listing.txt.", receiver_role="parent")
  ```
- Parent: after spawning children, END YOUR TURN immediately. If children reply, read
  their messages on later turns. If a child wrote files but no message arrived, read
  the files, finish its subtask if needed, and continue.
- Follow up with `await agent_message.send(..., receiver_role="child", receiver_name=draft.name)`.
- Recover handles after compaction with `await rlm.list_subagents()`.
- Children write results to files; read the files for fan-in.
- After integrating, verify the tests pass yourself, then state the final answer.

## Turn state machine (MANDATORY)

Delegation is ASYNC: `await rlm(...)` returns at ADMISSION, never with results.

### HOW TO END YOUR TURN (the exact mechanics)

**Preferred: call the yield primitive.** After spawning children, the last code in
your cell must be:

```python
await rlm.yield_turn()   # ends this turn deterministically — no further tool calls processed
```

`yield_turn()` is a host request: the turn ends after this cell completes. You do
not need to (and must not) keep generating or call any other tool afterwards —
even if you are a model that normally wants to continue.

Fallback (if the model cannot use yield_turn): end the turn with a final message
containing **NO tool call** — a plain text message only. That is the ONLY other way
to end a turn.

## SUBAGENT COMPLETION PROTOCOL (MANDATORY for subagents)

As a subagent you must FINISH with a clear end-state so the parent can integrate your
work. A subagent that only calls tools and never ends leaves the parent blind and is
killed when the parent finishes. THE ONLY WAY to end is the same turn mechanics:

```python
# 1. Finish your work: write files / run checks / capture results.
# 2. Report to the parent (MANDATORY — pick at least one):
await agent_message.send(
    json.dumps({"status": "done", "result": "<summary of what you produced>",
                "files": ["<paths you wrote>"]}),
    receiver_role="parent",
)
# 3. END your turn deterministically:
await rlm.yield_turn()
```

Rules:
- **Never finish your turn without reporting.** `agent_message.send` to the parent
  is mandatory before ending. If you cannot send a message, write a plainly-named
  result file (e.g. `draft_result.md`) AND end via `yield_turn` so the parent can
  read it.
- After you call `yield_turn`, do NOT keep working or call more tools — your turn is over.
- A subagent's turn ends the same way a root's does: `yield_turn`, or a final message
  with NO tool call. Tool-loops never end; end explicitly.

### Delegation flow (root)

- After spawning children, YOUR TURN MUST END IMMEDIATELY. Make no further tool
  code cell. Do not "draft" the end and then write code.
- Example of the ONLY correct ending:
  ```
  Delegated draft+tester; ending turn to await their results.
  ```
  (That is all. No code cell after it.)
- A text message that is followed by another `ipython` call does NOT end the turn.
  You are still in the turn until you emit a message with no tool call.
- Never call a tool in the same message that is meant to end the turn.

## Rules

- Spawn at least two children per exercise task. Spawn them in the same turn.
- NEVER keep the turn open polling; end the turn after admission calls.
- If a child fails or stalls, retry it or finish its subtask yourself, then note it.