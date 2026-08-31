# Prime Agent — Research & Eval Integration Plan

> Status: researched + downloaded + build-verified (`v0.8.1` runs from source).
> Date: 2026-08-30 · Repo: https://github.com/PrimeIntellect-ai/prime-agent (MIT, built on `pi`/earendil-works)
> Paper: arXiv:2608.23552 · Blog: https://www.primeintellect.ai/blog/prime-agent

## 1. What it is

Open-source coding/research agent harness (TypeScript monorepo). Two core abstractions:

- **RLM (Recursive Language Model)** — persistent IPython REPL is the model's only built-in tool;
  recursive subagents via `rlm(...)`; everything (files, bash, context) is programmatic.
- **Continual Harness** — durable session state: memories, skills (importable Python packages),
  subagent specs, `/refine` self-improvement with evidence-backed updates + rollback.

Long-horizon / eval-oriented features: daemon-backed sessions, compaction, goals,
heartbeats/schedules, bounded `/autonomous` mode (turn/token/time budgets + quality gates).

Paper headline numbers: ARC-AGI-3 RHAE Best@1 30% → 95.5%; matches/exceeds native+popular
harnesses on long-context coding, GPU-kernel gen, emulator construction, nanoGPT speedruns, Factorio.

## 2. Local install (verified)

- Clone: `/opt/data/repos/prime-agent` (24 MB).
- Build: `npm ci` (~50 s) — Node 22.22.3 (req ≥ 22.8) ✓.
- Run from source: `./prime-agent.sh --version` → `0.8.1` (matches latest GitHub release).
- Binary install alternative: `curl -fsSL https://app.primeintellect.ai/prime-agent/install.sh | sh`.

## 3. Integration surfaces (the parts that matter for evals)

| Surface | What it gives us |
|---|---|
| `models.json` (`~/.prime/agent/models.json`) | Custom providers: `openai-completions` / `openai-responses` / `anthropic-messages` / `google-generative-ai` against any `baseUrl`. Ollama, vLLM, LM Studio named explicitly. **Rig endpoints work out of the box.** `compat` flags for local-server quirks: `supportsDeveloperRole`, `supportsReasoningEffort`, `supportsUsageInStreaming`, `maxTokensField`, `thinkingFormat` (deepseek/zai/qwen). |
| ACP mode | Agent Client Protocol (JSON-RPC 2.0 over NDJSON) — any ACP client or **eval harness** can drive it. This is how verifiers drives prime-agent. |
| JSON mode (`--mode json`) | One-shot headless runs, full event stream as JSONL (turns, tool execs, compaction, retries). Easy scoring pipeline. |
| RPC mode (`--mode rpc`) | Full JSONL protocol: `prompt`/`steer`/`bash`/`get_messages`/`set_model`/`set_thinking_level`/`compact`/schedules/heartbeats/`observe`. Best for programmatic eval drivers. |
| Autonomous budget flags | `--autonomous-max-turns/-tokens/-timeout-ms`, `--autonomous-gate "<shell cmd>"` (quality gate with retries), `--autonomous-max-continuations`. Reproducible, bounded eval runs. |
| Sessions | JSONL under `~/.prime/agent/sessions/` — full trajectories for post-hoc scoring. |
| Kernel | `PRIME_AGENT_KERNEL_PYTHON` can point at an existing venv (e.g. one with cadquery/trimesh for CAD work). |

## 4. The key find — verifiers has a native `prime_agent` harness

PrimeIntellect's eval/RL engine **verifiers** (https://github.com/PrimeIntellect-ai/verifiers,
MIT, "RL environments + evals") ships `verifiers/v1/harnesses/prime_agent/`:

- Drives Prime Agent over its **native ACP mode** with an **intercept provider**
  (`PRIME_AGENT_INTERCEPT_KEY`) — verifiers *owns* the model endpoint, so any
  OpenAI-compatible backend listed in `configs/endpoints.toml` can serve the model,
  including a local rig (llama.cpp / vLLM).
- Pins prime-agent **v0.8.1** commit `5146337...` (identical to what we built).
- Installer grabs the four release tarballs (`prime-agent` + `pi-ai`/`pi-core`/`pi-tui`),
  sha256-verifies, repacks, `npm install -g`.
- Flags: `SUPPORTS_MCP`, `SUPPORTS_RESUME`, `SUPPORTS_SKILLS`, optional `autonomous: true`.
- Other harnesses for A/B comparison: `claude_code`, `codex`, `pi`, `hermes_agent`,
  `kimi_code`, `mini_swe_agent`, `bash`, `browser_use`, `null`, `pool`.

Eval runner usage (verifiers):
```bash
uv run eval @ config.toml
```
```toml
model = "<endpoint-id-or-model>"            # from endpoints.toml → can be rig
[sampling]
temperature = 1.0
[env.taskset]
id = "primeintellect/terminal-bench-2"      # or code_golf / gsm8k / deepwiki / wordle / ...
[env.agent.harness]
id = "prime_agent"                          # ← our harness
[env.agent.runtime]
type = "docker"
```
Outputs: `outputs/<env>--<model>--<harness>/<uuid>/` with `traces.jsonl` + logs;
`--resume` re-runs only missing/errored rollouts. Requires Python ≥3.11,<3.14 ✓ (3.13.5),
uv ✓ (0.11.6), docker runtime for sandboxed envs.

## 5. Fit against our existing benchmarks (local inventory)

Kyle's correction (2026-08-30): we ALREADY run a bench stack here — prime-agent is a new
*harness* that can drive the SAME tasksets head-to-head against aider's harness, not a
replacement stack. Key point: aider polyglot's scoring (pytest per exercise → pass_rate_1/2)
is harness-agnostic — any harness that produces an edited exercise file scores identically.

| Existing bench (local) | Where it lives | Fit with prime-agent | How |
|---|---|---|---|
| **Aider polyglot** — 225 Exercism exercises (cpp/go/java/js/python/rust) | `/opt/data/repos/aider` + `tmp.benchmarks/polyglot-benchmark`, run via `scripts/aider_bench.sh` → litellm → rig :8888 (pilot 2026-08-23, docs/benchmark-aider-polyglot.md) | ✅✅ **Best first target — harness A/B on same taskset** | Run each exercise dir as a prime-agent workdir: JSON/RPC prompt → agent edits via kernel/bash → score with the SAME pytest suite + `.aider.results.json` shape. Bonus: prime-agent's tool loop means the model doesn't emit strict whole/diff edit formats — sidesteps the pilot gotchas (thinking/tool-wrapper models fail aider's edit format). |
| **CADTestBench** — text-to-CAD (`/opt/data/repos/CADTestBench`, tiel_generate.py) | active bench rig | ✅ Strong | JSON/RPC driver per sample with `--autonomous-gate` = CAD validity/geometry check; or verifiers environment wrapping CAD tasksets. |
| **RepoBench / LongBench** — lcc (max 10k ctx) + repobench-p (max 18k ctx), edit_sim scoring, local parquet | `data/longbench/*.parquet` via lm_eval pipeline (`repobench_grid_driver.py`, ruler length-bucketed) | ⚠️ Low value | Single-shot completion tasks, no test loop — lm_eval is the right tool. Only agentic angle: cross-file "fix" variants, not worth it. |
| **RULER niah_single_1** (64, length-bucketed 4k–65k) | lm_eval generative | ❌ No | Needle-in-haystack, static. |
| **humaneval (164) / mbpp (500) / gsm8k (1319)** | lm_eval (`bench-sizes.json` canonical) | ⚠️ gsm8k no; humaneval/mbpp optional | gsm8k = single-turn, keep lm_eval. humaneval/mbpp CAN run agentic (write → run tests → fix) — a different capability than pass@k; only if a harness-comparison run is wanted. |
| **model-lab ledger/dashboard** (Mongo `model_lab`, bench-sizes.json, eval_queue/nightly grid) | `/opt/data/repos/unsloth-model-lab` | ✅ Adapt results in | New harness outputs must land in ledger.json/Mongo via an adapter (like aider pass_rate_1/2 → ledger row). Nightly grid keeps its window rules. |
| **LLM homelab rigs** (llama.cpp :8888 auto-switch ON, LM Studio :1234) | `.unsloth_api_key` | ✅ Native | prime-agent `models.json` custom provider (`openai-completions`, `maxTokensField: "max_tokens"`) OR verifiers `endpoints.toml` `type = "openai_chat_completions"`. POST /v1/load first (server serves only loaded model). |

Static knowledge benches (MMLU/HellaSwag loglikelihood) stay in lm_eval (Unsloth `/v1/completions`
has no logprobs anyway — generative-only per lab AGENTS.md).

### M0 results (B2, 2026-08-30 16:19–16:38) — harness lift reproduces

6 python exercises × Ling-3.0-tiny, aider (A, whole-format, threads=1) vs prime-agent (B, one session/exercise):

| exercise | A (aider) | B (prime-agent) | B tool calls | delegations |
|---|---|---|---|---|
| grade-school | ❌ 0/20 | ✅ 20/20 | 22 | 0 |
| simple-linked-list | ❌ 0/20 | ✅ 20/20 | 24 | 0 |
| list-ops | ❌ 22/24 | ❌ 22/24 (identical signature) | 21 | 0 |
| phone-number | ❌ 0/21 | ❌ 0/21 (identical) | 14 | 0 |
| transpose | ❌ | ❌ 0/12 (600s timeout, 156 tools) | 156 | 0 |
| robot-name | ❌ 0/4 | ❌ 0/4 (was 4/4 with detailed prompt — variance) | 18 | 0 |

**A 0/6 · B 2/6.** Identical failure signatures on list-ops/phone-number = model ceiling, not harness.
`rlm_calls=0` everywhere — Ling never composed delegation even though max depth = 2 default and the
built-in delegation guidance WAS in its prompt.

### M0b — why no delegation (research 2026-08-30)

- `rlm` is a **kernel-preloaded Python global**; the model must WRITE `await rlm('subtask')` as Python.
  Not a tool schema the model can call through normal function-calling.
- Prompt surface: `buildRlmPrompt()` teaches mechanics ("A callable `rlm` is already in your global
  namespace…") only when `allowRecursion && hasIpython`; `buildSubagentGuidance()` ("# Delegating to
  sub-agents" — when/why + Claude-Code-style menu) is appended right after (system-prompt.ts:136-145).
- Default `rlmMaxDepth` = 2 (settings-manager.ts:136 — `RLM_MAX_DEPTH`, then 2), so recursion was ON
  and guidance present. Conclusion (Kyle): passive mention ≠ taught behavior — a **prompt/teaching
  level** issue across models, not a tiny-model-only one.
- **Fix lever (native, no code changes):** `APPEND_SYSTEM.md` auto-appended from cwd or home
  (usage.md:151) and/or `--append-system-prompt <text>` CLI (repeatable). `--system-prompt` replaces.
- Delegation playbook written: `scripts/pa-playbook/APPEND_SYSTEM.md` (mandatory protocol: spawn
  draft + tester children in ONE turn, end turn, integrate via agent_message/files).
  `pa_single.sh` now drops it into every exercise workdir (`playbook=ON` in header).
- Probe in flight: forced-delegation task (2 children) on Ling to confirm children run headless in
  JSON mode + whether playbook makes Ling delegate.

### M0c — improvements for next test (B3)

1. Playbook (APPEND_SYSTEM.md) active — mandatory ≥2 children per exercise, directive tone.
2. Verify probe: children spawn headless (agent_message events, child files) — if json mode can't
   host children, move B to RPC/daemon mode.
3. If Ling still won't delegate: LFM2.5-2.6B leg (same playbook) — its own agentic/tool-call bias
   (lab notes) should take to rlm() better; keeps the "small model" claim.
4. Optional: child model pinning (e.g., Tiel 35B reviewer child) as a cost-aware variant.
5. Track per-exercise `rlm_calls` (child spawns), `agent_msgs`, child session dirs.

### M0d — fixes for next iteration (agreed 2026-08-30)

1. **Rig context/parallel:** reload Ling with `max_seq_length: 131072` (native max) + `n_parallel: 2`
   → **~65k ctx/slot** for root+children concurrently. No more "Context size has been exceeded".
   (Kyle: "ctx/n to be like 50k or so"; 131072/2 = 65536.)
2. **prime-agent models.json:** `contextWindow: 52000` (Kyle: **use 80%, leave 20% headroom** — not
   16k; compaction fires before the 65k server slot cap), `maxTokens: 16384`.
3. **RPC mode driver:** JSON one-shot ends the root session at turn end → child agent_message replies
   NEVER bubble up (proven in list-ops trace: root ended "Let me wait for their results",
   agent_end fired, children orphaned; 0/2 children reached terminal state, 4 errors incl. 1 ctx
   overflow). RPC keeps the session alive so the parent can re-enter after child replies
   (probe then full sweep).
4. **Spawn-first prompt:** root must delegate reading/execution immediately, not burn 7 turns of its
   own context before spawning (list-ops root did exactly that).
5. **Metrics emitter:** `scripts/pa_metrics.py` — per-exercise: spawns, child_terminal rate,
   child_errors/overflows, bubble-up (real deliveries only: `customType:"agent_message"` /
   `agent_message.send`, not playbook echo), ctx_overflow, clean_exit, zero_effort, tool_turns.
   Validated on list-ops (2 spawns / 0 terminal / 4 errors / clean_exit NO).

### Metrics spec (from issues, Kyle approved 2026-08-30)

| Issue | Metric | Definition | Source |
|---|---|---|---|
| No bubble-up | `bubble_up_rate` | exercises re-entered after ≥1 child reply ÷ with spawns | RPC stream/trace |
| | `child_replies` | deliveries INTO parent | child+root jsonl |
| | `parent_integration_turns` | root turns after first real delivery | trace |
| Child reliability | `child_terminal_rate` | children clean-complete ÷ spawned | child files |
| | `child_error_rate` | stopReason ∈ {error, aborted} ÷ child turns | child files |
| Context | `ctx_overflow_events` | "Context size has been exceeded" per run | grep |
| | `peak_ctx_util_pct` | max context ÷ contextWindow | rig monitor |
| Eval integrity | `clean_exit_rate` | agent_end + stopReason=stop, no aborts | trace |
| | `clean_pass_rate` | passes on clean-exit runs only | runner |
| | `zero_effort_rate` | ≤1 tool call exercises | trace |
| Efficiency | `wall_s`, `tool_calls`, `trace_mb` | per exercise (provider usage=0; monitor tok/s) | runner+monitor |
| Delegation value | `delegation_delta` | Δ pass: delegation-forced vs solo, same exercise+model | A/B |
| Noise | `run_variance` | repeat same exercise ×3 → std | repeats |

Targets: bubble_up_rate ≥ 0.8 · child_terminal_rate ≥ 0.9 · ctx_overflow = 0 ·
clean_exit_rate = 1.0 · zero_effort_rate → 0.

### M0e — rlm.yield_turn implemented (2026-08-30, hypothesis test result)

**Hypothesis (Kyle):** does a smarter model self-yield after delegation? Tested with a
fail-fast yield eval (`scripts/pa_yield_eval.py`, ~40s verdict, early-kill):

| model | self-yield (teaching) |
|---|---|
| Ling-3.0-tiny | ❌ FAIL |
| LFM2.5-2.6B | ❌ FAIL |
| Tiel-35B-A3B-MTP (UD-IQ3_XXS, 131k/1 slot) | ✅ PASS (spawn → plain-text yield, 134s) |

Conclusion: teaching (playbook "HOW TO END YOUR TURN") is enough for smarter models;
small models have a continuation-bias floor no matter the instruction.

**Fix — `rlm.yield_turn()` deterministic primitive (implemented, Ling now PASSes in ~20s):**
- Kernel: `prime-agent-runtime/src/rlm/__init__.py` — `yield_turn()` module fn +
  `rlm.yield_turn()` callable, `host_request("rlm.yield_turn")`. Synced to
  `packages/coding-agent/dist/prime-agent-runtime/` (bootstrap prefers dist).
- Host: `agent-session.ts` — `_yieldRequested` flag + `"rlm.yield_turn"` handler;
  ipython tool options get `takeYieldRequest()` (read-and-reset).
- Loop wiring: ipython.ts execute returns `terminate: takeYieldRequest() ?? false`;
  `shouldTerminateToolBatch` (all results terminate) → `hasMoreToolCalls=false` →
  turn ends, no follow-up LLM call (agent-end when no follow-ups/continuations).
- Yield eval accepts terminate-style yield (agent_end right after spawn, no tool msg).
- Playbook v5: `await rlm.yield_turn()` as the last line of the spawn cell.
- Typecheck: `tsgo --noEmit -p tsconfig.build.json` clean.
- Result: Ling yield eval **PASS 19.9s** (was FAIL across 5 probes). Fresh-workdir
  kernel bootstrap can eat 2-4 min — eval deadline must exceed it (~600s).

## 6. Proposed milestones

### M0 — harness-lift experiment (IN FLIGHT 2026-08-30)

Kyle's framing: prime-agent's value for small models is the model's OWN delegation
(`rlm()` subagents inside one session) — NOT user-side session fan-out. Question: does
the harness lift small-model scores vs the same evals run outside the harness (aider)?

- **A (baseline, outside harness):** aider benchmark.py, whole edit format, threads=1,
  `openai/bartowski/Ling-3.0-tiny-GGUF` (already in model-metadata.json from 08-23 ling-probe)
- **B (harness):** `scripts/pa_single.sh` — ONE prime-agent session per exercise, prompt
  invites decomposition via `await rlm('...')` subagents; model decides whether to delegate
- **Subset:** grade-school, list-ops, phone-number, simple-linked-list, transpose, robot-name (python)
- **Scoring:** identical `.venv-bench` pytest (same as aider_bench.sh); B also extracts
  `rlm_calls` / `agent_msgs` / `tool_calls` per trace for delegation-usage analysis
- **Rig:** Ling-3.0-tiny loaded via `/v1/load` with **`n_parallel` OMITTED** (llama-server
  `--parallel` default) so the server can serve concurrent decode slots
- **Proven so far:** single-session robot-name → 4/4 PASS, model self-verified via kernel
  (trace `/tmp/pa-smoke/baseline.jsonl`, 14k lines; independent pytest confirms)
- **Superseded:** `scripts/pa_swarm.sh` (user-side parallel sessions) — NOT the experiment,
  dropped by Kyle; kept only as a throughput curiosity.

- **M0 — smoke (today/repo)**: models.json → rig llama.cpp/vLLM endpoint; run
  `./prime-agent.sh --mode json "trivial task"`; confirm tool loop + session JSONL.
- **M1 — verifiers eval on rig**: `uv tool install prime` (or repo checkout) + `uv run eval`
  with `harness.id = "prime_agent"`, small taskset (code_golf or gsm8k), `num_tasks` ~10,
  shallow per Kyle's preference (small n, capped limits, time-boxed).
- **M2 — CADTestBench integration**: verifiers environment wrapping CADTestBench tasks
  (or direct JSON-mode driver with gates); score via existing tiel_generate.py pipeline;
  optionally publish to model-lab live dashboard.
- **M3 — ledger/dashboard plumbing**: prime-agent/verifiers traces.jsonl → model-lab ledger.

## 7. Risks / notes

- **Not a sandbox**: releases model-generated Python with user permissions; run rollouts in
  docker runtime (verifiers default) or disposable worktrees on tasks that touch the filesystem.
- Version pinning: verifiers pins prime-agent commit; upgrading prime-agent needs the
  harness's `commit`/`PRIME_AGENT_VERSION` bumps. We built from source (matches pinned v0.8.1);
  a binary install (`install.sh`) is the faster path for the eval runtime.
- Kernel bootstrap: first kernel use installs `prime-agent-runtime` python env
  (`PRIME_AGENT_BOOTSTRAP_KERNEL_ON_INSTALL=0` to defer; `PRIME_AGENT_KERNEL_PYTHON` to reuse).
- ACP + intercept provider means **verifiers controls the model call** — honest measurement,
  but test that our rig endpoint handles the exact request shapes the intercept server sends
  (reasoning params, tool schemas).

## 8. References

- Repo: https://github.com/PrimeIntellect-ai/prime-agent · Paper: https://arxiv.org/abs/2608.23552
- Prime Agent docs: `packages/coding-agent/docs/` (providers.md, models.md, json.md, rpc.md,
  usage.md, acp.md, custom-provider.md)
- Verifiers: https://github.com/PrimeIntellect-ai/verifiers · harness: `verifiers/v1/harnesses/prime_agent/harness.py`
- Eval usage: `docs/v1/evaluation.md` · endpoints: `configs/endpoints.toml` · harness list: `docs/v1/harnesses.md`