#!/usr/bin/env python3
"""pa_record.py — record a completed trial into the lab notebook + ledger.

Usage: pa_record.py <trial> <score> <key_metrics> <status>
Updates delegation-lab-notes.md: registry row + night-run log; updates BOX_LEDGER.json.
"""
import json
import re
import sys
import time
from pathlib import Path

trial, score, key_metrics, status = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
NOTES = Path("/opt/data/repos/unsloth-model-lab/docs/reports/delegation-lab-notes.md")
LEDGER = Path("/opt/data/repos/prime-agent/run-archive/BOX_LEDGER.json")

text = NOTES.read_text()
lines = text.splitlines()
out = []
for line in lines:
    m = re.match(rf"^\|\s*{re.escape(trial)}\s*\|", line)
    if m:
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        # | Trial | Phase | Leg | Exercise | Design/arm | Protocol | Components | Deadline | Status | Score | Key metrics |
        while len(cols) < 11:
            cols.append("")
        cols[8] = status      # Status
        cols[9] = score       # Score
        cols[10] = key_metrics
        line = "| " + " | ".join(cols) + " |"
    out.append(line)

stamp = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
block = f"\n### {stamp} — {trial} [{status}]\n- score: {score}\n- metrics: {key_metrics}\n"
out.append("\n## 10. Night-run log (auto)\n" if "## 10. Night-run log" not in text else "")
out.append(block)
NOTES.write_text("\n".join(out) + ("\n" if not out[-1].endswith("\n") else ""))

ledger = []
if LEDGER.exists():
    ledger = json.loads(LEDGER.read_text())
ledger.append({"trial": trial, "ts": stamp, "status": status, "score": score, "metrics": key_metrics})
LEDGER.write_text(json.dumps(ledger, indent=1))
print(f"[record] {trial} -> {status} | {score} | {key_metrics}")