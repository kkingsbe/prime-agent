# Decision/Decomposition Frameworks for the Orchestrator Prompt — Research (deep pass)

> Deep pass 2026-08-31/09-01 · owner Hermes + Kyle · Prompt NOT yet modified (Kyle).
> Goal: options for an injected decision flow — take task → decompose → complete **or** delegate
> → integrate — with **wide fan-out (≥3 subagents)** from a single orchestrator, for LFM2.5-2.6B.
> Primary sources cited inline (arXiv IDs / URLs). Companion to `eval-methodology.md` §9.

## 0. Decision context & hard constraints

1. **Verbosity tax (measured by us)**: long prose kills LFM2.5 delegation (criteria playbook 0/2 vs
   PB_SHORT ~700 B → 3/3). Framework must distill to ~700–1000 B imperative playbook; detail belongs
   in driver enforcement + child task text.
2. **Plan-following fidelity is poor and measurable** — From Plan to Action (arXiv:2604.12147,
   21,120 SWE-agent trajectories, 4 LLMs, 8 plan variations):
   - Without an explicit plan, agents fall back on incomplete/overfit internalized workflows.
   - A standard plan **improves** issue resolution.
   - **Periodic plan reminders mitigate violations and improve success** → the driver's re-entry
     message is a re-plan/remind hook.
   - **A subpar plan hurts more than no plan** → plan quality gate, don't inject alien phases;
     phases that clash with the model's internal strategy **degrade** performance (our verbosity-tax
     finding generalizes).
   - Recommendation: teach models to follow plans adaptively — not memorize task-specific ones.
3. **Width before depth** (Kyle): one-level wide fan-out now; 2–3-level depth is the later milestone.

## 1. Classic decision & cognitive frameworks (the "envelope")

| Framework | Origin | Loop / steps | Orchestrator mapping | Small-model fit |
|---|---|---|---|---|
| **OODA** | Boyd (military, ~1976) | Observe → Orient → Decide → Act, re-entered continuously | Decision cadence per turn; Orient = the weak small-model step (situation modeling) | Medium; prose-cheap but Orient quality dubious at 2.6B |
| **PDCA** | Deming (quality) | Plan → Do → Check → Act (adjust) | Plan in one message, Do via children, Check = tester run, Act = fix/readjust | High; near-native to our loop |
| **GTD** | David Allen | **Capture → Clarify → Organize → Reflect → Engage** | Capture = state task; Clarify = classify (SOLVE/DELEGATE/DROP); Organize = task list w/ deps; Reflect = integration review; Engage = act | **High**; 5 crisp nouns, very prompt-injectable |
| **Cynefin** | Snowden | Sense-making taxonomies (simple/complicated/complex/chaotic) → choose response mode | Choose strategy by task type: known → solve; complicated → decompose; complex → explore/parallel agents | Low-medium; classification is another 2.6B failure mode |
| **TOTE** | Miller/Galanter/Pribram; Newell/Simon | Test → Operate → Test → Exit (means-ends) | Test = tester child; Operate = fixer; loop until Test passes; Exit = final | High; already our integration loop |
| **BDI** | Rao & Georgeff (agent theory) | Belief (state) → Desire (goal) → Intention (commitment) | Give the orchestrator explicit goal + commitment discipline (intentions survive until done or abandoned) | Medium; mostly conceptual |
| **HTN planning** | Nau et al. (SHOP2, 2003) | Task → choose METHOD → subgoals → primitive actions, with preconditions | Task = exercise; method = our draft/tester/verify decomposition; preconditions = child contracts | High conceptually; prose cost high → driver-side contracts instead |
| **Checklists** | Gawande (The Checklist Manifesto) | Fixed step list, verification gates, no judgment | The protocol file IS a checklist; add explicit gate lines ("before delegating, verify plan has ≥3 tasks with deps") | **High**; checklists outperform prose for compliance |

LLM+HTN integration is active research (arXiv:2501.08068 roadmap; 2511.18165 framework; 2605.07707
LLM-generated heuristics; 2511.12901 online learning of methods).

## 2. LLM reasoning–action & planning frameworks

| Framework | Source | Core | Evidence base |
|---|---|---|---|
| **ReAct** | 2210.03629 | Interleave thought/action/observation | PaLM-540B/175B era; small-model transfer unproven |
| **Plan-and-Solve** | 2305.04091 | Zero-shot "devise a plan, then execute" | GPT-3.5; exact prompt = just two sentences → ultra-cheap |
| **Least-to-Most** | 2205.10625 | Decompose; solve in dependency order | GPT-3 (code-davinci); *positive* small-ish evidence historically |
| **Tree/Graph of Thoughts** | 2305.10601 / 2308.09687 | Search over reasoning trees | Expensive (many samples) → **skip** for a 2.6B eval rig |
| **LATS** | 2310.04406 | MCTS + value function for agents | GPT-4-class models; too heavy for us now; value-function idea = tester-as-critic |
| **Reflexion / Self-Refine** | 2303.11366 / 2303.17651 | Verbal self-reflection on failure → retry | GPT-4/GPT-3.5; the *mechanism* (write-what-failed-then-fix) is cheap and driver-embeddable |
| **As-Needed Decomposition** | 2311.05772 | Don't decompose when unnecessary; decompose when stuck/novel | Directly answers "complete **or** delegate": a solve-first, delegate-on-failure policy |
| **LLM+P / classical planners** | 2304.11477 | Plan via PDDL search, LM fills gaps | Strong but requires planner infra — out of scope for the prompt-injection question |

## 3. Decomposition & plan-compliance evidence

- **TaskBench** (2311.18760): benchmarks decomposition via "decomposer/solver" — node count, dep
  correctness, solvability. → Our plan artifacts should be scored on these axes, not just final tests.
- **Systematic decomposition** (2510.07772): reliability-oriented dependency/interface rules.
- **Second-pass gains in multi-LLM pipelines** (2604.01029): measures *why* a second agent pass helps
  (draft quality vs capability asymmetry) — informs what the "fixer child" actually contributes.
- **Planning survey** (2402.02716): planning modes (decompose, refine, retry, verify, backtrack) —
  vocabulary; **verifier mode = our tester child**.
- **Plan compliance** (2604.12147): see §0.2 — the single most actionable citation for us.

## 4. Delegation decision-making (the "complete or delegate" node)

- **Intelligent AI Delegation** (arXiv:2602.11865, 2026): positions delegation as *a sequence of
  decisions* with: task allocation, **transfer of authority/responsibility/accountability**,
  **roles & boundaries**, clarity of intent, and **trust mechanisms**; must adapt to environmental
  change and unexpected failure. → Each child task should carry a boundary spec ("you own file X,
  not Y"), which is exactly the contract our draft/tester split needs to formalize.
- **Utility-aware task decomposition & exchange** (multiagents.org 2026): agents estimate utility of
  decomposing/exchanging subtasks and validate per turn. → A cheap proxy rule for a 2.6B:
  "delegate when the subtask needs a different focus than your current context; solve when you can
  finish in ≤1-2 turns."
- **Delegation security**: Cerbos on "delegation without attenuation" (tokens/authorization passed
  downstream unchanged) — sub-agents inherit full scope; relevant later for tool scoping.
- **Agent-as-a-Tool** (Google Next '26 pattern; OpenAI Agents SDK): treat child agents as tools the
  orchestrator calls — exactly our `delegate` tool semantics.

## 5. Orchestration systems & industry patterns

| System | Pattern | Lesson for us |
|---|---|---|
| **Anthropic Research multi-agent** (blog 2025-06) | Orchestrator-worker; **parallel subagents with own context windows**; "the essence of search is compression — subagents explore in parallel, condense tokens for the lead" | Industry validation of our short-context thesis; children should RETURN SUMMARIES, not dumps |
| **Claude Code workflows** (code.claude.com) | "**Move the plan into code**": workflow script holds the loop/branching; model context holds only the answer | Driver-side orchestration (our pa_rpc re-entry + task list) IS the right architecture; don't expect the model to hold the whole plan in context |
| **Claude Code subagents** | Agent tool with context isolation | Children should NOT see parent's full history (ours already isolate) |
| **OpenAI Swarm / Agents SDK** | Agent + handoffs; agents-as-tools; routines | Handoff = our terminate:true; routines = playbook |
| **LangGraph supervisor** | Supervisor graph routes to specialists, validates | Graph = our driver loop; supervisor = root |
| **CrewAI hierarchical** | Manager creates/assigns tasks and **validates outcomes**; delegation explicit | Manager-validation as a first-class step (verifier child); delegation NOT ambient |
| **AgentOrchestra / TEA** | 2506.12508 — planner assigns to versioned entities/tools/envs; lifecycle awareness | Task/tool versioning = our per-turn snapshots; traceability |
| **HuggingGPT** | 2303.17580 — LLM brain: task parsing → planning (list w/ deps) → dispatch → response | The canonical WIDTH pattern (one child per task item) |
| **MetaGPT** | 2308.00352 — SOPs + role specialization, structured intermediates | Fixed roles + handoff artifacts (PLAN.md → reports) |
| **Voyager** | 2305.16291 — skill library + automatic curriculum | Later: reusable child "skills" per subtask class |

## 6. Small-model capability evidence (feasibility)

- **TinyAgent** (2409.00608): 1.1B/7B function calling **after curated SFT** — small models need
  function-calling training; vanilla small models are weak tool-callers.
- **SLM agentic evaluation** (2511.22138): SLMs measured on **BFCL categories — simple, multiple,
  parallel, parallel-multiple, relevance detection** — with SFT/PEFT/RL/DPO gains. Critical detail:
  **parallel-multiple** (emit several tool calls in one message) is the hardest category; our
  "delegate 3 children in ONE message" is exactly parallel-multiple.
- **Small reasoning models are instruction followers in function calling** (2608.22472, 2026):
  instruction-following with reasoning — supports keeping thinking on.
- **Instruction Hierarchy** (2404.13208, OpenAI): models prioritize system > user > tool inputs.
  After training; for vanilla LFM2.5, hierarchy is weaker → protocol must live in the *highest
  weighted* position we control + be repeated (periodic reminders, per 2604.12147).
- **Our measurements (2026-08-31)**: PB_SHORT ~700 B → 3/3 delegations; longer prose → 0/2;
  pinned path → 4/5 fire; grep-del1 went solo (stochastic); children follow the in-kernel pytest
  line while the root ignores its own protocol copy.

**Design implication (important):** expecting LFM2.5 to emit 3+ *parallel* delegate calls in one
message targets its weakest capability (BFCL parallel-multiple). The robust pattern is: the model
writes the **task list** (its strength: produced sequential text), and the **driver fans out N
children deterministically** from that list. Width becomes framework-enforced, not model-emitted.

## 7. Design implications (numbered)

1. **Width via driver, not parallel tool emission** — model writes PLAN (≥3 tasks w/ deps); runner
   parses and spawns one child per task. Deterministic ≥3 fan-out.
2. **Periodic plan reminders** — driver re-entry message re-states the plan + remaining tasks
   (2604.12147 "periodic plan reminders mitigate violations").
3. **Plan-quality gate** — abort/flag if plan <3 tasks or deps nonsense (subpar plan < no plan).
4. **Boundary specs per child** (2602.11865) — task text includes ownership scope + report format.
5. **Children return summaries, not dumps** (Anthropic compression) — tester reports = counts +
   names; draft reports = file paths + 1-line status.
6. **Checklist gates over prose** (Gawande; our verbosity tax) — the playbook is a checklist; gates
   verified by the driver (e.g., "plan file exists", "children spawn count == plan length").
7. **Solve-first, delegate-when-stuck** (as-needed decomp, 2311.05772) — completion-or-delegation
   rule: "do it yourself if ≤2 turns; else delegate."
8. **Reflect step on failure** (Reflexion) — integration re-entry forces a one-line failure
   diagnosis before fixes.
9. **Verify with a role, not a vibe** (CrewAI validate; τ-bench-style policy docs, 2406.12045) —
   tester/verifier child gates completion; τ-bench as a future measurement of policy adherence.

## 8. Candidate orchestrator designs (for a later explicit choice — prompt still untouched)

### Design A — PLAN-LIST (HuggingGPT + driver fan-out + reminders)
Playbook (~8 lines): "Write PLAN.md: ≥3 numbered subtasks with dependencies. Sign off. Your turn
ends." Driver reads plan → spawns N children (one per task) → on child-done, re-enters root with
remaining-task reminder → root integrates → verifier child pass.
- Width: **deterministic N** by construction. Cost: ~800 B. Risk: LOW (model does the easy part).
- Measures: plan-filled (N≥3), spawn==plan ratio (plan compliance!), per-task pass rate.

### Design B — GTD-ORCH (GTD loop as the decision node)
Playbook (~9 lines): "CAPTURE the task. CLARIFY each item: SOLVE (≤2 turns) / DELEGATE (child) /
SKIP. ORGANIZE the delegate list. ENGAGE: dispatch. REFLECT after test runs; fix or re-delegate."
- Gives the complete-or-delegate decision structure explicitly + Reflect integration.
- Width: model-driven (weak spot) → pair with A's driver fan-out for the plan portion.
- Cost: ~900 B. Risk: medium (classification step may misfire at 2.6B).

### Design C — OODA-LITE (decision cadence)
Playbook (~7 lines): per cycle: "OBSERVE current state/tests. ORIENT: what changed, what's unknown.
DECIDE per item: solve / delegate / verify. ACT: execute or delegate; end turn."
- Cheap, loop-native. Risk: Orient degenerates at 2.6B (vagueness), so ORIENT is the line to pin
  with a concrete template ("state: files+tests+reports; unknown: …").
- Width: model-driven → pair with A.

### Design D — CONTRACT-HTN (HTN-ish, driver-validated)
Playbook (~6 lines) + driver-side method table: root picks methods (IMPLEMENT/VERIFY/FIX) with
preconditions; driver checks preconditions before spawning.
- Most rigorous, most driver work. Risk: prose cheap but the model must choose valid methods
  (classification risk again).

**Recommended build order:** A (width foundation; driver fan-out is the piece every later design
reuses) → fold B's REFLECT line into the driver re-entry → C or D only if adherence metrics show
the loop needs an explicit decision cadence.

## 9. Measurement plan (ties to methodology §5)

- **Plan compliance**: `plan_tasks` (parsed from PLAN.md), `spawns`, `spawn/plan ratio`,
  dependency order respected (file timestamps/turn order).
- **Delegation decision quality**: per-task outcome (pass/fail) + whether it was solved locally vs
  delegated (utility-aware framing); "delegated-but-trivial" and "solved-locally-but-wrong" counts.
- **Adherence**: plan-violation events (root implements a delegated task itself; child exceeds
  boundary), time-to-first-delegate, reflect-line presence after failures.
- **Capability baselines**: BFCL-style micro-probe for LFM2.5 (single / multiple / parallel /
  parallel-multiple) to quantify the dispatch-weakness claim before designing around it.
- Future: τ-bench (2406.12045) for policy-following, TaskBench-style decomposition scoring.

## 11. Comparative plan: four designs (A–D) + additive components

### 11.1 Design comparison matrix

| Dimension | A PLAN-LIST | B GTD-ORCH | C OODA-LITE | D CONTRACT-HTN |
|---|---|---|---|---|
| Model artifact | `PLAN.md` (≥3 tasks + deps) | classification list (SOLVE/DELEGATE/SKIP per item) | per-turn decision line (Observe→Orient→Decide→Act) | method choice (IMPLEMENT/VERIFY/FIX + preconditions) |
| Width source | **driver spawns N from plan** | model-emitted delegate batch | model-emitted delegate batch | driver-validated methods → spawn |
| Prose cost | ~800 B | ~900 B | ~700 B | ~600 B + driver method table |
| Driver work | medium (parse plan, spawn, reminders) | medium (same plumbing) | low (cadence check only) | high (method/precondition validator) |
| 2.6B risk | **low** (model does its strong part: sequential text) | medium (classification misfires) | medium (Orient vagueness → pin template) | medium-high (invalid method picks) |
| Headline metric | spawn÷plan compliance | decision quality (delegated vs solved-own correctness) | cadence adherence | contract violation count |

### 11.2 Staged execution (sequential legs, same model+bench, n=2/cell, grep box)

- **Phase 0** (no inference): build driver ([link to plan]) + BFCL-style micro-probe of LFM2.5
  (single/multiple/parallel/parallel-multiple) to quantify dispatch weakness. 1 short leg.
- **Phase 1 — A vs control**: A1/A2 vs PB_SHORT_v2.1-del1/del2 (4 legs). Validates driver fan-out
  end-to-end; establishes compliance baseline.
- **Phase 2 — B vs D** (4 legs): the two model-driven designs with the clearest contrast
  (classification vs contracts). C runs only if cadence adherence data from A/B phases says the
  loop needs an explicit per-turn decision (otherwise C is redundant with the ReAct-native loop).
- **Phase 3 — additive deltas**: winner + each additive component toggled (2 legs per component).
- Gate rule (Kyle): metrics gate next leg; one variable per run; no score claim <2 repeats/cell.

### 11.3 Additive components (orthogonal, stackable on any design)

| # | Component | Origin | Mechanism | Effort |
|---|---|---|---|---|
| 1 | **Reflexion failure line** | Reflexion 2303.11366 | driver re-entry forces "what failed + why" 1-liner before fix | trivial (driver text) |
| 2 | **Plan reminders** | 2604.12147 | driver re-entry re-states plan + remaining tasks | trivial |
| 3 | **Boundary specs per child** | 2602.11865 | task text: "you own X, not Y; report format: …" | trivial (task template) |
| 4 | **Summaries-not-dumps** | Anthropic multi-agent | child reports = counts + names + paths + 1-line status | trivial (report template) |
| 5 | **Verifier child** | CrewAI/TOTE | dedicated 3rd child gates completion | medium (earliest for A) |
| 6 | **Checklist gates** | Gawande | driver asserts: plan exists, N≥3, spawn==plan, in-kernel tests, no session-dir reads | medium |
| 7 | **Few-shot seed** | L2M 2205.10625 | one good plan+delegate example in playbook (exemplar > prose for small models) | trivial |
| 8 | **Solve-first rule** | 2311.05772 | "≤2 turns local, else delegate" | trivial |
| 9 | **Machine-parseable plan schema** | — | `##T<id>: <desc> | dep: T<id>` → enables fan-out + compliance metrics | low (parser) |
| 10 | **Wave summary (BRIEF.md)** | Anthropic context mgmt | root writes condensed result summary after each wave (long-horizon) | low |
| 11 | **Fix-cycle cap** | our 27-turn thrash | max N fix waves, then delegate fix to child | low |
| 12 | **No-overwrite rule** | trace forensics | integration patches draft file, never rewrites from scratch | trivial |
| 13 | **Dispatch retry** | plan fidelity | spawn < plan → driver re-prompts once | low |

Priority order (leverage ÷ effort): 1, 2, 3, 7, 8 first (all trivial); 9 as the enabler for A's
compliance metrics; 4, 12 fold into the task/report templates; 5, 6 when width is stable; 10, 11
when integration shows long-horizon bleed; 13 if compliance data shows drift.

## 12. Sources (all verified reachable 2026-09-01)
- ReAct 2210.03629 · Plan-and-Solve 2305.04091 · Least-to-Most 2205.10625 · ToT 2305.10601 ·
  GoT 2308.09687 · LATS 2310.04406 · Reflexion 2303.11366 · Self-Refine 2303.17651 ·
  As-Needed Decomp 2311.05772 · LLM+P 2304.11477 · TaskBench 2311.18760 ·
  Systematic Decomp 2510.07772 · Second-pass gains 2604.01029 · Planning survey 2402.02716 ·
  **Plan compliance 2604.12147** · **Intelligent Delegation 2602.11865** · HTN: 2501.08068,
  2511.18165, 2605.07707, 2511.12901 · τ-bench 2406.12045 · Instruction Hierarchy 2404.13208 ·
  TinyAgent 2409.00608 · SLM agentic eval 2511.22138 · Small reasoning FC 2608.22472 ·
  MetaGPT 2308.00352 · HuggingGPT 2303.17580 · AgentOrchestra 2506.12508 · Voyager 2305.16291 ·
  CoALA 2309.02427 · Crowd: anthropic.com/engineering/multi-agent-research-system,
  code.claude.com/docs/en/workflows, github.com/openai/swarm, docs.crewai.com hierarchical,
  gettingthingsdone.com (GTD), wikipedia (OODA/PDCA/Cynefin/BDI/SHOP2)