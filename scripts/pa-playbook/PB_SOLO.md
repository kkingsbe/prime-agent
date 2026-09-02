# SOLO PROTOCOL (delegation DISABLED) — MANDATORY. Do exactly this.

YOU implement everything yourself. NEVER call the delegate tool — all work is yours.

1. READ .docs/instructions.md and the test file FIRST.
2. WRITE PLAN.md yourself (>=3 tasks: ##T1: ... | dep: none) to structure your work.
3. IMPLEMENT <ABS_WORKDIR>/<SLUG>.py yourself, in-place, patching as you go:
   - Imports (import X) go at the VERY TOP — never inside strings/docstrings.
   - After writing, VERIFY it parses: import ast; ast.parse(open('<ABS_WORKDIR>/<SLUG>.py').read()).
   - WRITE EARLY AND OFTEN — no stubs; the file must always be importable.

CONTRACT (you MUST honor): "The tests `from <SLUG> import ...` — implement the function(s)
the tests import, with the EXACT signatures and return types described in
.docs/instructions.md. Match their behavior precisely. NEVER build a CLI, no __main__, no
argparse, no sys.argv, no stdin reads."

4. Run the tests IN-KERNEL (import pytest; pytest.main(['<SLUG>_test.py'])) — never
   subprocess — and fix until they PASS.
5. MEMORY: append ONE line to REFLECTIONS.md per failed attempt: "what failed / why / what
   you changed". Re-read before each new attempt.

6. FEEDBACK LOOP (on every re-entry when tests still fail): fix IN PLACE yourself —
   read the failing test names + expected-vs-actual in the feedback, patch the file with
   ipython edits, re-run the tests in-kernel. Keep editing until they pass or the cycle
   budget runs out.

NEVER: delegate; rlm()/spawn; edit <SLUG>_test.py; keep code only in the kernel.