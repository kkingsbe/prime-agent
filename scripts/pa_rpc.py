#!/usr/bin/env python3
"""pa_rpc.py — run one exercise through prime-agent RPC mode with bubble-up support.

RPC keeps the root session alive past the first agent_end, so child agent_message
replies can re-enter the parent. On first agent_end we send a follow_up that commands
integration; we collect the final answer on the second agent_end.

Usage:
  pa_rpc.py --workdir <dir> --model <model> [--delegate] --prompt "<task>"

Events are dumped to <workdir>/rpc.jsonl for pa_metrics.py.
"""
import argparse
import json
import os
import selectors
import subprocess
import sys
import time

PA = "/opt/data/repos/prime-agent/prime-agent.sh"

# RPC stream carries per-token streaming deltas (thinking_delta, toolcall_delta,
# message_update, ...) that explode the trace to GB scale on thinking models with
# active children (measured: 3.9GB in ~6 min, LFM2.5 phone-number armA2 2026-08-31).
# pa_metrics.py only consumes terminal events (message_end / agent_end /
# rlm_child_update / turn_end) + child session files. Drop the deltas at the write
# site; keep the driver's live logic on the raw stream untouched.
DROP_EVENT_TYPES = {
    "thinking",
    "thinking_delta",
    "reasoning",
    "reasoning_delta",
    "text",
    "text_delta",
    "message_update",
    "message_delta",
    "toolcall_delta",
    "toolcall_update",
    "tool_execution_update",
    "tool_execution_delta",
    "tool_result_delta",
}

# Child statuses that mean the child will not produce more work. "done" is a
# natural completion; cancelled/error are teardown or provider failures.
TERMINAL_CHILD_STATUSES = {"done", "cancelled", "error"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--model", default="bartowski/Ling-3.0-tiny-GGUF")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--deadline", type=int, default=900)
    args = ap.parse_args()

    env = dict(os.environ)
    env["RIG_API_KEY"] = open("/opt/data/.unsloth_api_key").read().strip()
    env["PRIME_AGENT_TELEMETRY"] = "0"

    evfile = os.path.join(args.workdir, "rpc.jsonl")
    evf = open(evfile, "w")
    dropped_by_type: dict[str, int] = {}
    kept_lines = 0

    proc = subprocess.Popen(
        [PA, "--mode", "rpc", "--provider", "rig", "--model", args.model],
        cwd=args.workdir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1,
    )
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, "out")

    def send(cmd):
        proc.stdin.write(json.dumps(cmd) + "\n")
        proc.stdin.flush()

    send({"type": "prompt", "message": args.prompt, "id": "req-1"})

    deadline = time.time() + args.deadline
    agent_ends = 0
    followup_sent = False
    yielded_steered = False
    spawned_at_turn = None
    turns = 0
    last_event = time.time()
    children_status: dict[str, str] = {}
    integrate_sent = False

    def drain():
        nonlocal agent_ends, followup_sent, last_event, spawned_at_turn, yielded_steered, turns, kept_lines, integrate_sent
        while True:
            r = sel.select(timeout=0.2)
            if not r:
                break
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            last_event = time.time()
            try:
                ev = json.loads(line)
            except Exception:
                continue
            et = ev.get("type")
            if et in DROP_EVENT_TYPES:
                dropped_by_type[et] = dropped_by_type.get(et, 0) + 1
                continue
            evf.write(line + "\n")
            kept_lines += 1
            if et == "message_end":
                msg = ev.get("message", {})
                if msg.get("role") == "assistant":
                    turns += 1
                    for c in msg.get("content", []):
                        if (
                            isinstance(c, dict)
                            and c.get("type") == "toolCall"
                            and c.get("name") == "ipython"
                        ):
                            code = c.get("arguments", {}).get("code", "")
                            if "rlm(" in code and spawned_at_turn is None:
                                spawned_at_turn = turns
                                print("[rpc] detected rlm() spawn; arming yield enforcement", flush=True)
                    sr = msg.get("stopReason")
                    if sr == "toolUse" and spawned_at_turn is not None:
                        if turns - spawned_at_turn >= 2 and not yielded_steered:
                            yielded_steered = True
                            send({
                                "type": "steer",
                                "message": (
                                    "You have delegated with rlm(). Stop working now: "
                                    "END YOUR TURN and yield. Children run in the background; "
                                    "you will be re-entered when their results arrive."
                                ),
                                "id": "req-yield",
                            })
                            print("[rpc] steered root to yield (2+ tool turns after spawn)", flush=True)
            elif et == "turn_end":
                pass
            if et == "agent_end":
                agent_ends += 1
                print(f"[rpc] agent_end #{agent_ends} at {time.time():.0f}", flush=True)
                if children_status:
                    # Delegation path: never conclude while children are still active.
                    if all(s in TERMINAL_CHILD_STATUSES for s in children_status.values()):
                        print("[rpc] final agent_end — all children terminal; done", flush=True)
                        return True
                    print(
                        f"[rpc] agent_end #{agent_ends} but children active "
                        f"({dict(children_status)}); waiting for child-done re-entry",
                        flush=True,
                    )
                else:
                    if agent_ends == 1 and not followup_sent:
                        followup_sent = True
                        send({
                            "type": "follow_up",
                            "message": (
                                "Children may have replied via agent_message or written files. "
                                "INTEGRATE now: read what they produced, apply/fix the solution in the "
                                "exercise files, run the test suite yourself, and give the final answer."
                            ),
                            "id": "req-2",
                        })
                        print("[rpc] sent integration follow_up (single)", flush=True)
                    elif agent_ends >= 2:
                        print("[rpc] final agent_end — done", flush=True)
                        return True
            elif et == "rlm_child_update":
                c = ev.get("child", {})
                cid = c.get("id")
                if cid:
                    children_status[cid] = c.get("status")
                if c.get("status") in ("queued", "done") or c.get("repliedSinceTask"):
                    print(
                        f"[rpc] child {c.get('sessionName')} status={c.get('status')} "
                        f"replied={c.get('repliedSinceTask')}",
                        flush=True,
                    )
                # Re-entry on child completion: once ALL children are terminal, nudge
                # the root to integrate (retro open item: reports arrive late; the
                # root must be re-entered AFTER children finish, not before).
                if (
                    children_status
                    and all(s in TERMINAL_CHILD_STATUSES for s in children_status.values())
                    and not integrate_sent
                ):
                    integrate_sent = True
                    send({
                        "type": "follow_up",
                        "message": (
                            "All subagents have finished. INTEGRATE now: read what they "
                            "produced (files + reports), apply/fix the solution in the "
                            "exercise files, run the test suite yourself, and give the "
                            "final answer once the tests pass."
                        ),
                        "id": "req-integrate",
                    })
                    print("[rpc] all children terminal; sent integration follow_up", flush=True)
        return False

    done = False
    while time.time() < deadline and not done:
        done = drain()
        # NO repeated nudges: a single follow_up above is the only re-entry.
        # If the process goes quiet, we just wait; the deadline bounds the run.
    if not done:
        print(f"[rpc] deadline exceeded ({args.deadline}s); aborting", flush=True)
        try:
            send({"type": "abort", "id": "req-9"})
        except Exception:
            pass

    try:
        proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=20)
    except Exception:
        proc.kill()
    evf.close()
    total_dropped = sum(dropped_by_type.values())
    if total_dropped:
        top = ", ".join(f"{k}={v}" for k, v in sorted(dropped_by_type.items(), key=lambda kv: -kv[1])[:5])
        print(f"[rpc] stream filter: kept {kept_lines} terminal events, dropped {total_dropped} delta events ({top}, ...)", flush=True)
    print(f"[rpc] events -> {evfile}", flush=True)


if __name__ == "__main__":
    main()