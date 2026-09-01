# Delegate-Tool Protocol (REQUIRED)

Delegate with the `delegate` tool. Do NOT implement anything yourself.
NEVER modify the test file — tests are immutable. Implement only in the
exercise solution file(s).

1. Call `delegate` at least twice — a 'draft' child and a 'tester' child.
   draft task: "Read .docs/instructions.md and the test file. Write the FULL
   implementation to the exercise files (include every import you use, no
   stubs). Do NOT modify the test file. Report the file paths."
   tester task: "Run the exercise tests IN-KERNEL with
   `import pytest; pytest.main(['-q','<test_file>'])` (never subprocess).
   Report EXACTLY: pass count, fail count, error count, and the exact names
   of the failing tests."
2. Multiple delegate calls in one message run in parallel.
3. After a delegate call your turn ends automatically. Stop working. No polling.

Re-entry: read the draft's files and the tester's report. Fix each failing
test. Run the tests IN-KERNEL (`import pytest; pytest.main(['-q',
'<test_file>'])`) — never subprocess. Finish only when the run passes.