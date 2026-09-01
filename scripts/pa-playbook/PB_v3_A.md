# Protocol A (PLAN-LIST) — MANDATORY

Work in this order:

1. READ the exercise docs (`.docs/instructions.md`) and the test file.
2. WRITE `PLAN.md` in this directory NOW, BEFORE any delegate call: at least 3
   numbered tasks, one per line:
   ##T1: <first work item> | dep: none
   ##T2: <second work item> | dep: T1
   ##T3: <third work item> | dep: T1
   Each task must be a DIFFERENT work item. List dependencies after |.
3. DELEGATE one child per task — one `delegate` tool call per task, SEQUENTIAL
   (never parallel). Name each child after its task (T1, T2, T3). Give the child
   its task text verbatim. Use ONLY the delegate tool: NEVER rlm(), NEVER spawn,
   NEVER parallel children, NEVER work the tasks yourself.
4. END YOUR TURN after delegating. Do NOT work on the tasks yourself.
5. Your turn resumes when children finish: read their files + reports, INTEGRATE
   (patch their work, do not rewrite from scratch), run tests IN-KERNEL
   (`import pytest; pytest.main([...])`), fix until the tests pass.

NEVER modify the test file. Each child owns only its assigned task file.