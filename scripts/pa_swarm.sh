#!/usr/bin/env bash
# pa_swarm.sh — fire N polyglot exercises in parallel through prime-agent (JSON mode).
# Uses the rig model already loaded (n_parallel omitted on /v1/load => server runs concurrent decode slots).
# Scoring: .venv-bench python + pytest (same as aider_bench.sh).
# Usage: pa_swarm.sh <model-id> [pool] [exercise...]
set -u
MODEL="${1:-bartowski/Ling-3.0-tiny-GGUF}"
POOL="${2:-5}"
SRC=/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice
WORK=/tmp/pa-swarm
PA=/opt/data/repos/prime-agent/prime-agent.sh
PYTEST=/opt/data/repos/aider/.venv-bench/bin/python
export RIG_API_KEY="$(cat /opt/data/.unsloth_api_key)"
shift 2 || true
EXS=("$@")
[ ${#EXS[@]} -eq 0 ] && EXS=(grade-school list-ops phone-number simple-linked-list transpose)

rm -rf "$WORK"; mkdir -p "$WORK"
echo "SWARM start $(date -u +%H:%M:%S) model=$MODEL pool=$POOL exercises=${#EXS[@]}"

run_one() {
  local ex="$1"
  cp -r "$SRC/$ex" "$WORK/$ex"
  cd "$WORK/$ex" || return 1
  timeout 600 "$PA" --mode json --provider rig --model "$MODEL" \
    "Implement the $ex exercise per .docs/instructions.md. Make all tests pass — run the test file yourself to verify before finishing." \
    > run.jsonl 2> run.err
  echo "$?" > exit.code
  "$PYTEST" -m pytest -q 2>/dev/null | tail -1 > pytest.out || true
  echo "[$(date -u +%H:%M:%S)] $ex exit=$(cat exit.code) $(cat pytest.out)"
}

for ex in "${EXS[@]}"; do
  run_one "$ex" &
done
wait
echo "SWARM done $(date -u +%H:%M:%S)"