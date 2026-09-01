#!/usr/bin/env bash
# pa_lever2.sh — marker probe + pinned-path retest A/B (2026-08-31 follow-up).
# 1. Marker probe: secret token in APPEND_SYSTEM.md; model asked to echo it (JSON mode).
# 2. armA3: PB_SHORT.md file + ABSOLUTE PATH pinned in task prompt (900s; expect delegation).
# 3. armB3: PB_SHORT verbatim via APPEND_SYSTEM.md (600s); verdict gated on probe result.
set -u
MODEL="LiquidAI/LFM2.5-2.6B-GGUF"
EX="phone-number"
SRC="/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice/${EX}"
PB="/opt/data/repos/prime-agent/scripts/pa-playbook/PB_SHORT.md"
PA_DRIVER="/opt/data/repos/prime-agent/scripts/pa_rpc.py"
VENV_PY="/opt/data/repos/aider/.venv-bench/bin/python"
OUT="/tmp/pa-lever2"
TS=$(date -u +%Y%m%d-%H%M%S)
BASE="${OUT}/${TS}"
mkdir -p "$BASE"
MKR="MKR-$(date -u +%H%M%S)-$$"

# --- 1. marker probe ---
PR="$BASE/probe"
mkdir -p "$PR/.prime/agent"
printf '# Delivery marker probe\nMARKER TEXT: %s\nIf the user asks for the marker token, reply with exactly: %s\n' "$MKR" "$MKR" > "$PR/.prime/agent/APPEND_SYSTEM.md"
echo "[probe] marker=$MKR start $(date -u +%H:%M:%S)Z"
(cd "$PR" && /opt/data/repos/prime-agent/prime-agent.sh --mode json --provider rig --model "$MODEL" "Report the marker token from your system prompt verbatim, and nothing else." > probe.jsonl 2> probe.err)
echo "[probe] exit=$? out_bytes=$(wc -c < "$PR/probe.jsonl" 2>/dev/null)"
if grep -q "$MKR" "$PR/probe.jsonl" 2>/dev/null; then
  echo "[probe] VERDICT: append delivery WORKS (marker echoed)"
else
  echo "[probe] VERDICT: append delivery INVISIBLE (marker absent)"
fi

run_arm() { # $1 tag, $2 file|append, $3 deadline
  local ARM="$1" MODE="$2" DL="$3" RD="${BASE}/${1}"
  mkdir -p "$RD/${EX}"
  cp -r "$SRC"/. "$RD/${EX}/"
  local PROMPT
  if [ "$MODE" = "file" ]; then
    cp "$PB" "$RD/${EX}/PB_SHORT.md"
    local PBABS="${RD}/${EX}/PB_SHORT.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. READ AND FOLLOW THE PROTOCOL FILE AT ${PBABS} — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
  else
    mkdir -p "$RD/${EX}/.prime/agent"
    cp "$PB" "$RD/${EX}/.prime/agent/APPEND_SYSTEM.md"
    PROMPT="Work on the '${EX}' exercise in this directory: read .docs/instructions.md and the test file, implement the solution in the exercise files, and make the tests pass. FOLLOW THE PROTOCOL IN YOUR SYSTEM PROMPT — it is MANDATORY. Delegate at least two subagents (draft + tester) with the delegate tool in a single message; your turn ends automatically. You will be re-entered to integrate."
  fi
  echo "[${ARM}] start $(date -u +%H:%M:%S)Z (deadline ${DL}s)"
  python3 "$PA_DRIVER" --workdir "$RD/${EX}" --model "$MODEL" --prompt "$PROMPT" --deadline "$DL" > "$RD/run.log" 2>&1
  cd "$RD/${EX}" && "$VENV_PY" -m pytest -q 2>&1 | tail -1 > "$RD/score.txt"
  echo "[${ARM}] done $(date -u +%H:%M:%S)Z | $(cat "$RD/score.txt") | rpc_B=$(stat -c%s "$RD/${EX}/rpc.jsonl" 2>/dev/null)"
  python3 /opt/data/repos/prime-agent/scripts/pa_metrics.py "$RD/${EX}/rpc.jsonl" 2>/dev/null | grep -E "spawns|child_terminal|child_aborted|bubble_up|clean_exit|root_tool_turns" | sed "s/^/[${ARM}] /"
}

run_arm armA3 file 900
run_arm armB3 append 600
echo "== done. results in $BASE =="