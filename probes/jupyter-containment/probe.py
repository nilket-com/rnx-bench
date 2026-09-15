#!/usr/bin/env python3
"""Linux observation of worker-owned deadlines, with explicit cleanup/reaping."""

import argparse, ctypes, json, os, pathlib, signal, sys, tempfile, time

root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root.parent / "rnx/tests"))
from worker_parent import Parent

assert sys.platform == "linux", "Linux execution probe; no Windows claim"
assert (
    ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
)  # PR_SET_CHILD_SUBREAPER


def alive(pid):
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


def reap(pid):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        try:
            if os.waitpid(pid, os.WNOHANG)[0]:
                return
        except ChildProcessError:
            return
        time.sleep(0.005)
    raise AssertionError(f"failed to reap owned child {pid}")


def case(binary, mode):
    child = None
    with tempfile.TemporaryDirectory() as tmp:
        ready = pathlib.Path(tmp) / "ready.json"
        w = Parent(binary)
        try:
            args = [str(pathlib.Path(__file__).parent / "child.py"), str(ready)]
            if mode == "escape_then_interrupt":
                args.append("escape")
            source = f"process::run({json.dumps(sys.executable)}, {json.dumps(args)}, #{{timeout_ms: 2000}})?"
            start = time.monotonic()
            w.begin(source)
            assert w.message(5)["type"] == "armed"
            limit = time.monotonic() + 5
            while not ready.exists():
                assert time.monotonic() < limit
                time.sleep(0.005)
            child = json.loads(ready.read_text())
            assert child["group"] != os.getpgrp()
            assert alive(child["pid"])
            action = time.monotonic()
            if mode == "deadline":
                reply, _ = w.settled()
                w.handoff()
                assert reply["failure"] is None
                assert '"timed_out": true' in reply["text_plain"], reply
            elif mode in ("interrupt", "escape_then_interrupt"):
                os.kill(w.p.pid, signal.SIGINT)
                reply, _ = w.settled()
                w.handoff()
                assert reply["failure"]["category"] == "interrupted", reply
                if mode == "escape_then_interrupt":
                    time.sleep(2.5)  # also observe the escaped child after the deadline
            else:
                if mode == "interrupt_stopped_then_kill":
                    os.kill(w.p.pid, signal.SIGSTOP)
                    # Wait for stop before delivering the interrupt; cleanup cannot run.
                    until = time.monotonic() + 5
                    while (
                        pathlib.Path(f"/proc/{w.p.pid}/stat")
                        .read_text()
                        .split(") ", 1)[1][0]
                        != "T"
                    ):
                        assert time.monotonic() < until
                        time.sleep(0.002)
                    os.kill(w.p.pid, signal.SIGINT)
                w.p.kill()
                w.p.wait(timeout=5)
                assert w.messages.get(timeout=5) is None
                # Wait past the requested 2-second child deadline, measured from
                # after the child announced itself (therefore after spawn).
                time.sleep(2.5)
            survives = alive(child["pid"])
            expected = mode not in ("deadline", "interrupt")
            assert survives == expected, (mode, child, survives)
            print(
                json.dumps(
                    dict(
                        case=mode,
                        requested_child_deadline_ms=2000,
                        since_action_ms=round(1000 * (time.monotonic() - action), 3),
                        since_execute_ms=round(1000 * (time.monotonic() - start), 3),
                        worker_alive=w.p.poll() is None,
                        child=child,
                        child_alive=survives,
                        observation="survival; harness will kill and reap"
                        if survives
                        else "child ended",
                    )
                ),
                flush=True,
            )
        finally:
            w.close()
            if child:
                for group in {child["group"], child["helper"]}:
                    assert group != os.getpgrp()
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                for pid in {child["pid"], child["helper"]}:
                    reap(pid)
                assert not alive(child["pid"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rnx", required=True)
    a = p.parse_args()
    for mode in [
        "deadline",
        "interrupt",
        "kill",
        "interrupt_stopped_then_kill",
        "escape_then_interrupt",
    ]:
        case(a.rnx, mode)
    print(json.dumps(dict(cleanup="all owned descendants killed/reaped; no survivors")))
