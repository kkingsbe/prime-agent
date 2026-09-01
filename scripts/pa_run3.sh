#!/usr/bin/env bash
# pa_run3.sh — champion-arm rerun with PB_SHORT_v2 (integration-effectiveness lever).
# Pinned absolute path to the playbook, fixed driver (child-done re-entry + delta filter),
# 900s deadline, LFM2.5 phone-number. Verify delegate->children->integrate->passes.
set -u
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
EX="phone-number"
SRC="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice/${EX}"
PB="/opt/data/repos/prime-agent/scripts/pa-playbook/PB_SHORT_v2.md"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-run3"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE/${EX}"
cp -r "$SRC"/. "$BASE/${EX}/"
cp "$PB" "$BASE/${EX}/PB_SHORT_v2.md"
PBABS="${BASE}/${EX}/PB_SHORT_v2.md"
PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. READ AND FOLLOW THE PROTOCOL FILE AT ${PBABS} — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
echo "[run3] $(date -u +%H:%M:%S)Z start | PB v2 | deadline 900s"
python3 "$PA_DRIVER" --workdir "$BASE/${EX}" --model "$MODEL" --prompt "$PROMPT" --deadline 900 > "$BASE/run.log" 2>&1
cd "$BASE/${EX}" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$BASE/score.txt"
echo "[run3] done $(date -u +%H:%M:%S)Z | $(cat "$BASE/score.txt")"
python3 /opt/data/repos/prime-agent/scripts/pa_metrics.py "$BASE/${EX}/rpc.jsonl" 2>/dev/null | grep -E "spawns|child_terminal|child_aborted|bubble_up|clean_exit|root_tool_turns|child_natural" | sed "s/^/[run3] /"
echo "== done. results in $BASE =="