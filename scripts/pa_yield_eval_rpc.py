#!/usr/bin/env python3
"""pa_yield_eval_rpc.py — RPC-mode yield eval (validates the REAL deployment path).

Same case as pa_yield_eval.py but drives prime-agent over --mode rpc:
after the agent spawns rlm() children, the turn must end (agent_end) with NO
further tool-call message from the root. Early-kills as soon as the verdict is
known. JSON-mode validation is NOT representative (RPC keeps the session alive
and adds re-entry semantics).

Usage: pa_yield_eval_rpc.py --workdir <dir> --model <model> --prompt "<task>" [--deadline N]
Exit: 0=PASS 1=FAIL 2=TIMEOUT
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
    ap.add_argument("--model", default="bartowski/Ling-3.0-tiny-GGUF")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--deadline", type=int, default=600)
    args = ap.parse_args()

    env = dict(os.environ)
    env["RIG_API_KEY"] = open("/opt/data/.unsloth_api_key").read().strip()
    env["PRIME_AGENT_TELEMETRY"] = "0"

    proc = subprocess.Popen(
        [PA, "--mode", "rpc", "--provider", "rig", "--model", args.model],
        cwd=args.workdir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
        bufsize=1,
    )
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)

    proc.stdin.write(json.dumps({"type": "prompt", "message": args.prompt, "id": "req-1"}) + "\n")
    proc.stdin.flush()

    state = {
        "spawn_seen": False,
        "any_tool_after_spawn": False,
        "verdict": None,
    }
    deadline = time.time() + args.deadline
    t0 = time.time()

    def classify(ev):
        """Root-session events only: message_end of assistant tool/text messages,
        and agent_end. Child sessions stream some events too; we only act on the
        root's own message_end volume via the stream."""
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
            if has_tool:
                state["any_tool_after_spawn"] = True
                state["verdict"] = "FAIL"
                print(
                    f"[yield] FAIL: root tool call after spawn at {time.time()-t0:.1f}s",
                    flush=True,
                )
                return True
            # tool-free assistant message (text yield) — allow; agent_end decides
            if msg.get("stopReason") == "stop":
                state["verdict"] = "PASS"
                print(
                    f"[yield] PASS: root yielded with tool-free message at {time.time()-t0:.1f}s",
                    flush=True,
                )
                return True
        if state["spawn_seen"] and state["verdict"] is None and not state["any_tool_after_spawn"]:
            if t == "agent_end":
                state["verdict"] = "PASS"
                print(
                    f"[yield] PASS: turn ended via agent_end after spawn at {time.time()-t0:.1f}s",
                    flush=True,
                )
                return True
        return False

    while time.time() < deadline and state["verdict"] is None:
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
        state["verdict"] = "TIMEOUT"
        print(f"[yield] TIMEOUT ({args.deadline}s): no verdict", flush=True)

    try:
        proc.stdin.close()
    except Exception:
        pass
    try:
        proc.kill()
        proc.wait(timeout=5)
    except Exception:
        pass

    print(f"[yield] final: {state['verdict']}  ({time.time()-t0:.1f}s wall)", flush=True)
    sys.exit(0 if state["verdict"] == "PASS" else (1 if state["verdict"] == "FAIL" else 2))


if __name__ == "__main__":
    main()