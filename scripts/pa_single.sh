#!/usr/bin/env bash
# pa_single.sh — harness-lift condition (B): ONE prime-agent session per exercise,
# prompt invites the MODEL to decompose/delegate via rlm() subagents (no user-side fan-out).
# Scores with same .venv-bench pytest as aider; extracts delegation usage from the trace.
# Usage: pa_single.sh <model-id> [exercise...]
set -u
MODEL="${1:-bartowski/Ling-3.0-tiny-GGUF}"
SRC=/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice
WORK=/tmp/pa-single
PA=/opt/data/repos/prime-agent/prime-agent.sh
PYTEST=/opt/data/repos/aider/.venv-bench/bin/python
PLAYBOOK=/opt/data/repos/prime-agent/scripts/pa-playbook/APPEND_SYSTEM.md
export RIG_API_KEY="$(cat /opt/data/.unsloth_api_key)"
shift || true
EXS=("$@")
[ ${#EXS[@]} -eq 0 ] && EXS=(grade-school list-ops phone-number simple-linked-list transpose robot-name)

rm -rf "$WORK"; mkdir -p "$WORK"
echo "SINGLE start $(date -u +%H:%M:%S) model=$MODEL exercises=${#EXS[@]} playbook=$([ -f "$PLAYBOOK" ] && echo ON || echo OFF)"

for ex in "${EXS[@]}"; do
  mkdir -p "$WORK/$ex"
  cp -r "$SRC/$ex/." "$WORK/$ex/"
  [ -f "$PLAYBOOK" ] && cp "$PLAYBOOK" "$WORK/$ex/APPEND_SYSTEM.md"
  cd "$WORK/$ex" || continue
  if [ "${PA_FORCE_DELEGATE:-0}" = "1" ]; then
    PROMPT="Work on the '$ex' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE DELEGATION PROTOCOL IN APPEND_SYSTEM.md — it is MANDATORY: decompose this task and spawn at least two rlm() subagents (a 'draft' child and a 'tester' child, plus any others you need) in a single turn, end your turn, then integrate their results via files and agent_message replies. Apply the final solution to the files yourself and verify the tests pass before finishing."
  else
    PROMPT="Work on the '$ex' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. You may delegate subtasks to parallel subagents with await rlm('...') — for example dispatch one subagent to read context and draft the implementation while another runs the test suite, then integrate their results (subagents reply via agent_message). Apply the final solution to the files yourself and verify the tests pass before finishing."
  fi
  timeout 600 "$PA" --mode json --provider rig --model "$MODEL" "$PROMPT" \
    > run.jsonl 2> run.err
  echo "$?" > exit.code
  "$PYTEST" -m pytest -q 2>/dev/null | tail -1 > pytest.out || true
  # delegation metrics from the trace
  rlm_calls=$(python3 /opt/data/repos/prime-agent/scripts/pa_trace_analyze.py run.jsonl 2>/dev/null | awk -F': ' '/ipython_turns_containing_rlm_code|rlm_named_tool_events/ {s+=$2} END {print s+0}')
  agent_msgs=$(python3 /opt/data/repos/prime-agent/scripts/pa_trace_analyze.py run.jsonl 2>/dev/null | awk -F': ' '/agent_message_events/ {print $2}')
  tools=$(python3 /opt/data/repos/prime-agent/scripts/pa_trace_analyze.py run.jsonl 2>/dev/null | awk -F': ' '/tool_execution_total/ {print $2}')
  echo "[$(date -u +%H:%M:%S)] $ex exit=$(cat exit.code) rlm_calls=$rlm_calls agent_msgs=$agent_msgs tool_calls=$tools score=$(cat pytest.out)"
done
echo "SINGLE done $(date -u +%H:%M:%S)"