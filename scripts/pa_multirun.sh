#!/usr/bin/env bash
# pa_multirun.sh — chained multi-box runner for the reviewer protocol (Q1/Q2/Q3).
# Usage: pa_multirun.sh <spec1.txt> <spec2.txt> ...
# Each spec file: one leg per line:  <exercise>|<runlabel>|<box2 flags...>
# Example:  pig-latin|S1|--solo
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/run-archive/multiQ.log"
mkdir -p "$ROOT/run-archive"
echo "== multirun @ $(date -u +%H:%M:%SZ) ==" >> "$LOG"
for spec in "$@"; do
  while IFS='|' read -r EX RUN FLAGS || [ -n "$EX" ]; do
    [ -z "$EX" ] && continue
    echo "=== $EX [$RUN] @ $(date -u +%H:%M:%SZ) ===" >> "$LOG"
    timeout 2300 bash "$ROOT/scripts/pa_box2.sh" --ex "$EX" --run "$RUN" $FLAGS >> "$LOG" 2>&1 \
      || echo "rc=$? ($EX)" >> "$LOG"
    echo "=== $EX [$RUN] done @ $(date -u +%H:%M:%SZ) ===" >> "$LOG"
  done < "$spec"
done
echo "== MULTIRUN-COMPLETE @ $(date -u +%H:%M:%SZ) ==" >> "$LOG"