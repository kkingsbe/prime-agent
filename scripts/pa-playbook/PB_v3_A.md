# PROTOCOL A (PLAN-LIST) v3.5 — MANDATORY. Do exactly this, in this order.

1. WRITE PLAN.md NOW, yourself, exactly 3 lines:
   ##T1: <work item> | dep: none
   ##T2: <work item> | dep: T1
   ##T3: <work item> | dep: T2
   Writing the plan is YOUR job. Never delegate it.

2. DELEGATE one child per task, in order: T1 first, then T2, then T3.
   One delegate call per child. Sequential, never parallel.
   NEVER delegate the same task twice — if a task failed, AMEND it with the
   failure details (never re-send the identical task text).

3. APPEND to EVERY child task, VERBATIM:
   "WRITE your deliverable to <ABS_WORKDIR>/<SLUG>.py — open('<ABS_WORKDIR>/<SLUG>.py', 'w').write(<code>) — then READ THE FILE BACK. No stubs. Imports (import X) go at the VERY TOP — never inside strings/docstrings. After writing, VERIFY it parses: import ast; ast.parse(open('<ABS_WORKDIR>/<SLUG>.py').read()) — fix before finishing."

CONTRACT (root MUST include in every child task): "The tests `from <SLUG> import ...` — implement
the function(s) the tests import, with the EXACT signatures and return types described in
.docs/instructions.md. Match their behavior precisely. NEVER build a CLI, no __main__, no
argparse, no sys.argv, no stdin reads."

4. END YOUR TURN right after delegating.

5. On re-entry: INTEGRATE the children's files (patch in place, never rewrite
   from scratch), run pytest IN-KERNEL (import pytest; pytest.main(['grep_test.py'])),
   fix until the tests PASS.

6. MEMORY: append ONE line to REFLECTIONS.md (in the workdir) per attempt:
   "what failed / why / what you changed". RE-READ it before re-delegating anything.
   If an attempt failed the same way twice, change the AMENDED task, not the file.

7. EVALUATOR: if a task needs verification, delegate ONE tester child that RUNS the
   tests IN-KERNEL (import pytest; pytest.main(['grep_test.py'])) and reports the exact
   failing test NAMES + expected-vs-actual values. A tester child NEVER writes tests.

NEVER: delegate the plan; re-delegate finished work; rlm()/spawn; parallel
children; delegate writing or editing grep_test.py (tests are fixed/authoritative);
edit grep_test.py yourself; keep code only in the kernel.