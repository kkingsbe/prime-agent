#!/usr/bin/env bash
# pa_lfm2_snapshots.sh — sample run state at 1/2/5/10 min marks into a log.
SNAP=/tmp/pa-lfm2/snapshots.log
TAIL=/tmp/pa-lfm2/run.log
RPC=/tmp/pa-lfm2/phone-number/rpc.jsonl
SCORE=/tmp/pa-lfm2/score.txt
KEY=$(cat /opt/data/.unsloth_api_key)

snap() {
  {
    echo "=== MARK: $1 (at $(date -u +%H:%M:%S)Z) ==="
    echo "-- run.log --"
    tail -6 "$TAIL" 2>/dev/null
    echo "-- events --"
    wc -l "$RPC" 2>/dev/null
    echo "-- score --"
    cat "$SCORE" 2>/dev/null || echo "(none yet)"
    echo "-- rig --"
    curl -s -m 10 http://192.168.68.58:8888/api/inference/monitor -H "Authorization: Bearer $KEY" 2>/dev/null \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print('reqs:', d.get('active_requests'))" 2>/dev/null
    echo
  } >> "$SNAP"
}

snap "1min"; sleep 60
snap "2min"; sleep 180
snap "5min"; sleep 300
snap "10min"
echo "DONE" >> "$SNAP"