#!/usr/bin/env python3
"""Forensic scan of the last three delegation runs — identify all issues."""
import json, os, re, sys, ast

ARCH = "/opt/data/repos/prime-agent/run-archive"
TRIALS = ["20260901-132236-A2", "20260901-134523-ctrl1", "20260901-140533-ctrl2"]

def child_sessions(rpc_path):
    dirs = {}
    if not os.path.exists(rpc_path): return dirs
    for line in open(rpc_path):
        try: ev = json.loads(line)
        except: continue
        if ev.get("type") != "rlm_child_update": continue
        c = ev.get("child", {})
        nm, sd = c.get("sessionName"), c.get("sessionDir")
        if nm and sd: dirs.setdefault(nm, sd)
    return dirs

def scan_child(sd):
    info = {"turns":0, "tools":[], "writes":[], "stops":[], "overflows":0, "ipython":0}
    if not sd or not os.path.isdir(sd): return info
    for f in os.listdir(sd):
        if not f.endswith(".jsonl"): continue
        for line in open(os.path.join(sd, f)):
            try: ev = json.loads(line)
            except: continue
            if ev.get("type") not in ("message","message_end"): continue
            m = ev.get("message", {})
            if m.get("role") != "assistant": continue
            info["turns"] += 1
            if m.get("stopReason"): info["stops"].append(m.get("stopReason"))
            if "Context size has been exceeded" in json.dumps(m): info["overflows"] += 1
            for c in m.get("content", []):
                if not isinstance(c, dict): continue
                if c.get("type") == "toolCall" and c.get("name") == "ipython":
                    info["ipython"] += 1
                    code = c.get("arguments", {}).get("code", "") or ""
                    for mm in re.finditer(r'open\("([^"]+)"\s*,\s*[wbr]', code):
                        info["writes"].append(os.path.basename(mm.group(1)))
    return info

def root_delegates(rpc_path):
    dl = []
    if not os.path.exists(rpc_path): return dl
    for line in open(rpc_path):
        try: ev = json.loads(line)
        except: continue
        if ev.get("type") != "message_end": continue
        m = ev.get("message", {})
        if m.get("role") != "assistant": continue
        for c in m.get("content", []):
            if isinstance(c, dict) and c.get("type") == "toolCall" and c.get("name") == "delegate":
                a = c.get("arguments", {})
                dl.append((a.get("name","?")[:32], (a.get("task","") or "")[:140].replace("\n"," ")))
    return dl

for trial_dir in TRIALS:
    D = os.path.join(ARCH, trial_dir)
    if not os.path.isdir(D):
        print(f"== MISSING {trial_dir} =="); continue
    print("="*72)
    print("RUN:", trial_dir)
    rpc = os.path.join(D, "rpc.jsonl")
    print("-- root delegate calls --")
    for name, task in root_delegates(rpc):
        print(f"   [{name}] {task}")
    print("-- child sessions --")
    for nm, sd in child_sessions(rpc).items():
        i = scan_child(sd)
        print(f"   {nm}: turns={i['turns']} ipy={i['ipython']} stops={i['stops'][-4:]} writes={sorted(set(i['writes']))} overflow={i['overflows']}")
    for f in ["grep.py", "PLAN.md", "run_tests.py", "REFLECTIONS.md"]:
        p = os.path.join(D, f)
        if os.path.exists(p):
            sz = os.path.getsize(p)
            ok = "ok"
            if f.endswith(".py"):
                try: ast.parse(open(p).read())
                except Exception as e: ok = "BROKEN:"+str(e)[:60]
            print(f"   file {f}: {sz}B {ok}")
    gp = os.path.join(D, "grep.py")
    if os.path.exists(gp):
        print("   grep.py head: " + " / ".join(open(gp).read().splitlines()[:3]))
