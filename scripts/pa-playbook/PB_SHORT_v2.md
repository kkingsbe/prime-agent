# Delegate-Tool Protocol (REQUIRED)

Delegate with the `delegate` tool. Do NOT implement anything yourself.
NEVER modify the test file — tests are immutable. Implement only in the
exercise solution file(s).

1. Call `delegate` EXACTLY twice — a 'draft' child and a 'tester' child.
   Copy the draft task VERBATIM:
   "Read .docs/instructions.md FIRST. The spec REQUIRES returning ALL
   matching lines (not just the first). Write the FULL implementation to
   the exercise files (include every import; no stubs). Do NOT modify the
   test file. Report the file paths."
   tester task: "Run the exercise tests IN-KERNEL with
   `import pytest; pytest.main(['-q','<test_file>'])` (never subprocess).
   Report EXACTLY: pass count, fail count, error count, and the exact names
   of the failing tests."
2. Multiple delegate calls in one message run in parallel.
3. After a delegate call your turn ends automatically. Stop working. No polling.

APPEND to EVERY child task, VERBATIM:
"WRITE your deliverable to <ABS_WORKDIR>/grep.py — open('<ABS_WORKDIR>/grep.py', 'w').write(<code>) — then READ THE FILE BACK. No stubs. Imports (import X) go at the VERY TOP — never inside strings/docstrings. After writing, VERIFY it parses: import ast; ast.parse(open('<ABS_WORKDIR>/grep.py').read()) — fix before finishing."

CONTRACT (include with EVERY child task): "The tests import `grep(pattern, flags,
files) -> list[str]` from grep.py — implement THAT function exactly. Keep its signature.
Do NOT build a CLI, no __main__, no argparse."

Re-entry: read the draft's files and the tester's report. Fix each failing
test. Run the tests IN-KERNEL (`import pytest; pytest.main(['-q',
'<test_file>'])`) — never subprocess. Finish ONLY when all tests pass.
A tester child NEVER writes tests.