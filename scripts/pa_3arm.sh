#!/usr/bin/env bash
# pa_3arm.sh — 3 prompt-strategy arms × N runs, LFM phone-number, delegate-tool stack.
#
# Arms (playbook in session context):
#   SHORT    — minimal imperative protocol (4 rules, no ornament)
#   ROLE     — identity-lock: "YOU ARE THE ORCHESTRATOR — NEVER IMPLEMENT"
#   EXAMPLE  — worked-example few-shot (copy this exact shape)
#
# Usage: pa_3arm.sh [runs_per_arm]
set -u
N=${1:-2}
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
EX="phone-number"
SRC="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice/${EX}"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
PA_METRICS="/opt/data/repos/prime-agent/scripts/pa_metrics.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-3arm"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE"
SUMMARY="$BASE/summary.txt"

echo "== pa_3arm $(date -u) ==" > "$SUMMARY"
echo "model: $MODEL | ex: $EX | arms: SHORT ROLE EXAMPLE | runs/arm: $N" >> "$SUMMARY"

curl -s -m 120 -X POST http://192.168.68.58:8888/v1/load \
  -H "Authorization: Bearer $(cat /opt/data/.unsloth_api_key)" \
  -H "Content-Type: application/json" \
  -d '{"model_path":"LiquidAI/LFM2.5-2.6B-GGUF","gguf_variant":"Q4_K_M","force_cancel_active":true,"max_seq_length":131072,"n_parallel":2,"speculative_type":"none"}' > /tmp/pa-3arm-load.json 2>&1

for ARM in SHORT ROLE EXAMPLE; do
  PLAYBOOK="/opt/data/repos/prime-agent/scripts/pa-playbook/PB_${ARM}.md"
  for i in $(seq 1 "$N"); do
    RD="${BASE}/${ARM}-run${i}-$(date -u +%H%M%S)"
    mkdir -p "$RD/${EX}"
    cp -r "$SRC"/. "$RD/${EX}/"
    cp "$PLAYBOOK" "$RD/${EX}/"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE PROTOCOL IN PB_${ARM}.md — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
    echo "[$ARM/$i] starting $(date -u +%H:%M:%S)Z" | tee -a "$SUMMARY"
    python3 "$PA_DRIVER" --workdir "$RD/${EX}" --model "$MODEL" --prompt "$PROMPT" \
      --deadline 900 > "$RD/run.log" 2>&1
    cd "$RD/${EX}" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$RD/score.txt"
    SCORE=$(cat "$RD/score.txt")
    echo "[$ARM/$i] done $(date -u +%H:%M:%S)Z | $SCORE" | tee -a "$SUMMARY"
    echo "" >> "$SUMMARY"
    python3 "$PA_METRICS" "$RD/${EX}/rpc.jsonl" 2>&1 | grep -E "spawns|child_terminal|child_natural|child_aborted|root_tool|bubble_up|clean_exit|victory" >> "$SUMMARY"
    echo "" >> "$SUMMARY"
  done
done

echo "== done. results in $BASE ==" | tee -a "$SUMMARY"