#!/usr/bin/env bash
# pa_night_runner.sh — hourly cron child: run the next delegation trial, record it,
# commit the lab notes. Historically safe when called every hour until 08:00 ET.
set -uo pipefail
ROOT=/opt/data/repos/prime-agent
LAB=/opt/data/repos/unsloth-model-lab
ARCH="$ROOT/run-archive"; mkdir -p "$ARCH"
PROG="$ARCH/BOX_PROGRESS.json"
NOTES="$LAB/docs/reports/delegation-lab-notes.md"
ORDER='["TR-00","TR-01","TR-02","TR-03","TR-04"]'

UTC_HM=$(date -u +%H%M)
echo "== pa_night_runner $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

# 0. 08:00 ET (=12:00 UTC) stop guard: final wrap-up only
if [ "$UTC_HM" -ge 1200 ]; then
  echo "[night] 8am ET reached — trials complete. Final ledger:"
  python3 -c "import json; d=json.load(open('$ARCH/BOX_LEDGER.json')) if __import__('os').path.exists('$ARCH/BOX_LEDGER.json') else []; [print(' ', r['trial'], r['status'], r['score']) for r in d]" 2>/dev/null || echo "  (no ledger)"
  exit 0
fi

# 1. in-progress guard — never overlap runs
if pgrep -f "pa_rpc.py|pa_box2.sh" >/dev/null 2>&1; then
  cur=$(ls -t "$ARCH" 2>/dev/null | head -1)
  echo "[night] trial in progress ($cur) — skipping this tick"; exit 0
fi

# 2. progress init + pick next trial (pending/failed = actionable)
if [ ! -f "$PROG" ]; then
  python3 - "$PROG" <<'EOF'
import json, sys
prog = {"trials": {t: {"status": "pending", "attempts": 0}
                   for t in ["TR-00", "TR-01", "TR-02", "TR-03", "TR-04"]}}
json.dump(prog, open(sys.argv[1], "w"), indent=1)
EOF
fi
NEXT=$(python3 - "$PROG" <<'EOF'
import json, sys
prog = json.load(open(sys.argv[1]))
for t, st in prog.get("trials", {}).items():
    if st.get("status") in ("pending", "failed"):
        print(t); break
EOF
)
if [ -z "$NEXT" ]; then
  echo "[night] all trials done — idle until stop guard."
  exit 0
fi
echo "[night] next trial: $NEXT"

# 3. rig preflight (assert; reload once on failure; assert again)
if ! bash "$ROOT/scripts/pa_rigctl.sh" assert >/dev/null 2>&1; then
  echo "[night] spec assert failed — reloading with spec-off"
  bash "$ROOT/scripts/pa_rigctl.sh" load >/dev/null 2>&1; sleep 8
  bash "$ROOT/scripts/pa_rigctl.sh" assert >/dev/null 2>&1 || { echo "[night] ASSERT FAIL after reload — aborting tick"; exit 3; }
fi
echo "[night] rig ok (spec off)"

# 4. execute the trial
RC=1; SCORE=""; METRICS=""; STATUS="FAILED"
case "$NEXT" in
  TR-00)
    timeout 900 python3 "$ROOT/scripts/pa_bfcl_probe.py" > "$ARCH/TR-00-probe.txt" 2>&1
    RC=$?
    if [ $RC -eq 0 ]; then
      SCORE=$(grep -E "parallel-multiple|single|multiple|parallel|relevance" "$ARCH/TR-00-probe.txt" | tail -5 | tr '\n' '; ')
      METRICS="probe -> $ARCH/TR-00-probe.txt"
      STATUS="done"
    fi ;;
  TR-01) timeout 1500 bash "$ROOT/scripts/pa_box2.sh" --ex grep --run A1 --design A  --deadline 1200 --components 1,2,7,8,12 > "$ARCH/TR-01.log" 2>&1;    RC=$? ;;
  TR-02) timeout 1500 bash "$ROOT/scripts/pa_box2.sh" --ex grep --run A2 --design A  --deadline 1200 --components 1,2,7,8,12 > "$ARCH/TR-02.log" 2>&1;    RC=$? ;;
  TR-03) timeout 1500 bash "$ROOT/scripts/pa_box2.sh" --ex grep --run ctrl1 --design ctrl --deadline 1200 > "$ARCH/TR-03.log" 2>&1;                     RC=$? ;;
  TR-04) timeout 1500 bash "$ROOT/scripts/pa_box2.sh" --ex grep --run ctrl2 --design ctrl --deadline 1200 > "$ARCH/TR-04.log" 2>&1;                     RC=$? ;;
esac

if [ "$NEXT" != "TR-00" ]; then
  DST=$(ls -dt "$ARCH"/*-"${NEXT#TR-}" 2>/dev/null | head -1)
  [ -z "$DST" ] && DST=$(find "$ARCH" -mindepth 1 -maxdepth 1 -type d -name "*-*" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  if [ -d "$DST" ]; then
    SCORE=$(head -1 "$DST/score.txt" 2>/dev/null)
    METRICS=$(grep -E "delegates|spawns|child_terminal|child_aborted|clean_exit|error_flags|plan_tasks" "$DST/metrics.txt" 2>/dev/null | tr '\n' '; ')
    [ "$RC" -eq 0 ] && STATUS="done"
    [ "$RC" -eq 124 ] && STATUS="TIMEOUT"
  else
    SCORE="no archive"; METRICS="rc=$RC"
  fi
fi

# 5. record + commit
python3 "$ROOT/scripts/pa_record.py" "$NEXT" "$SCORE" "$METRICS" "$STATUS"
python3 - "$PROG" "$NEXT" "$STATUS" <<'EOF'
import json, sys
p, t, st = sys.argv[1], sys.argv[2], sys.argv[3]
prog = json.load(open(p))
entry = prog.setdefault("trials", {}).setdefault(t, {"status": "pending", "attempts": 0})
entry["attempts"] = entry.get("attempts", 0) + 1
if st == "done":
    entry["status"] = "done"
elif st in ("FAILED", "TIMEOUT"):
    entry["status"] = "failed"   # actionable: diagnose, fix, retry
json.dump(prog, open(p, "w"), indent=1)
EOF
cd "$LAB" && git add docs/reports/delegation-lab-notes.md && git commit -q -m "lab notes: record $NEXT ($STATUS)" && git push -q origin master 2>/dev/null
echo "[night] $NEXT -> $STATUS | $SCORE"
echo "[night] metrics: $METRICS"
exit 0