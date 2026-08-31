#!/usr/bin/env python3
"""pa_yield_eval.py — PASS/FAIL eval for post-delegation self-yield.

Case: after the agent spawns rlm() children, it must END ITS TURN (plain-text
message, no tool call) as its very next assistant message. Any tool call after
the spawn message = FAIL. Missing/yielding late = FAIL. Early-kills the process
the moment the verdict is known, so we never wait for full cases.

Usage: pa_yield_eval.py --workdir <dir> --model <model> --prompt "<task>"
Exit: 0=PASS (self-yield within N tool-free turns)  1=FAIL (tool call after spawn)
      2=TIMEOUT (no verdict in deadline)
"""
import argparse
import json
import os
import selectors
import subprocess
import sys
import time

PA = "/opt/data/repos/prime-agent/prime-agent.sh"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--model", default="LiquidAI/LFM2.5-2.6B-GGUF")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--deadline", type=int, default=240)
    args = ap.parse_args()

    env = dict(os.environ)
    env["RIG_API_KEY"] = open("/opt/data/.unsloth_api_key").read().strip()
    env["PRIME_AGENT_TELEMETRY"] = "0"

    proc = subprocess.Popen(
        [PA, "--mode", "json", "--provider", "rig", "--model", args.model, args.prompt],
        cwd=args.workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
        bufsize=1,
    )
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)

    state = {
        "spawn_seen": False,
        "assistant_msgs_after_spawn": 0,
        "verdict": None,
        "any_tool_after_spawn": False,
    }
    deadline = time.time() + args.deadline
    t0 = time.time()

    def classify(ev):
        """Return True when verdict known (PASS/FAIL)."""
        t = ev.get("type")
        if t == "message_end":
            msg = ev.get("message", {})
            if msg.get("role") != "assistant":
                return False
            has_tool = any(
                isinstance(c, dict) and c.get("type") == "toolCall"
                for c in msg.get("content", [])
            )
            code = ""
            for c in msg.get("content", []):
                if isinstance(c, dict) and c.get("type") == "toolCall":
                    code = c.get("arguments", {}).get("code", "")
            if not state["spawn_seen"]:
                if has_tool and "rlm(" in code:
                    state["spawn_seen"] = True
                    print(f"[yield] spawn turn at {time.time()-t0:.1f}s", flush=True)
                return False
            # spawn seen: any further assistant message with a tool call = FAIL
            if has_tool:
                state["assistant_msgs_after_spawn"] += 1
                state["any_tool_after_spawn"] = True
                state["verdict"] = "FAIL"
                print(
                    f"[yield] FAIL: tool call {state['assistant_msgs_after_spawn']} "
                    f"msg(s) after spawn (no self-yield)",
                    flush=True,
                )
                return True
            if msg.get("stopReason") == "stop":
                state["verdict"] = "PASS"
                print(
                    f"[yield] PASS: self-yielded on msg "
                    f"{state['assistant_msgs_after_spawn'] + 1} after spawn at {time.time()-t0:.1f}s",
                    flush=True,
                )
                return True
        if state["spawn_seen"] and not state["any_tool_after_spawn"]:
            # terminate-style yield: agent_end arrives with no further assistant tool message
            if t in ("turn_end", "agent_end") and state["verdict"] is None:
                state["verdict"] = "PASS"
                print(
                    f"[yield] PASS: turn ended via terminate (yield_turn) at {time.time()-t0:.1f}s",
                    flush=True,
                )
                return True
        return False

    while time.time() < deadline:
        r = sel.select(timeout=0.2)
        if not r:
            continue
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if classify(ev):
            break

    if state["verdict"] is None:
        state["verdict"] = "TIMEOUT" if time.time() >= deadline else "TIMEOUT"
        print(f"[yield] TIMEOUT ({args.deadline}s): no verdict", flush=True)

    proc.kill()
    try:
        proc.wait(timeout=5)
    except Exception:
        pass

    print(f"[yield] final: {state['verdict']}  ({time.time()-t0:.1f}s wall)", flush=True)
    sys.exit(0 if state["verdict"] == "PASS" else (1 if state["verdict"] == "FAIL" else 2))


if __name__ == "__main__":
    main()