# PROTOCOL A (PLAN-LIST) — MANDATORY. Do exactly this, in this order.

1. WRITE PLAN.md NOW, yourself, exactly 3 lines:
   ##T1: <work item> | dep: none
   ##T2: <work item> | dep: T1
   ##T3: <work item> | dep: T2
   Writing the plan is YOUR job. Never delegate it.

2. DELEGATE one child per task, in order: T1 first, then T2, then T3.
   One delegate call per child. Sequential, never parallel.

3. APPEND to EVERY child task, VERBATIM:
   "WRITE your deliverable to <ABS_WORKDIR>/grep.py — open('<ABS_WORKDIR>/grep.py', 'w').write(<code>) — then READ THE FILE BACK. No stubs. Imports (import X) go at the VERY TOP — never inside strings/docstrings. After writing, VERIFY it parses: import ast; ast.parse(open('<ABS_WORKDIR>/grep.py').read()) — fix before finishing."

4. END YOUR TURN right after delegating.

5. On re-entry: INTEGRATE the children's files (patch in place, never rewrite
   from scratch), run pytest IN-KERNEL (import pytest; pytest.main(['grep_test.py'])),
   fix until the tests PASS.

NEVER: delegate the plan; re-delegate finished work; rlm()/spawn; parallel
children; edit grep_test.py; keep code only in the kernel.