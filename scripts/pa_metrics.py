#!/usr/bin/env python3
"""pa_metrics.py — emit the improvement metrics for a prime-agent exercise run.

Primary signal: `rlm_child_update` events (child id/status/sessionDir/repliedSinceTask)
which the root JSON stream emits natively. Child stop reasons are read from the child
session files located via the event's sessionDir.

Usage: pa_metrics.py <run.jsonl>
"""
import json
import os
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pa-single/list-ops/run.jsonl"

children = {}  # id -> {name, statuses:[], replied:bool, sessionDir, label}
stop_reasons = []
ctx_overflow_root = 0
clean_exit = False
zero_effort = True
root_tool_turns = 0
turn_index = 0
agent_ends = 0
final_text = ""
rlm_code_turns = 0
first_reply_turn = None
n_lines = 0
last_turn_of_first_reply_child = {}
first_agent_end_turn = None

# NEW metrics (2026-08-30 forensic pass)
first_rlm_turn = None          # index of first root turn containing rlm( code
spawn_cells = 0                # distinct root turns containing rlm( code
yield_fused = False            # any spawn cell also ends with yield_turn
poll_turns = 0                 # root turns whose code is a sleep/check loop
victory_claim = False          # final text asserts success
child_aborted = 0              # children whose last stopReason == aborted
child_natural_stop = 0         # children whose last message stopReason == stop
child_cells_scan = {}          # cid -> {stops:[], last_stop, has_text} from session files

POLL_MARKERS = ("time.sleep", "sleep(", "while True")
VICTORY_MARKERS = ("all tests pass", "tests passed", "all pass", "complete and all tests", "passed all")

with open(RUN) as f:
    for line in f:
        n_lines += 1
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "message_end":
            msg = ev.get("message", {})
            if msg.get("role") == "assistant":
                turn_index += 1
                for c in msg.get("content", []):
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "toolCall" and c.get("name") == "ipython":
                        zero_effort = False
                        root_tool_turns += 1
                        code = c.get("arguments", {}).get("code", "")
                        if "rlm(" in code:
                            rlm_code_turns += 1
                            spawn_cells += 1
                            if first_rlm_turn is None:
                                first_rlm_turn = turn_index
                            if "yield_turn" in code:
                                yield_fused = True
                        if any(p in code for p in POLL_MARKERS):
                            poll_turns += 1
                    if c.get("type") == "text" and c.get("text"):
                        final_text = c["text"]
                sr = msg.get("stopReason")
                if sr:
                    stop_reasons.append(sr)
                joined = json.dumps(msg)
                if "Context size has been exceeded" in joined:
                    ctx_overflow_root += 1
        elif t == "agent_end":
            agent_ends += 1
            if first_agent_end_turn is None:
                first_agent_end_turn = turn_index
        elif t == "rlm_child_update":
            c = ev.get("child", {})
            cid = c.get("id")
            if cid not in children:
                children[cid] = {
                    "name": c.get("sessionName"),
                    "label": (c.get("label") or "")[:80],
                    "statuses": [],
                    "replied": False,
                    "sessionDir": c.get("sessionDir"),
                }
            children[cid]["statuses"].append(c.get("status"))
            if c.get("repliedSinceTask"):
                children[cid]["replied"] = True
                if first_reply_turn is None:
                    first_reply_turn = turn_index

# root integration = root turns AFTER first agent_end (re-entry via follow_up)
# OR after first child reply delivery (repliedSinceTask)
root_turns_after_reply = 0
if first_reply_turn is not None:
    root_turns_after_reply = max(0, turn_index - first_reply_turn)
integration_turns = 0
if first_agent_end_turn is not None:
    integration_turns = max(0, turn_index - first_agent_end_turn)
bubble_up = root_turns_after_reply > 0 or integration_turns > 0

# child-level stats
spawns = len(children)
terminal = 0
replied = 0
child_errors = 0
child_overflows = 0
child_turns = 0
for cid, ch in children.items():
    if "done" in ch["statuses"]:
        terminal += 1
    if ch["replied"]:
        replied += 1
    d = ch.get("sessionDir")
    ch_stops = []
    ch_last_stop = None
    if d and os.path.isdir(d):
        for cf in os.listdir(d):
            if not cf.endswith(".jsonl"):
                continue
            with open(os.path.join(d, cf)) as f:
                for line in f:
                    try:
                        cev = json.loads(line)
                    except Exception:
                        continue
                    if cev.get("type") in ("message", "message_end"):
                        m = cev.get("message", {})
                        if m.get("role") == "assistant":
                            child_turns += 1
                            sr = m.get("stopReason")
                            if sr:
                                ch_stops.append(sr)
                                ch_last_stop = sr
                            if sr in ("error", "aborted"):
                                child_errors += 1
                            if "Context size has been exceeded" in json.dumps(m):
                                child_overflows += 1
    child_cells_scan[cid] = {"stops": ch_stops, "last_stop": ch_last_stop}
    if ch_last_stop == "aborted":
        child_aborted += 1
    if ch_last_stop == "stop":
        child_natural_stop += 1

clean_exit = agent_ends >= 1 and bool(stop_reasons) and stop_reasons[-1] == "stop"
if any(v in final_text.lower() for v in VICTORY_MARKERS):
    victory_claim = True

poll_ratio = (poll_turns / root_tool_turns) if root_tool_turns else 0.0
child_work_ratio = (child_turns / root_tool_turns) if root_tool_turns else 0.0
turns_before_spawn = (first_rlm_turn - 1) if first_rlm_turn is not None else None

print(f"=== metrics: {RUN} ===")
print(f"lines            : {n_lines}")
print(f"spawns           : {spawns}  (rlm code turns: {rlm_code_turns})")
for cid, ch in children.items():
    last_stop = child_cells_scan.get(cid, {}).get("last_stop")
    print(
        f"  child {cid} '{ch['name']}': "
        f"last_status={ch['statuses'][-1] if ch['statuses'] else '?'} "
        f"last_stop={last_stop} "
        f"replied={ch['replied']} label={ch['label']!r}"
    )
print(f"child_terminal   : {terminal}/{spawns} (status 'done')")
print(f"child_replied    : {replied}/{spawns} (repliedSinceTask=true)")
print(f"child_errors     : {child_errors}  (overflows: {child_overflows}) across {child_turns} child turns")
print(f"child_aborted    : {child_aborted}/{spawns} (last stop=aborted, teardown kills)")
print(f"child_natural_stop: {child_natural_stop}/{spawns} (last stop=stop, final answer given)")
print(f"child_work_ratio : {child_work_ratio:.2f} (child turns / root tool turns)")
print(f"bubble_up        : {'YES' if bubble_up else 'NO'}  "
      f"(delivery_turns_after={root_turns_after_reply}, integration_turns_after_agent_end={integration_turns})")
print(f"ctx_overflow     : {ctx_overflow_root} (root trace)")
print(f"clean_exit       : {'YES' if clean_exit else 'NO'}  "
      f"(agent_end={agent_ends}, last stop={stop_reasons[-1] if stop_reasons else None})")
print(f"zero_effort      : {'YES' if zero_effort else 'NO'}")
print(f"root_tool_turns  : {root_tool_turns}  (poll_turn_ratio={poll_ratio:.2f}, polls={poll_turns})")
print(f"spawn_cells      : {spawn_cells}  (target 1) | yield_fused: {'YES' if yield_fused else 'NO'} | turns_before_spawn: {turns_before_spawn}")
print(f"victory_claim    : {'YES' if victory_claim else 'NO'} (final text asserts success)")
print(f"final_tail       : {final_text[-160:]!r}")