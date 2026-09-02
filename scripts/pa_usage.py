#!/usr/bin/env python3
"""pa_usage.py — per-leg token usage from the rig monitor (per-request entries).
Usage: pa_usage.py <start_epoch> <end_epoch> [limit]
Prints max prompt_tokens, max context_usage (per-slot pressure), request count.
"""
import json, sys, time, urllib.request

KEY = open("/opt/data/.unsloth_api_key").read().strip()
MON = "http://192.168.68.58:8888/api/inference/monitor"

start, end = float(sys.argv[1]), float(sys.argv[2])
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 500

req = urllib.request.Request(MON, headers={"Authorization": f"Bearer {KEY}"})
entries = json.load(urllib.request.urlopen(req, timeout=10)).get("entries", [])[:lim]
rows = [e for e in entries
        if (e.get("started_at") or 0) >= start and (e.get("started_at") or 0) <= end]
pk = max((e.get("prompt_tokens") or 0) for e in rows) if rows else 0
ck = max((e.get("completion_tokens") or 0) for e in rows) if rows else 0
cu = max((e.get("context_usage") or 0) for e in rows) if rows else 0
with_tokens = sum(1 for e in rows if e.get("prompt_tokens"))
print(f"requests={len(rows)} with_tokens={with_tokens} peak_prompt={pk} peak_completion={ck} peak_context_usage={cu}")