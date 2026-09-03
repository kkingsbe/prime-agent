#!/usr/bin/env bash
# pa_rigctl.sh — rig control + post-load assert (Phase 0).
# Usage: pa_rigctl.sh status | load [model] | assert
#   load: force-loads LFM2.5 spec-off (champion config) unless model id given.
#   assert: prints model/spec/ctx; exits 1 if spec is not off (or model mismatch).
set -u
KEY=$(cat /opt/data/.unsloth_api_key)
RIG="${RIG:-http://192.168.68.58:8888}"
MODEL="${MODEL:-LiquidAI/LFM2.5-2.6B-GGUF}"
VARIANT="${VARIANT:-Q4_K_M}"

status() { curl -s -m 8 -H "Authorization: Bearer $KEY" "$RIG/api/inference/status"; }

case "${1:-status}" in
  status) status | python3 -c "import json,sys; d=json.load(sys.stdin); print('model:', d.get('active_model') or d.get('model_path'), '| spec:', d.get('speculative_type'), '| drafter:', d.get('spec_drafter_kind'), '| ctx:', d.get('context_length'), '| parallel:', d.get('parallel_slots') or d.get('n_parallel'))" ;;
  load)   curl -s -m 180 -X POST "$RIG/v1/load" -H "Authorization: Bearer $KEY" \
            -H "Content-Type: application/json" \
            -d "{\"model_path\":\"$MODEL\",\"gguf_variant\":\"$VARIANT\",\"force_cancel_active\":true,\"max_seq_length\":131072,\"n_parallel\":${PARALLEL:-4},\"speculative_type\":\"off\"}" >/dev/null && echo "load issued" ;;
  assert) status | python3 -c "
import json,sys,os
d=json.load(sys.stdin)
m=d.get('active_model') or d.get('model_path')
s=d.get('speculative_type')
p=d.get('parallel_slots') or d.get('n_parallel')
print('model:', m, '| spec:', s, '| ctx:', d.get('context_length'), '| parallel:', p)
ok = (s == 'off')
exp = os.environ.get('PARALLEL','4')
if str(p) != str(exp): print('ASSERT FAIL: parallel_slots', p, '!= expected', exp); sys.exit(1)
if not ok: print('ASSERT FAIL: speculative_type must be off (b10687); got:', s); sys.exit(1)
" ;;
  *) echo "usage: $0 [status|load|assert]"; exit 2 ;;
esac