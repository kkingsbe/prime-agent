#!/usr/bin/env python3
"""Deep-dive a prime-agent trace: reconstruct the delegation graph + bubble-up flow.

Prints chronological events for rlm spawns, child admissions, agent_message traffic,
root tool turns, and the final file/test state. Designed for 10-50MB jsonl traces.
"""
import json
import sys
import re

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pa-single/list-ops/run.jsonl"

spawn_turns = []  # (idx, code)
admissions = []   # (idx, text)  rlm child handles seen in toolResult stdout
agent_msgs = []   # (idx, sender_role_guess, text_snip)
root_tool_calls = []  # (idx, code_head)
final_text = ""
timeline = []

with open(path) as f:
    idx = 0
    for line in f:
        idx += 1
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "message_end":
            msg = ev.get("message", {})
            if msg.get("role") != "assistant":
                continue
            for c in msg.get("content", []):
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "toolCall" and c.get("name") == "ipython":
                    code = c.get("arguments", {}).get("code", "")
                    head = code.strip().splitlines()[:4]
                    if "rlm(" in code:
                        spawn_turns.append((idx, code))
                        timeline.append((idx, "SPAWN", "\n".join(head)[:220]))
                    else:
                        root_tool_calls.append((idx, head[0] if head else ""))
                if c.get("type") == "text" and c.get("text"):
                    final_text = c["text"]
        elif t == "tool_execution_end":
            res = ev.get("result", {})
            text = ""
            if isinstance(res, dict):
                if isinstance(res.get("content"), list):
                    text = " ".join(
                        x.get("text", "")
                        for x in res["content"]
                        if isinstance(x, dict)
                    )
                elif isinstance(res.get("content"), str):
                    text = res["content"]
                stdout = res.get("stdout") or res.get("details", {}).get("stdout", "")
                if stdout:
                    text += "\n" + str(stdout)
            joined = text or ""
            # rlm admission handles appear in kernel stdout
            if "rlm_child_id" in joined or "rlm(" in joined:
                snip = re.sub(r"\s+", " ", joined)[:300]
                admissions.append((idx, snip))
                timeline.append((idx, "ADMIT", snip))
            if "agent_message" in joined and len(joined) < 8000:
                snip = re.sub(r"\s+", " ", joined)[:250]
                agent_msgs.append((idx, snip))
                timeline.append((idx, "AGENT_MSG", snip))
        elif t == "agent_end":
            for m in ev.get("messages", []):
                if m.get("role") == "assistant":
                    txt = "".join(
                        c.get("text", "")
                        for c in m.get("content", [])
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                    if txt:
                        final_text = txt

print(f"=== {path} ===")
print(f"lines: {idx}")
print(f"spawn turns: {len(spawn_turns)} | admissions seen: {len(admissions)} | agent_msg mentions: {len(agent_msgs)} | root tool turns: {len(root_tool_calls)}")
print("\n=== SPAWN TURNS (full code of rlm turns) ===")
for i, code in spawn_turns:
    print(f"-- line {i} --")
    print(code[:2500])
print("\n=== TIMELINE (chronological) ===")
for i, kind, snip in timeline:
    print(f"[{i}] {kind:10s} {snip}")
print("\n=== ROOT KERNEL TURN HEADS ===")
for i, head in root_tool_calls:
    print(f"[{i}] {head[:170]}")
print("\n=== FINAL ANSWER (tail) ===")
print(final_text[-1200:])