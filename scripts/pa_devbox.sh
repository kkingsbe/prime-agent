#!/usr/bin/env bash
# pa_devbox.sh — dev-task delegation A/B box: forth + grep, LFM2.5.
# Arms per exercise x2 runs each: DEL (PB_SHORT_v2 pinned, delegate tool) vs SOLO (no protocol).
# Scorer ALWAYS restores the pristine test file before pytest (test-mutation guard).
# Sequential legs. Deadlines: DEL 1200s, SOLO 900s.
set -u
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
POLY="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice"
PB="/opt/data/repos/prime-agent/scripts/pa-playbook/PB_SHORT_v2.md"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-devbox"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE"
echo "== pa_devbox $(date -u) | model=$MODEL | exercises: forth grep | arms: DEL x2 SOLO x2 =="

run_case() { # $1=tag $2=ex $3=del|solo $4=i
  local TAG="$1" EX="$2" ARM="$3" I="$4" SRC="$POLY/$EX"
  local RD="$BASE/$TAG" DL
  mkdir -p "$RD"
  cp -r "$SRC"/. "$RD/"
  local PROMPT
  if [ "$ARM" = "del" ]; then
    DL=1200
    cp "$PB" "$RD/PB_SHORT_v2.md"
    local PBABS="$RD/PB_SHORT_v2.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. READ AND FOLLOW THE PROTOCOL FILE AT ${PBABS} — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
  else
    DL=900
    rm -f "$RD/PB_SHORT_v2.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass."
  fi
  echo "[$TAG] $(date -u +%H:%M:%S)Z start | $EX $ARM#$I | deadline ${DL}s"
  python3 "$PA_DRIVER" --workdir "$RD" --model "$MODEL" --prompt "$PROMPT" --deadline "$DL" > "$RD/run.log" 2>&1
  # pristine test restore + score
  for tf in "$SRC"/*test*.py; do cp "$tf" "$RD/"; done
  cd "$RD" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$RD/score.txt"
  echo "[$TAG] done $(date -u +%H:%M:%S)Z | $(cat "$RD/score.txt") | rpc_B=$(stat -c%s "$RD/rpc.jsonl" 2>/dev/null)"
  python3 /opt/data/repos/prime-agent/scripts/pa_metrics.py "$RD/rpc.jsonl" 2>/dev/null | grep -E "spawns|child_terminal|child_aborted|child_natural_stop|bubble_up|clean_exit|root_tool_turns" | sed "s/^/[$TAG] /"
  echo ""
}

for EX in forth grep; do
  run_case "${EX}-del1" "$EX" del 1
  run_case "${EX}-del2" "$EX" del 2
  run_case "${EX}-solo1" "$EX" solo 1
  run_case "${EX}-solo2" "$EX" solo 2
done
echo "== done. results in $BASE =="