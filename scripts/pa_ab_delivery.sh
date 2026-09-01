#!/usr/bin/env bash
# pa_ab_delivery.sh — delivery-channel A/B for the PB_SHORT delegation protocol.
# Arm A: PB_SHORT.md as a workdir FILE referenced from the task prompt (yesterday's method).
# Arm B: PB_SHORT.md VERBATIM as .prime/agent/APPEND_SYSTEM.md (native system-prompt append, root+children).
# Same model (LFM2.5), exercise (phone-number), task wording; protocol text identical. Legs sequential.
set -u
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
EX="phone-number"
SRC="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice/${EX}"
PB="/opt/data/repos/prime-agent/scripts/pa-playbook/PB_SHORT.md"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-ab-delivery"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE"

run_arm() { # $1 = arm tag, $2 = file|append
  local ARM="$1" MODE="$2" RD="${BASE}/${1}"
  mkdir -p "$RD/${EX}"
  cp -r "$SRC"/. "$RD/${EX}/"
  local PROMPT
  if [ "$MODE" = "file" ]; then
    cp "$PB" "$RD/${EX}/PB_SHORT.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE PROTOCOL IN PB_SHORT.md — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
  else
    mkdir -p "$RD/${EX}/.prime/agent"
    cp "$PB" "$RD/${EX}/.prime/agent/APPEND_SYSTEM.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE PROTOCOL IN YOUR SYSTEM PROMPT — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
  fi
  echo "[${ARM}] $(date -u +%H:%M:%S)Z start"
  python3 "$PA_DRIVER" --workdir "$RD/${EX}" --model "$MODEL" --prompt "$PROMPT" --deadline 600 > "$RD/run.log" 2>&1
  cd "$RD/${EX}" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$RD/score.txt"
  echo "[${ARM}] done $(date -u +%H:%M:%S)Z | $(cat "$RD/score.txt")"
  python3 /opt/data/repos/prime-agent/scripts/pa_metrics.py "$RD/${EX}/rpc.jsonl" 2>/dev/null | grep -E "spawns|child_terminal|child_natural |child_aborted|root_tool|bubble_up|clean_exit" | sed "s/^/[${ARM}] /"
  echo ""
}

run_arm armA2 file
run_arm armB2 append
echo "== done. results in $BASE =="