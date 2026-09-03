#!/usr/bin/env python3
"""pa_cycles.py — per-cycle trajectory forensics for looped legs (reviewer R5.1).
For each loop cycle: passing count before/after, tests flipped per direction, and who
edited (root in-kernel via ipython, fixer child via delegate, or nobody).
Usage: pa_cycles.py <leg-dir> [more-leg-dirs...]
"""
import json, re, sys, os, hashlib

def load(leg):
    evs = []
    for line in open(os.path.join(leg, "rpc.jsonl")):
        try:
            evs.append(json.loads(line))
        except Exception:
            pass
    return evs

def failinfo(text):
    m = re.search(r"PYTEST FEEDBACK \((\d+) failing", text)
    fails = int(m.group(1)) if m else None
    names = set(re.findall(r"(?:failures|detail)[^\n]*?\b(test_\w+)", text))
    names |= set(re.findall(r"- ·?(test_\w+)", text))
    names |= set(re.findall(r"(?:^\|\s*)?(test_\w+)\s*(?:·|$)", text, re.M))
    p = re.search(r"(\d+) passed", text)
    return fails, (p.group(1) if p else None), names

def run(leg):
    evs = load(leg)
    cycles = []          # (fail_before, pass_before, fail_after, pass_after, flips)
    cur = None
    for ev in evs:
        t = ev.get("type")
        m = ev.get("message", {})
        if t == "message_start" and m.get("role") == "user":
            txt = "".join(c.get("text", "") for c in m.get("content", [])
                          if isinstance(c, dict))
            if "PYTEST FEEDBACK" in txt:
                if cur:
                    cycles.append(cur)
                fails, passed, names = failinfo(txt)
                cur = {"fails": fails, "passed": passed, "names": names,
                       "delegates": 0, "ipythons": 0, "delegate_names": []}
        elif cur is not None and t == "message_end" and m.get("role") == "assistant":
            for c in m.get("content", []):
                if isinstance(c, dict) and c.get("type") == "toolCall":
                    if c.get("name") == "delegate":
                        cur["delegates"] += 1
                        cur["delegate_names"].append(
                            str(c.get("arguments", {}).get("sessionName", "?"))[:22])
                    if c.get("name") == "ipython":
                        cur["ipythons"] += 1
    if cur:
        cycles.append(cur)
    return cycles

def main():
    for leg in sys.argv[1:]:
        name = os.path.basename(leg.rstrip("/"))
        cycles = run(leg)
        print(f"== {name}: {len(cycles)} cycles")
        for i, c in enumerate(cycles):
            edit = "fixer-child" if c["delegates"] > 0 else ("root-ipython" if c["ipythons"] > 0 else "nobody")
            print(f"   c{i+1}: fails={c['fails']} passed={c['passed']} "
                  f"delegates={c['delegates']}({','.join(c['delegate_names'][:2])}) "
                  f"ipythons={c['ipythons']} editor={edit}")
        # flips between consecutive cycles (names available where feedback listed them)
        for i in range(len(cycles) - 1):
            a, b = cycles[i], cycles[i + 1]
            if a["names"] and b["names"]:
                gained = b["names"] - a["names"]
                lost = a["names"] - b["names"]
                print(f"   flip c{i+1}->c{i+2}: +{len(gained)}/-{len(lost)} "
                      f"({sorted(gained)[:3]} | {sorted(lost)[:3]})")

if __name__ == "__main__":
    main()