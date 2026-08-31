# Delegate-Tool Example Protocol (REQUIRED)

Follow this worked example EXACTLY — same shape, your content.

EXAMPLE (verbatim pattern to copy):
```
delegate {
  "task": "Read .docs/instructions.md and the test file. Write the full
           implementation to the exercise files on disk. Report the file
           paths you changed.",
  "name": "draft"
}
delegate {
  "task": "Run the exercise test suite with pytest. Report pass/fail counts
           and the failing test names.",
  "name": "tester"
}
```

Rules:
- Emit BOTH delegate calls in ONE message. They run in parallel.
- After the delegate call your turn ends automatically — do not work, do not poll.
- On re-entry: read the subagents' results (files/reports), integrate, run the
  real test file yourself, and finish when it passes.

Your task now: produce the same shape with tasks for this exercise.