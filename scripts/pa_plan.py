#!/usr/bin/env python3
"""pa_plan.py — PLAN.md parser for design A (PLAN-LIST) fan-out.

Parses the model-written plan artifact from `<workdir>/PLAN.md` into an ordered
task list with dependencies. Schema (loose, tolerant of prose around it):

    ##T1: <description> | dep: none
    ##T2: <description> | dep: T1
    ##T3: <description> | dep: T1,T2

Returns JSON: {"tasks":[{"id":"T1","desc":"...","deps":[]},...], "error":null}
Exits 2 on unparseable/unusable plan (fewer than 3 tasks), exit 1 on missing file.
"""
import json
import re
import sys
from pathlib import Path

TASK_RE = re.compile(r"^##\s*(T\d+)\s*[:.\-]?\s*(.*)$", re.I)


def parse_plan(text: str) -> dict:
    tasks, by_id = [], {}
    order = []
    for line in text.splitlines():
        m = TASK_RE.match(line.strip())
        if not m:
            continue
        tid = m.group(1).upper()
        rest = m.group(2).strip()
        # split optional "| dep: ..." tail
        desc, deps = rest, []
        if "|" in rest:
            desc, _, deptail = rest.partition("|")
            for d in re.findall(r"T\d+", deptail, re.I):
                deps.append(d.upper())
        if not desc or desc.lower() in ("none", "n/a", "-", "--"):
            desc = f"(no description for {tid})"
        if tid in by_id:
            continue  # duplicate id: first wins
        by_id[tid] = {"id": tid, "desc": desc.strip(), "deps": deps}
        order.append(tid)
    tasks = [by_id[t] for t in order]
    # validity checks
    for t in tasks:
        for d in t["deps"]:
            if d not in by_id:
                return {"tasks": tasks, "error": f"task {t['id']} depends on unknown {d}"}
            if d == t["id"]:
                return {"tasks": tasks, "error": f"task {t['id']} depends on itself"}
    if len(tasks) < 3:
        return {"tasks": tasks, "error": f"plan has {len(tasks)} tasks, need >=3"}
    return {"tasks": tasks, "error": None}


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "PLAN.md")
    if not path.exists():
        print(json.dumps({"tasks": [], "error": f"{path} missing"}))
        return 1
    result = parse_plan(path.read_text())
    print(json.dumps(result, indent=1))
    return 2 if result["error"] else 0


if __name__ == "__main__":
    sys.exit(main())