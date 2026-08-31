#!/usr/bin/env bash
# pa_ab_criteria.sh — A/B: task acceptance-criteria arm vs recorded open-task arm.
#
# Arm A (control, RECORDED): delegate-tool run1 (4/21) + run2 (6/21) — open-ended child
# tasks (pre-criteria playbook). Data in /tmp/pa-tool-exp/20260831-001625/.
#
# Arm B (treatment): same delegate-tool stack, but APPEND_SYSTEM_B.md now carries
# VERIFIABLE acceptance criteria in the task templates (draft iterates to best pytest
# count then stops; tester runs once). 2 runs, LFM2.5, phone-number.
#
# Usage: pa_ab_criteria.sh [n_runs]
set -u
N=${1:-2}
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
EX="phone-number"
SRC="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice/${EX}"
PLAYBOOK="/opt/data/repos/prime-agent/scripts/pa-playbook/APPEND_SYSTEM_B.md"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
PA_METRICS="/opt/data/repos/prime-agent/scripts/pa_metrics.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-ab-criteria"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE"
SUMMARY="$BASE/summary.txt"

echo "== pa_ab_criteria $(date -u) ==" > "$SUMMARY"
echo "model: $MODEL | ex: $EX | arm: B (criteria tasks) | runs: $N" >> "$SUMMARY"

curl -s -m 120 -X POST http://192.168.68.58:8888/v1/load \
  -H "Authorization: Bearer $(cat /opt/data/.unsloth_api_key)" \
  -H "Content-Type: application/json" \
  -d '{"model_path":"LiquidAI/LFM2.5-2.6B-GGUF","gguf_variant":"Q4_K_M","force_cancel_active":true,"max_seq_length":131072,"n_parallel":2,"speculative_type":"none"}' > /tmp/pa-ab-load.json 2>&1

for i in $(seq 1 "$N"); do
  RD="${BASE}/run${i}-$(date -u +%H%M%S)"
  mkdir -p "$RD/${EX}"
  cp -r "$SRC"/. "$RD/${EX}/"
  cp "$PLAYBOOK" "$RD/${EX}/"
  PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE DELEGATE-TOOL PROTOCOL IN APPEND_SYSTEM_B.md — it is MANDATORY: delegate at least two subagents (a 'draft' child and a 'tester' child) using the delegate tool in a single message, then your turn ends automatically. You will be re-entered to integrate their results."
  echo "[run $i] starting $(date -u +%H:%M:%S)Z" | tee -a "$SUMMARY"
  python3 "$PA_DRIVER" --workdir "$RD/${EX}" --model "$MODEL" --prompt "$PROMPT" \
    --deadline 900 > "$RD/run.log" 2>&1
  cd "$RD/${EX}" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$RD/score.txt"
  echo "[run $i] done $(date -u +%H:%M:%S)Z | $(cat "$RD/score.txt")" | tee -a "$SUMMARY"
  echo "" >> "$SUMMARY"
  python3 "$PA_METRICS" "$RD/${EX}/rpc.jsonl" >> "$SUMMARY" 2>&1
  echo "" >> "$SUMMARY"
done

echo "== done. results in $BASE ==" | tee -a "$SUMMARY"