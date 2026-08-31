# Experiment: Tool-based delegation vs kernel-function delegation (RLM)

**Date:** 2026-08-30 · **Status:** PROPOSED · **Owner:** Hermes + Kyle

## Hypothesis

Making delegation a **first-class tool** (structured schema + framework-owned turn
termination, OpenAI-handoff style) yields reliable delegation *and* eliminates the
post-delegation yield failure on small models — versus the current kernel-function
`rlm()` + prompt protocol, which spawns ~70-100% of runs but never self-yields
(steer required every run; 2+ in-turn tool turns after spawn on Ling & LFM2.5).

Sub-claim: multiple `delegate` tool calls in one assistant message preserve parallel
delegation (the blocking concern with sync `rlm()`), because all children run
concurrently from one batch and the parent's turn terminates once after the batch.

## Design

### Arms (independent variable: delegation mechanism)

| arm | mechanism | status of data |
|---|---|---|
| **A — Control (prompt/kernel)** | `rlm()` kernel callable + playbook v6; turn end via `yield_turn`/steer | **exists** (pa-lfm2 phone-number 2/21; B2/B4 Ling; pa-full1 list-ops 22/24) |
| **B — Tool-based** | `delegate` tool added to base registry (schema-visible alongside `ipython`); harness auto-ends the turn after a delegate batch (`terminate: true` on the tool result, same mechanism as yield_turn) | **to run** |

### Run matrix (shallow per Kyle's preference; reuse recorded A-arm results)

- Exercise: **phone-number** only (the hardest; Ling floor 0/21, LFM 2/21 — biggest signal room)
- Models: **Ling-3.0-tiny** + **LFM2.5-2.6B** (both proven self-yield failures)
- B-arm: 2 runs per model = **4 B-arm runs**; A-arm: reuse pa-lfm2 (LFM 2/21) + B4-era Ling phone-number (0/21) + one fresh Ling A-arm run for same-day parity
- Deadline: 900s both arms. Same rig load config (spec-off for LFM; Ling Q4_K_M 131072/2).

### Dependent variables (existing pa_metrics.py + driver counters)

| metric | B-arm expectation |
|---|---|
| `spawns` | ≥2 every run (tool schema forces structure) |
| `root turns after delegate call` | **0 by construction** (terminate on tool result); measure anyway |
| steer count | **0** (driver steer should never fire) |
| `child_terminal` / `child_natural_stop` | ≥ control (children get more real wall time) |
| `child_replied` | watch (unchanged channel) |
| `score` | ≥ 2/21 (no regression) |
| `wall_s` per exercise | ≤ control (no in-turn polling waste) |

### Confounds to control

- pytest availability in child kernels (install into the actual per-session venv before the run — removes the tester-child repair-waste confound)
- Same RPC driver, deadline, scorer (`.venv-bench` pytest)
- Same server (spec-off LFM; Ling default), no other load on rig
- B-arm playbook: delegation described as a tool; children keep v6 completion protocol (unchanged child-side)

## Implementation sketch (B arm, ~1 small patch each)

1. **Tool definition** — add `delegate` to `createAllToolDefinitions` alongside ipython:
   schema `{task: string, name?: string, model?: string}`; execute → `runRlmChild(task, {name, model})`; result content = admission handle JSON; **`terminate: true`** when any child was spawned in the batch (reuses the `shouldTerminateToolBatch` path from yield_turn — batch ends, turn ends, agent_end fires, child notices re-enter later).
2. **Multiple delegates in one batch** — the model can emit 2+ `delegate` tool calls in a single assistant message (parallel tool execution like OpenAI fan-out); all spawn children; the turn terminates once after the whole batch.
3. Playbook B: "Delegation happens via the `delegate` tool. After a delegate call your turn ends automatically — do not keep working or poll. Child results arrive as messages on re-entry."
4. Worker-side unchanged (`runRlmChild`, child sessions, v6 completion protocol).

## Success criteria

- B-arm spawns = 2/2 runs × 2 models (100%) vs A-arm historical ~70-100%
- steer fires 0 times in B (vs 1-2 per A-arm run)
- zero root tool turns after delegate call
- score no regression; wall_s ≤ control; child_done ≥ control

## Next actions

1. Implement B-arm patch (tool def + terminate flag + playbook B)
2. Install pytest into the per-session kernel venv (find real path)
3. Run 4 B-arm runs (2×Ling, 2×LFM, phone-number)
4. Compare table vs recorded A-arm; decide: tool-based delegation becomes the default?