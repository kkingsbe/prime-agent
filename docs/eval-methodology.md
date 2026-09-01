# Prime-Agent Delegation Eval — Methodology (living doc)

> v1 · drafted 2026-08-31 (session: LFM2.5 delegation lab) · owner: Hermes + Kyle
> Companion to `EVAL-PLAN.md` (harness research) and `docs/delivery-ab-2026-08-31.md`
> (round-by-round results). Update this doc when the protocol changes.

## 0. Goal (north star)

**Provably improve end-to-end performance on real tasks with small models (LFM2.5-2.6B today,
Qwen3.8 eventually) running in the prime-agent harness**, driven by **delegation that keeps
every agent's context small**, exploiting two physics facts of small models:

1. **Speed ↑ as context ↓** — decode cost grows with context; a short-context agent turns
   faster (less context = higher t/s on the same rig).
2. **Intelligence ↑ as context ↓** — small models dilute on long contexts; narrow, focused
   slices are where their accuracy is highest.

**Thesis (falsifiable):** *a fleet of short-context agents (root orchestrator + narrow-task
children) beats the same model grinding solo at long context — same harness, honest scores —
delivering a speed × score point that punches above the model's weight class.*

**Eventual structure milestone (Kyle, 2026-08-31):** fan-out **2–3 levels deep** —
the root decomposes a complex task into subtasks, children decompose further into
grandchildren (depth-2/3), each level working at small context, with results bubbling back
up. This is the scaling target the protocol (v3) and harness levers are built toward.

## 1. Research questions

| # | Question | Status |
|---|---|---|
| RQ1 | Can a small local model (LFM2.5-2.6B on a 12GB RTX4070 rig) delegate **reliably** inside prime-agent's RLM harness? | ✅ resolved — delegate tool + `terminate:true` + child-done driver re-entry (children done 2/2, 0 aborted, across forth legs) |
| RQ2 | How must the delegation **protocol** reach the model? | ✅ resolved — pinned workdir file beats system-prompt append (marker probe: append is *delivered but ignored*; file-read is *followed*) |
| RQ3 | Does delegation **beat solo** on dev-shaped tasks (honest scores, not deadline-corrupted)? | ❌ open — honest A/B pending (grep box rerun + runner integrity fixes) |
| RQ4 | Will it **delegate further** as task complexity grows — fan-out **2–3 levels deep**, decomposing a complex task into subtasks/grandchildren? | ❌ open — **milestone**; v3 protocol lever (wave/recursive delegation), `rlmMaxDepth=2` default already permits depth-2; runner + protocol work required |

## 2. Environment

- **Rig**: `192.168.68.58:8888` Unsloth Studio (llama.cpp b10687). Auth: bearer from `/opt/data/.unsloth_api_key`. OpenAI-compat `/v1`.
- **Champion load** (LFM2.5): `{"model_path":"LiquidAI/LFM2.5-2.6B-GGUF","gguf_variant":"Q4_K_M","force_cancel_active":true,"max_seq_length":131072,"n_parallel":2,"speculative_type":"none"}`.
  ⚠️ Post-load spec-state assert is REQUIRED (b10687 spec bug broke both delegated legs 2026-08-31 devbox; `speculative_type` did not hold after a force-cancel reload).
- **Host**: WSL `/opt/data`. Fork `kkingsbe/prime-agent` branch `eval-harness`; bench at `/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark`; scorer `/opt/data/repos/aider/.venv-bench/bin/python` (pytest 9.1.1).
- **Agent kernel env**: `~/.prime/agent/kernel-venv` (has pytest + rlm). Model must run tests IN-KERNEL (`import pytest; pytest.main([...])`), never via `subprocess.run(["python", ...])` → PATH python lacks pytest.

## 3. Harness mechanics (source-verified)

| Mechanism | Where | Role |
|---|---|---|
| RPC mode mandatory | JSON mode ends root session at `agent_end`; children can't re-enter | bubble-up requires RPC |
| `delegate` tool | `packages/coding-agent/src/core/tools/delegate.ts`; schema `{task,name,model}`; `terminate:true` (OpenAI-handoff) | tool-visible spawn; turn auto-ends; parallel multi-delegate per message |
| `rlm.yield_turn()` | kernel `host_request` → ipython result `terminate` | deterministic turn-end primitive (superseded by auto-end on tool arm) |
| Child system prompt | `agent-session.ts:9547-9567` — children SHARE `_resourceLoader`/`_cwd`/settings; `_rebuildSystemPrompt` (:4373) pulls loader append per session | base prompt + append + context files identical root↔child; children add doctrine + depth+1 |
| Active tools default | `sdk.ts:239`, `agent-session.ts:9169` → `["ipython","delegate"]` | delegate is offered by default |
| Driver re-entry | `scripts/pa_rpc.py` — `TERMINAL_CHILD_STATUSES={"done","cancelled","error"}`; agent_end with children active ⇒ wait; ALL terminal ⇒ integration follow_up | children no longer teardown-killed (retro open item, landed 2026-08-31) |
| Trace filter | `pa_rpc.py` `DROP_EVENT_TYPES` (thinking/toolcall/message deltas) | 5.7 GB → 0.4–100 MB per run |

## 4. Experimental design

- **Controlled variable hierarchy**: mechanism → protocol delivery → protocol content → task scope. Change one level per run (Kyle: ONE fix/run).
- **Arms**: DEL (protocol file pinned by absolute path + delegate tool) vs SOLO (same harness, no protocol file, no delegation) vs AIDER baseline (harness-lift context; not yet in this series).
- **Legs strictly sequential** (shares the rig; no concurrency). Small n: 2 runs per arm typical (variance floor demands repeats).
- **Deadlines**: solo 900 s, delegated 1200 s. Runs that don't reach a clean `agent_end` are deadline-cut and flagged (not counted as clean exits).
- **Protocol delivery channels tested**:
  - `APPEND_SYSTEM.md` (native append; long & verbatim variants) → 0/3 fired. Marker probe proved the append IS in-context but ignored (salience, not delivery).
  - File + prompt reference, unpinned path → fragile (1/2 path hallucination → protocol never read).
  - **File + absolute path pinned in prompt → adopted** (fired 4/5; 1 solo-rollout = grep-del1).
- **Protocol versions**: PB_SHORT (4 imperative rules) → PB_SHORT_v2 (+ in-kernel pytest, tester report template, draft quality bar) → v2.1 (+ NEVER modify test file). v3 wave/recursive delegation = planned lever for RQ4.

## 5. Metrics

From `scripts/pa_metrics.py` + runner digests (all per-run):

- **Mechanism**: `delegate_fired` (⚠️ NOT yet measured — script counts `rlm(` code turns only; tool-arm counting pending), `spawns`, `child_terminal` (done rate), `child_aborted`, `child_natural_stop`, `child_errors`/`child_overflows`, `child_work_ratio`, `root_tool_turns`, `bubble_up` (delivery + integration turns), `clean_exit` (needs error-taxonomy: deadline-cut / spec-error / refusal), `zero_effort`, `poll_ratio`, `victory_claim`.
- **Score**: pytest pass_rate on PRISTINE tests (runner restores the source test file before scoring — agent test-mutation guard).
- **Trace hygiene**: filtered `rpc.jsonl` per leg; keep `message_end`/`agent_end`/`rlm_child_update`/`turn_end`.
- **Gates**: metrics gate the next leg/box. No score claim without ≥2 repeats per cell above the variance floor.

## 6. Scoring integrity

1. **Pristine test restore** before every pytest (runner `cp` from exercise source).
2. **Test-file mutation guard**: protocol v2.1 + restore (confirmed working 2026-08-31; a run mutated `phone_number_test.py`, contaminated scores, caught by diff).
3. **Last-importable-state snapshot** (PENDING): snapshot the solution file per root turn / at child-done; score the last importable state. Kills the deadline-mid-edit corruption that zeroed 3/4 forth legs (`class X:` no body → IndentationError; `pass` stub).
4. **Spec-error flag** (PENDING): detect `speculative batch index N is not inside the current sub-batch` in traces and fail the load-assert instead.
5. **404 fail-fast** (PENDING): `pa_rpc.py` aborts immediately on `model downloaded but not loaded` instead of burning the run (observed twice 2026-08-31).

## 7. Known confounds & guards

| Confound | Evidence | Guard |
|---|---|---|
| Model run variance | phone-number solo 0–12/21 across days | ≥2 repeats per cell; report band not point |
| Verbosity tax | long criteria playbook 0/2 vs short 3/3 | protocols stay short + imperative |
| Path hallucination | A1 read wrong dir; FileNotFound ×3 | absolute path pinned by runner |
| b10687 spec bug | `speculative batch index 16/32` killed del finals | spec-off load + post-load assert |
| Model unloaded mid-series | 404 (Heretic takeover) | fail-fast + reload before box |
| Deadline mid-edit corruption | 3/4 forth legs syntax-broken at cap | last-importable-state scoring |
| Test-file mutation | rewritten test method → false "1 error" | restore + protocol ban |
| Stochastic delegation | grep-del1 solo despite pinned protocol (22 calls, 0 children) | tabulate `delegate_fired`; no-fire legs analyzed separately |
| Integration anti-patterns | root overwrites draft (del1 call 7); pokes child session dirs (del2); subprocess-thrash (2–5 turns/leg) | driver re-entry message carries rules (patch-don't-rewrite, in-kernel pytest, no session-dir reads, tester lists test names) |

## 8. Artifacts & trace conventions

- Runners: `scripts/pa_ab_delivery.sh`, `pa_lever2.sh`, `pa_run3.sh`, `pa_devbox.sh` (all uncommitted on `eval-harness` as of 2026-08-31).
- Playbooks: `scripts/pa-playbook/PB_SHORT{.md,_v2.md}` (+ legacy `APPEND_SYSTEM*.md`).
- Results: `docs/delivery-ab-2026-08-31.md` (rounds 1–3 + devbox), `docs/results-and-retro-2026-08-30.md`.
- Traces: `/tmp/pa-*/<timestamp>/<leg>/rpc.jsonl` (filtered). Session JSONL: `~/.prime/agent/sessions/`.
- Version-control experiment assets as they evolve (lesson from playbook-restoration incident).
- "Done" = committed + pushed on `eval-harness` (fork `kkingsbe/prime-agent`).

## 9. Open items / next box

1. Runner integrity fix set (zero inference): post-load spec assert; last-importable-state snapshot scoring; 404 fail-fast; driver re-entry integration rules; `delegate_fired` metric.
2. **grep box rerun** — 4 legs (del1/del2 + solo1/solo2), LFM2.5, PB_SHORT_v2.1 pinned, pristine scoring, 900/1200 s deadlines. Question: honest del-vs-solo delta on a CLI-tool task.
3. **v3 wave/recursive delegation protocol A/B (RQ4 — the 2–3-level fan-out milestone)**: root re-delegates fixer children on integration failure; protocol describing multi-level decomposition (root → subtask children → grandchild workers), each level short-context; A/B vs v2.1 on a complex task (forth or a multi-file task). `rlmMaxDepth` (settings-manager.ts:136, default 2) already allows depth-2; `allowRecursion` is `rlmDepth < rlmMaxDepth` (agent-session.ts:4389).
4. Horizon-mix extension (RQ3 generality) after a signal.