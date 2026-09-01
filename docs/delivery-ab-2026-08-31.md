# Delivery-Channel A/B — PB_SHORT delegation protocol (2026-08-31)

Follow-up to the 2026-08-30 prime-agent harness eval (results-and-retro-2026-08-30.md).
Question: how should the delegation protocol reach LFM2.5-2.6B — as a workdir FILE the
model reads, or via the native system-prompt append? And do subagents get the same prompt?

## Setup
- Rig 192.168.68.58:8888, `LiquidAI/LFM2.5-2.6B-GGUF` Q4_K_M, 131072 ctx / 2 slots,
  `speculative_type: none`. Branch `eval-harness`, driver `scripts/pa_rpc.py`,
  runner `scripts/pa_ab_delivery.sh` (untracked), exercise `phone-number`,
  scorer `.venv-bench` pytest. All legs sequential.

## System-prompt facts (verified in source)
- Base prompt: `packages/coding-agent/src/core/system-prompt.ts` → `buildSystemPrompt()`
  (RLM recursion guidance + subagent guidance + skills + AGENTS.md context files).
- Native append: `resource-loader.ts` `discoverAppendSystemPromptFile()` — at startup
  appends `<cwd>/.prime/agent/APPEND_SYSTEM.md` (project; `CONFIG_DIR_NAME=".prime/agent"`
  from `config.ts:498`, `pkg.piConfig` empty) or `~/.prime/agent/APPEND_SYSTEM.md` (global);
  `--append-system-prompt` fills the same slot (`agent-session.ts:4373-4384`).
- **Children inherit loader-sourced prompt content**: `_createInlineRlmSubagentRuntime`
  (`agent-session.ts:9547-9567`) passes the SAME `_resourceLoader`, `_cwd`, settingsManager;
  `_rebuildSystemPrompt` reads `getAppendSystemPrompt()` per session → base prompt + append +
  context files are identical root↔child. Children additionally get child doctrine
  (`buildRlmPrompt` parentAgent) and depth+1 (may still delegate below max depth).

## Runs (4 + 1 probe; all phone-number, LFM2.5)
| run | delivery | delegated | children done/aborted | root tool turns | integrate turns | score | trace size |
|---|---|---|---|---|---|---|---|
| A1 (killed ~25t) | PB_SHORT.md file + prompt ref | ❌ 0 | – | 24 | – | 3/21 | small |
| B1 probe | append, LONG dual-mode text | ❌ 0 | – | 30 | – | 6/21 | small |
| **A2** | **PB_SHORT.md file + prompt ref** | **✅ 2 (draft+tester)** | **2/2, 0** | **14** | **10** | **12/21** | 5.68 GB |
| B2 | append, PB_SHORT VERBATIM | ❌ 0 | – | 14 | 0 | 0/21 | ~4 GB |

A2 = full champion cycle reproduced: delegate 2 children → both `done` (0 aborted) →
root re-enters (bubble_up YES, 10 integration turns) → 12/21 (best of the day; run
hit the 600 s cap mid-integration, not a clean exit).

## Issues identified
1. **File-path delivery is coin-flip for LFM2.5** — A1 vs A2, identical setup: A1
   hallucinated the PB_SHORT path (read `<…>/PB_SHORT.md` instead of `<…>/phone-number/PB_SHORT.md`,
   all reads FileNotFoundError) → protocol never entered context → solo grind. A2 read it
   correctly → perfect delegation. Fix: pin the ABSOLUTE path in the task prompt (runner
   computes it), or verify the read succeeded in-turn.
2. **System-prompt append ≈ invisible to LFM2.5 (B1+B2, 0/2 delegation)** — even with
   PB_SHORT text verbatim (identical to A2's file). Either the append is not reaching the
   model at runtime (discovery unverified end-to-end; marker probe needed) or a 2.6B model
   weighs system-prompt text far below file content read in-turn. Do NOT rely on the append
   for small-model protocol delivery until a marker probe proves it lands.
3. **RPC trace bloat — FIXED (driver)** — pa_rpc.py recorded every event incl. per-token
   streaming deltas (`thinking_delta`, `toolcall_delta`, `message_update`, …) → 3.9-5.7 GB
   per delegated run with a thinking model + children. Patch: `DROP_EVENT_TYPES` filter at the
   write site (unit-tested; keeps message_end/agent_end/rlm_child_update/turn_end for
   pa_metrics). NOTE: armB2 booted 27 s before the last patch and ran unfiltered — the fix is
   verified standalone but not yet in a live run.
4. **600 s deadline is too tight for delegated legs** — A2 children completed but the root
   had 10 integration turns still running when the cap fired (clean_exit NO). Champion used
   900 s. Keep 900 s for delegated arms (solo legs finish in ~3 min at 600).
5. **pa_metrics gaps for the tool arm** — `spawn_cells`/`yield_fused` count `rlm(` CODE turns
   only; delegate-tool spawns show as `rlm code turns: 0`. Add delegate-tool-turn counting so
   the metrics table describes the tool arm.
6. **Repro** — `pa_ab_delivery.sh` is untracked; parameterize deadline per arm and keep with
   the experiment assets (lesson 7: version-control experiment artifacts as they evolve).

## Score evidence
No delegation-vs-solo claim yet: 12/21 (A2, delegated, deadline-cut) sits inside the
yesterday noise band (0-12/21). Mechanism is now reproducible (delegate → 2/2 done → integrate)
when the protocol is DELIVERED. The score question still needs the horizon-mix sweep.

## Dev-task box (forth + grep) — PARTIAL (stopped by operator 2026-08-31 22:14Z)
Runner `scripts/pa_devbox.sh` (PB_SHORT_v2.1 pinned for DEL legs; SOLO = same harness, no
protocol; pristine-test scoring; del 1200s / solo 900s). Stopped during grep-del1; forth
column COMPLETE, grep column = 0 runs.

| leg | score | delegated | children done | root turns | notes |
|---|---|---|---|---|---|
| forth-del1 | **4/54** | ✅ 2 | 2/2 (nat-stop) | 17 | ONLY functional interpreter; draft had dead negative-number branch; root overwrote draft (call 7), subprocess-pytest thrash incl `result=import pytest` |
| forth-del2 | 1 error | ✅ 2 | 2/2 | 12 | collect error: `class ZeroDivisionError(Exception):` no body → IndentationError (deadline cut mid-edit) |
| forth-solo1 | 1 error | ❌ | – | 16 | collect error (broken file at deadline) |
| forth-solo2 | 1 error | ❌ | – | 25 | file ended as `def evaluate(...): pass` stub — work never landed |
| grep-del1 | – | – | – | – | aborted mid-first-turn; grep.py untouched (2 LOC stub) |

**Findings (n=1 functional leg — directional, not significant):**
1. Only the delegated leg produced a working artifact; all three 0-scores are **deadline-mid-edit
   file corruption** (syntax-broken file committed when the cap fires). Hazard for the runner:
   snapshot solution file per root turn / at child-done and score the last importable state.
2. Tester reports counts but omits exact failing-test names (v2 asks; not delivered) → root
   can't target fixes. Enforce template.
3. Root integration anti-patterns: (a) overwrites draft instead of patching it; (b) subprocess
   pytest thrash persists in the ROOT (children follow the in-kernel line; root ignores it);
   (c) pokes child session JSONL dirs instead of reading workdir files (del2).
4. Driver re-entry message is the right injection point for integration rules (arrives exactly
   at re-entry, where the root's own protocol copy is contextually buried).
5. Test-file mutation guard WORKED (pristine ✓ on all forth legs).

**Deferred (next session):** grep column; driver integration-message rules; v3 recursive/wave
delegation protocol; last-importable-state snapshot scoring; 404 fail-fast in pa_rpc.py
(model-not-loaded → abort immediately instead of burning the run).

*Runs: /tmp/pa-devbox/20260831-204559 (210 MB total; traces filtered).*

---

## Round 3 — marker probe + pinned-path retest (fixed driver) — 2026-08-31 evening
Runner `scripts/pa_lever2.sh` (probe → armA3 pinned-file → armB3 append), driver patched with
child-done re-entry (`TERMINAL_CHILD_STATUSES`, wait-while-active, integrate follow_up after
ALL children terminal).

**1. Marker probe — append delivery VERIFED WORKING (2×).** Secret token in
`APPEND_SYSTEM.md`; LFM2.5 echoed it verbatim both times (~90 KB JSONL, one turn). The B-arm
zero-delegation is therefore a salience/compliance effect, NOT delivery failure: the model
SEES the system-prompt protocol and still ignores it when the task says "implement".

**2. Pinned absolute path = deterministic delegation (armA3).** Prompt: "READ AND FOLLOW THE
PROTOCOL FILE AT <abs path>". Root delegated in the FIRST turn every time. Kills the A1
path-hallucination coin-flip. **Adopt as the standard prompt shape.**

**3. Driver child-done re-entry — live-verified.** armA3: agent_end #1 with children active →
driver waited (old driver would have exited + teardown-killed) → 2/2 children `done`, 0 aborted
→ integration follow_up sent → root re-entered for 11 integration turns. `child_terminal 2/2`,
`child_aborted 0/2`, bubble_up YES. The retro open item ("re-entry on child-done") is landed.

**4. Trace-size fix live-verified.** armA3 rpc.jsonl = 62 MB (delegated, 17 tool calls, child
events) vs 5.7 GB unfiltered yesterday; armB3 = 0.38 MB. Delta filter works in production.

**5. Integration effectiveness is now THE bottleneck.** armA3 scored 0/21 at deadline-cut
(900 s used, agent_end=1 — root never reached a clean final turn): the draft child wrote the
implementation but with ZERO imports (`re.sub` without `import re` → every test errors); the
tester child's report (0 pass / 13 fail / 8 ERROR) contained the signal but the root thrashed
(~8 turns on unittest-loader gymnastics) instead of fixing. Two root causes:
   a. **Subprocess python trap:** kernel venv (`~/.prime/agent/kernel-venv`) HAS pytest 9.1.1,
      but the model runs `subprocess.run(["python","-m","pytest",…])` → PATH python (system
      3.13, no pytest) → ModuleNotFoundError → thrash. Fix = protocol line: run tests IN-KERNEL
      with `import pytest; pytest.main(["-q", "<test>.py"])`, never subprocess. (Also revises
      the retro "children self-install pytest" note — kernel venv already has it.)
   b. **Draft quality + report exploitation:** tester reports use prose; root doesn't act on
      error counts. Candidate: structured report template (exact failing tests + error types)
      and/or a `--strict`-style fix-first directive.

**6. armB3 (append, fixed driver) still zero delegation** — 21 solo ipython turns, 9/21 best
solo of the day. Consistent with B1/B2: append protocol visible-but-ignored by LFM2.5.

### Updated scoreboard (phone-number, LFM2.5, 6 runs + probe)
| run | delivery | delegated | children done | score | notes |
|---|---|---|---|---|---|
| A1 | file, unpinned | ❌ path lost | – | 3/21 | hallucinated PB_SHORT path |
| B1 | append, long text | ❌ | – | 6/21 | probe |
| A2 | file, unpinned | ✅ | 2/2 | 12/21 | best; deadline-cut |
| B2 | append, verbatim | ❌ | – | 0/21 | |
| A3 | file, PINNED | ✅ | 2/2 (0 aborted) | 0/21 | deadline-cut; no import re |
| B3 | append, verbatim | ❌ | – | 9/21 | solo grind |

**Champion recipe (updated):** RPC + delegate tool + `terminate:true` + pinned-absolute-path
PB_SHORT reference + yield/auto-end + child-done driver re-entry + delta-filtered trace +
`import pytest; pytest.main(...)` in-kernel test runs + maxTokens unset + LFM2.5 spec-off.
Open: integration effectiveness (report format, fix-first directive); score lift still
unproven (variance floor).

*Runs: /tmp/pa-lever2/20260831-184025 (probe MKR echo 2×, armA3, armB3).*

---

*Prepared 2026-08-31. Traces: /tmp/pa-ab-delivery/20260831-181107 (armA2 5.68 GB unfiltered,
armB2 ~4 GB unfiltered legacy driver; kept-event extraction needs the filtered driver).*