#!/usr/bin/env bash
# pa_screen.sh — multi-module candidate screen (request R4.4): 3 SOLO legs in parallel.
# Context-stress probe: score + peak prompt tokens (reported from the trace later).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/run-archive/multiQ.log"
cd "$ROOT"
mkdir -p "$LOG"
for spec in dot-dsl go-counting react; do
  timeout 1700 bash scripts/pa_box2.sh --ex "$spec" --run SC1 --solo --deadline 1200 \
    >> "$LOG" 2>&1 &
done
wait
echo "=== SCREEN-DONE @ $(date -u +%H:%M:%SZ) ===" >> "$LOG"