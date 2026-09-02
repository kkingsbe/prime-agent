#!/usr/bin/env bash
# pa_box2.sh — trial runner for the delegation A/B box (Phases 1-3, grep).
# Usage:
#   pa_box2.sh --ex grep --run A1 --design A --deadline 1200 [--components 1,2,7,8,12] [--solo]
# Guarantees: spec-off assert, pristine test scoring, last-importable-state snapshot,
# metrics v2 digest, archive to run-archive/.
set -uo pipefail
exec 9>&- 2>/dev/null   # child: release the night-runner's flock fd (no inheritance)
cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)
POLY=/opt/data/repos/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice
SCORER=/opt/data/repos/aider/.venv-bench/bin/python
ARCHIVE="$ROOT/run-archive"
mkdir -p "$ARCHIVE" /tmp/pa-box2

EX=""; RUN=""; DESIGN="ctrl"; DEADLINE=1200; COMPS=""; SOLO=0; CONTRACT=0; EVAL=0; LOOP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ex) EX="$2"; shift 2;; --run) RUN="$2"; shift 2;; --design) DESIGN="$2"; shift 2;;
    --deadline) DEADLINE="$2"; shift 2;; --components) COMPS="$2"; shift 2;;
    --solo) SOLO=1; shift;; --contract) CONTRACT=1; shift;; --eval) EVAL=1; shift;;
    --loop) LOOP="$2"; shift 2;;
    *) echo "unknown: $1"; exit 2;;
  esac
done
: "${EX:?--ex required}" ; : "${RUN:?--run required}"
SRC="$POLY/$EX"; [ -d "$SRC" ] || { echo "no exercise $SRC"; exit 1; }
SLUG=$(echo "$EX" | tr - _)   # dir name -> module file slug (phone-number -> phone_number)

# 0. rig assert (fail fast)
bash "$ROOT/scripts/pa_rigctl.sh" assert || { echo "[box2] RIG ASSERT FAILED — aborting"; exit 3; }
echo "[box2] $RUN | ex=$EX design=$DESIGN deadline=${DEADLINE}s comps=[$COMPS] solo=$SOLO | $(date -u +%H:%M:%SZ)"

# 1. workdir from PRISTINE source
TS=$(date +%Y%m%d-%H%M%S); WD="/tmp/pa-box2/$TS-$RUN"; mkdir -p "$WD"
cp -r "$SRC"/. "$WD/"
[ -f "$SRC/forth.py" ] && cp "$SRC/forth.py" "$WD/forth.py"
SOLFILE="$WD/$SLUG.py"
cp "$SOLFILE" "$WD/snap-000-start.py"

# 2. protocol + prompt per design (solo arm: no protocol at all)
PB=""; PROMPT=""
if [ "$SOLO" -eq 1 ]; then
  PB="$ROOT/scripts/pa-playbook/PB_SOLO.md"
  PROMPT="Work on the '$EX' exercise in this directory. READ AND FOLLOW THE PROTOCOL FILE AT $WD/PB_SOLO.md — MANDATORY. Implement $SLUG.py yourself (delegation DISABLED — never use the delegate tool) and make the tests pass."
else
  case "$DESIGN" in
  ctrl)
    PB="$ROOT/scripts/pa-playbook/PB_SHORT_v2.md"
    PROMPT="Work on the '$EX' exercise in this directory. READ AND FOLLOW THE PROTOCOL FILE AT $WD/PB_SHORT_v2.md — MANDATORY. Improve the solution and make the tests pass." ;;
  A)
    PB="$ROOT/scripts/pa-playbook/PB_v3_A.md"
    PROMPT="Work on the '$EX' exercise in this directory. READ AND FOLLOW THE PROTOCOL FILE AT $WD/PB_v3_A.md — MANDATORY. FIRST write PLAN.md (>=3 numbered tasks: ##T1: desc | dep: none). THEN delegate one child per task. Your turn ends after delegating; you will be re-entered to integrate." ;;
  B|D)
    PB="$ROOT/scripts/pa-playbook/PB_v3_$DESIGN.md"
    PROMPT="Work on the '$EX' exercise in this directory. READ AND FOLLOW THE PROTOCOL FILE AT $WD/PB_v3_$DESIGN.md — MANDATORY. Make the tests pass." ;;
  *) echo "unknown design $DESIGN"; exit 2 ;;
  esac
fi
[ -f "$PB" ] && cp "$PB" "$WD/" || { echo "[box2] protocol missing: $PB"; exit 1; }
# inject the real workdir path into the protocol's ABS_WORKDIR placeholder so the
# root's child-task suffix carries a concrete absolute path (children run in their
# own session dirs; only an absolute path reaches the scored box file)
if grep -q '<ABS_WORKDIR>\|<SLUG>' "$WD"/*.md 2>/dev/null; then
  sed -i -e "s|<ABS_WORKDIR>|$WD|g" -e "s|<SLUG>|$SLUG|g" "$WD"/*.md
fi

# Q2: driver-side contract extraction (deterministic, ast-based) -> CONTRACT.md + prompt ref
if [ "$CONTRACT" -eq 1 ]; then
  if python3 "$ROOT/scripts/pa_contract.py" "$SRC/${SLUG}_test.py" "$SLUG" > "$WD/CONTRACT.md" 2>/dev/null; then
    PROMPT="$PROMPT
IMPORTANT: read '$WD/CONTRACT.md' BEFORE planning — it lists the EXACT imports and call shapes the tests use. Implement against it."
  else
    echo "[box2] contract extraction failed — continuing without CONTRACT.md"
  fi
fi
# Q3: driver-side evaluator — pytest output injected at integration re-entry
[ "$EVAL" -eq 1 ] && export PA_EVAL_TEST="$SRC/${SLUG}_test.py"

# 3. follow-up components -> PA_FOLLOWUP_EXTRA
EXTRA=""
add() { EXTRA="${EXTRA}${EXTRA:+$'\n\n'}$1"; }
if [ "$SOLO" -eq 0 ]; then
  add "Run tests IN-KERNEL (import pytest; pytest.main([...])). NEVER via subprocess. Do NOT inspect subagent session directories."
  case ",$COMPS," in
    *,1,*) add "First write ONE LINE: what failed and why. Then fix it." ;;
  esac
  case ",$COMPS," in
    *,2,*) add "PLAN reminder: finish remaining tasks now — do NOT re-delegate work already delegated." ;;
  esac
  case ",$COMPS," in
    *,12,*) add "PATCH the draft's files in place; do NOT rewrite from scratch." ;;
  esac
  add "FINALIZE when the remaining failures are understood: leave the last file state importable and END your turn with a one-line summary. Re-check REFLECTIONS.md before deciding what to try next."
fi
export PA_FOLLOWUP_EXTRA="$EXTRA"

# 4. run (foreground; deadline+buffer) with periodic solution-file snapshots
echo "[box2] following entries -> $WD/run.log"
cd "$ROOT" && timeout $((DEADLINE + 90)) python3 scripts/pa_rpc.py \
  --workdir "$WD" --model LiquidAI/LFM2.5-2.6B-GGUF --prompt "$PROMPT" \
  --deadline "$DEADLINE" --loop "$LOOP" > "$WD/run.log" 2>&1 &
RPC_PID=$!
( while kill -0 "$RPC_PID" 2>/dev/null; do
    cp "$SOLFILE" "$WD/snap-$(date +%s).py" 2>/dev/null
    cp "$WD/PLAN.md" "$WD/snap-$(date +%s)-plan.md" 2>/dev/null
    sleep 30
  done ) &
SNAP_PID=$!
wait "$RPC_PID"; RC=$?
kill "$SNAP_PID" 2>/dev/null
cp "$SOLFILE" "$WD/snap-$(date +%s)-final.py" 2>/dev/null
grep --line-buffered -E "\[rpc\]" "$WD/run.log" | tail -25
echo "[box2] rpc exit=$RC"

# 5. snapshot walk + score (last importable state, pristine tests)
cp "$SRC/${SLUG}_test.py" "$WD/${SLUG}_test.py"   # pristine restore
last_good=""
for f in $(ls -t "$WD"/snap-*.py 2>/dev/null); do
  # test the SNAPSHOT FILE itself (ast.parse), not the live workdir file
  if $SCORER -c "import ast; ast.parse(open(r'$f').read())" 2>/dev/null; then
    last_good="$f"; break
  fi
done
if [ -n "$last_good" ] && [ "$last_good" != "$SOLFILE" ]; then
  cp "$last_good" "$SOLFILE" && echo "[box2] scored last-importable state: $(basename "$last_good")"
else
  echo "[box2] no parseable snapshot (${last_good:-none}); scoring final file state"
fi
( cd "$WD" && $SCORER -m pytest "${SLUG}_test.py" -q 2>&1 | tail -3 ) | tee "$WD/score.txt"

# 6. metrics v2
python3 scripts/pa_metrics.py "$WD/rpc.jsonl" 2>/dev/null | tee "$WD/metrics.txt" | grep -E "delegates|spawns|child_|clean_exit|error_flags|score|plan_tasks"

# 7. archive
DST="$ARCHIVE/$TS-$RUN"; mv "$WD" "$DST"
echo "[box2] DONE -> $DST | score: $(head -1 "$DST/score.txt")"