# Prime-Agent Harness Eval — Results & Retrospective (2026-08-30)

Companion to `docs/experiment-delegation-tool-vs-kernel.md` (design) and `EVAL-PLAN.md`.
Status: COMMITTED 2026-08-31. All runs: rig `192.168.68.58:8888`, polyglot-benchmark
exercises, scored with `.venv-bench` pytest (pass_rate = passed/total).

## 1. Baseline & context

- **Models:** Ling-3.0-tiny (Q4_K_M, 65k ctx/slot @131072/2), LFM2.5-2.6B (Q4_K_M,
  spec-off), Tiel-35B-A3B-MTP (UD-IQ3_XXS), Qwen3.8-4B-Distilled, Qwen3.8-27B
  (UD-IQ2_XXS, deemed too slow at ~50-110s/turn for this loop).
- **Rig quirks found:** b10687 speculative-decode bug (`speculative batch index N is
  not inside the current sub-batch`) kills long requests — must load with
  `speculative_type: none`; phantom-quant load can wedge the daemon (fix = Studio
  restart); UD-IQ1_M/Q4_K_M load attempts fail silently for quants not on disk.

## 2. Run ledger (all LFM2.5 phone-number unless noted)

| run | mode/arm | delegated? | score | child_terminal | child_aborted | root_turns | notes |
|---|---|---|---|---|---|---|---|
| pa-rpc1 (Ling, list-ops) | RPC probe | ✅ 2 | 24F | 2/2 | 0/2 | 62 | driver loop bug |
| pa-rpc2 (Ling, list-ops) | RPC probe | ✅ 2 | 22/24 | 1/2 | – | 19 | root never yielded |
| pa-rpc3 (Ling, list-ops) | RPC probe | ✅ 2 | 21/24 | 1/2 | – | 17 | maxTokens cut final |
| pa-full1 (Ling, list-ops) | RPC full | ✅ 2 | 22/24 | 0/2 | 2/2 | 15 | teardown kill, 6/16 poll turns |
| pa-lfm (killed) | prompt/kernel | ✅ 2 | – | 1/2 | – | 18 | spec bug aborts |
| pa-lfm2 | prompt/kernel | ✅ 2 | 2/21 | 0/2 | 2/2 | 23 | victory-claim lie (2/21) |
| pa-qph (Qwen3.8-4B) | prompt/kernel | ❌ 0 | 0/21 | – | – | 0 | no tool calling at all |
| tool r1 | delegate tool, open | ✅ 2 | 4/21 | 2/2 | 0/2 | 9 | first children to `done` |
| tool r2 | delegate tool, open | ✅ 2 | 6/21 | 1/2 | 0/2 | 14 | |
| criteria r1 | delegate tool, criteria | ❌ 0 (solo) | 12/21 | – | – | 15 | highest LFM phone score |
| criteria r2 | delegate tool, criteria | ❌ 0 (solo) | 0/21 | – | – | 18 | |
| control r1 | delegate tool, open (restored) | ✅ 2 | 9/21 | – | – | – | clean agent_end #2, ~4min |
| pa-3arm SHORT/1 | 3-arm (killed ~1min) | – | – | – | – | – | run aborted by operator |

## 3. Findings

### 3.1 Deterministic turn-end (`yield_turn`) — SOLVED, core contribution
- Hypothesis (Kyle): does a smarter model self-yield after delegation? Yield-eval
  results: Ling ❌, LFM2.5 ❌, **Tiel-35B ✅** (spawn→text yield, 134s). Teaching is
  enough for strong models; small models have a continuation-bias floor.
- **Fix: `rlm.yield_turn()`** — kernel host request; ipython tool result reports
  `terminate: true` so the loop ends the turn without another LLM call. Ling yield
  eval: **FAIL→PASS in 19.9s**; validated in JSON AND RPC modes (RPC: 64.2s PASS).
- Secondary: unset output budget — `model-registry.ts` forced `?? 16384`; patched to
  send no `max_tokens` when omitted (server owns the cap). Verified via rig
  `stop_reason` — no more `length` cuts mid-answer.

### 3.2 Children never finish — ROOT CAUSE FOUND (teardown kill)
- Every pre-tool run: children 0/2 `done`, **2/2 aborted at parent teardown**
  (`_cancelActiveRlmChildRuns("Parent session disposed")`, agent-session.ts:4116).
  Children worked 2-3× the root's turns (48-50) then were murdered.
- Children never produced `stopReason: stop` → `promptAndWait` never resolved →
  status never `done` → terminal notice never delivered.
- **Fix (playbook v6 + delegate tool): child completion ritual** — finish work →
  `agent_message.send` OR plain-text report → `yield_turn`. Tool-arm r1: children
  2/2 `done`, 0 aborted, 0 errors — first time in the whole series.

### 3.3 Child→parent reply channel is dead on small models (0/2 everywhere)
- Small models never call `agent_message.send` even when the playbook mandates it.
  BUT the host's **`rlm_child_terminal_notice`** (`completed_without_reply` +
  `lastAssistantTextPreview`) delivers the child's final report into the parent
  session — the real working channel.
- Gap: the notice arrives when the child *completes* (late) and does not re-enter the
  parent; our driver's single follow_up precedes it → report unseen. Next fix:
  driver re-enters on `rlm_child_update done`, and count notices as
  `child_report_delivered` in metrics.

### 3.4 Delegation-vs-solo score evidence is NOISE at this n
- LFM phone-number scores: 2 (delegated), 4 (del), 6 (del), 12 (solo), 0 (solo),
  9 (del). Delegation shows no score lift on this exercise at n=6; variance (Ling
  grade-school 20/20↔17/20) swamps mechanism effects. More exercises + more runs
  needed before any score claim.

### 3.5 Verbosity-tax hypothesis (prompt design)
- Delegation fired **3/3 with the short open playbook**, **0/2 with the long
  criteria playbook** (identical tool stack). Leading explanation: longer
  instruction prose makes small models revert to solo behavior. Untested as A/B
  (criteria arm never actually exercised the criteria — it bailed to solo).
  **Deferred 3-arm design** (`PB_SHORT` / `PB_ROLE` / `PB_EXAMPLE`) exists but was
  killed before data.

### 3.6 Task-scoping lesson
- Analysis of delegated task text: open-ended tasks ("draft the full implementation")
  ⇄ children grind to `length` truncation (27-30 turns each); terminal tasks ("run
  once, report") ⇄ clean natural stop. Acceptance criteria should be baked into
  delegated task templates (deferred — collides with the verbosity-tax finding).

## 4. Open items / next

1. Rerun the 3-arm prompt experiment (SHORT/ROLE/EXAMPLE ×2) — no watchdog.
2. Driver re-entry on child-`done` + `child_report_delivered` metric.
3. A/B: acceptance criteria in a SHORT wrapper (criteria without verbosity).
4. Multi-exercise sweep (B5) for actual delegation-vs-solo score evidence.
5. Kernel-venv pytest: children self-install pytest per-session (waste) — pre-seed.

## 5. Repo artifacts (branch `eval-harness`, commit 6edf4de)

- Code: `rlm.yield_turn()` (kernel+runtime), `delegate` tool, session defaults,
  model-registry maxTokens fix.
- Scripts: `pa_rpc.py` (driver), `pa_metrics.py`, `pa_yield_eval.py` + `_rpc.py`,
  `pa_tool_experiment.sh`, `pa_ab_criteria.sh`, `pa_3arm.sh`, playbooks
  `APPEND_SYSTEM*.md`, `PB_SHORT/ROLE/EXAMPLE.md`.
- Docs: `EVAL-PLAN.md`, `docs/experiment-delegation-tool-vs-kernel.md`, this file.
- Raw traces: `/tmp/pa-*` (ephemeral — copy into repo if needed for re-analysis).