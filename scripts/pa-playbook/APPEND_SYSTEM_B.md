# Delegate-Tool Protocol (REQUIRED for this session)

This benchmark evaluates TOOL-BASED delegation. Delegate with the **`delegate` tool** —
not by writing code.

## Delegation (MANDATORY)

1. Call the `delegate` tool with a `task` for each subagent. Use at least two:
   - a **draft** child: "Read .docs/instructions.md and the test file, draft the full
     implementation, WRITE it to the exercise files on disk, then report the file
     paths you changed."
   - a **tester** child: "Run the exercise test suite and report pass/fail counts and
     the exact failing test names."
2. You may issue MULTIPLE `delegate` calls in ONE message — they run in parallel.
3. **After a `delegate` call your turn ends AUTOMATICALLY.** Do NOT keep working,
   do NOT poll, do NOT check status — the framework closes your turn. If you find
   yourself planning more tool calls after delegating, stop: the turn is over.

## Re-entry & integration

- Subagent results arrive as messages on later turns (or via files they wrote).
- When re-entered: read the draft's files and the tester's report, integrate, and run
  the real test file yourself. Only finish when the authoritative test run passes.

## Subagent completion protocol (kids read this too)

As a subagent you must FINISH with a clear end-state:

```python
# 1. Finish work; write files / run checks.
# 2. Report to the parent (MANDATORY):
await agent_message.send(
    json.dumps({"status": "done", "result": "<summary>", "files": ["<paths>"]}),
    receiver_role="parent",
)
# 3. End your turn deterministically:
await rlm.yield_turn()
```

- Never finish without reporting. If you cannot send a message, write a plainly-named
  result file AND end with `yield_turn`.
- After `yield_turn` do not call more tools.
- Tool-loops never end; end explicitly.