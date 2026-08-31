#!/usr/bin/env python3
"""Analyze a prime-agent JSON-mode trace for delegation behavior."""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pa-probe/probe.jsonl"

rlm_spawns = 0
agent_msgs = 0
tool_calls = 0
rlm_code_turns = 0
statuses = {}
final_text = ""

with open(path) as f:
    for line in f:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "tool_execution_start":
            tool_calls += 1
            if ev.get("toolName") == "rlm":
                rlm_spawns += 1
        if t == "message_end":
            msg = ev.get("message", {})
            for c in msg.get("content", []):
                if isinstance(c, dict) and c.get("type") == "toolCall" and c.get("name") == "ipython":
                    code = c.get("arguments", {}).get("code", "")
                    if "rlm(" in code:
                        rlm_code_turns += 1
        if "agent_message" in json.dumps(ev):
            agent_msgs += 1
        if t == "agent_end":
            for m in ev.get("messages", []):
                if m.get("role") == "assistant":
                    txt = "".join(
                        c.get("text", "")
                        for c in m.get("content", [])
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                    if txt:
                        final_text = txt
        if t == "tool_execution_end":
            st = ev.get("result", {})
            statuses[ev.get("toolName", "?")] = statuses.get(ev.get("toolName", "?"), 0) + 1

print(f"tool_execution_total: {tool_calls}")
print(f"rlm_named_tool_events: {rlm_spawns}")
print(f"ipython_turns_containing_rlm_code: {rlm_code_turns}")
print(f"agent_message_events: {agent_msgs}")
print("statuses:", statuses)
print("---final answer---")
print(final_text[-600:])