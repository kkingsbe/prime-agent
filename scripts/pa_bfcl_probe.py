#!/usr/bin/env python3
"""pa_bfcl_probe.py — BFCL-style dispatch micro-probe for LFM2.5 (TR-00).

Calls /v1/chat/completions with tools for each prompt in probes/bfcl_prompts.json,
classifies the model's tool-call emission per BFCL category:
  single / multiple / parallel / parallel-multiple / relevance-detection
Prints a result table; writes probes/bfcl_results_<ts>.csv.
Usage: pa_bfcl_probe.py [--limit N]
"""
import argparse
import csv
import json
import os
import time
import urllib.request
from pathlib import Path

KEY = Path("/opt/data/.unsloth_api_key").read_text().strip()
RIG = "http://192.168.68.58:8888/v1/chat/completions"
MODEL = "LiquidAI/LFM2.5-2.6B-GGUF"

TOOLS = [
    {"type": "function", "function": {"name": "get_weather",
        "description": "Get current weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "calculate",
        "description": "Evaluate a math expression.",
        "parameters": {"type": "object", "properties": {"expr": {"type": "string"}}, "required": ["expr"]}}},
    {"type": "function", "function": {"name": "search_files",
        "description": "Search files in a repo.",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}},
]


def probe(prompt: str) -> list:
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "tools": TOOLS, "tool_choice": "auto", "max_tokens": 256,
            "reasoning_effort": "low"}
    req = urllib.request.Request(RIG, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    calls = [c["function"]["name"] for c in msg.get("tool_calls", [])]
    return calls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    prompts = json.loads(Path(__file__).parent.joinpath("probes/bfcl_prompts.json").read_text())
    rows, errors = [], 0
    for i, p in enumerate(prompts):
        if args.limit and i >= args.limit:
            break
        try:
            calls = probe(p["user"])
            ok = sorted(calls) == sorted(p["expected"])
            rows.append((p["cat"], p["id"], ",".join(calls), ok, ""))
        except Exception as e:
            errors += 1
            rows.append((p["cat"], p["id"], "ERR", False, str(e)[:80]))
        time.sleep(0.5)
    out = Path(__file__).parent / f"probes/bfcl_results_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "id", "emitted", "correct", "note"])
        w.writerows(rows)
    bycat = {}
    for cat, _, _, ok, _ in rows:
        bycat.setdefault(cat, [0, 0])
        bycat[cat][0] += 1
        bycat[cat][1] += int(ok)
    print("=== BFCL micro-probe ===")
    for cat, (n, ok) in bycat.items():
        print(f"{cat:22s} {ok}/{n}")
    print(f"errors: {errors} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())