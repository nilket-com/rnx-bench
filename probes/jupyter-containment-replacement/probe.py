#!/usr/bin/env python3
import ctypes, json, os, pathlib, signal, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "rnx/tests"))
from worker_parent import Parent

assert sys.platform == "linux"
assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0


def log(**x):
    print(json.dumps(x), flush=True)


def children():
    found = set()
    for task in pathlib.Path("/proc/self/task").iterdir():
        try:
            found.update(map(int, (task / "children").read_text().split()))
        except FileNotFoundError:
            pass
    return found


def sweep():
    start = time.monotonic()
    seen = set()
    while True:
        current = children()
        if not current:
            return dict(
                reaped=sorted(seen),
                cleanup_ms=round((time.monotonic() - start) * 1000, 3),
            )
        assert time.monotonic() - start < 5, ("cleanup timeout", current)
        for pid in current:
            # No other reaper runs concurrently. Unreaped children cannot reuse PIDs;
            # pidfds bind signalling to the identity we opened.
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                if pid in children():
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)
            try:
                if os.waitpid(pid, os.WNOHANG)[0]:
                    seen.add(pid)
            except ChildProcessError:
                pass
        time.sleep(0.005)


def alive(pid):
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


def worker_case(mode):
    with tempfile.TemporaryDirectory() as d:
        ready = pathlib.Path(d) / "ready"
        w = Parent(str(ROOT.parents[2] / "rnx/target/release/rnx"))
        try:
            args = [str(ROOT / "descendant.py"), str(ready)]
            w.begin(
                f"process::run({json.dumps(sys.executable)}, {json.dumps(args)}, #{{timeout_ms: 2000}})?"
            )
            assert w.message(5)["type"] == "armed"
            end = time.monotonic() + 5
            while not ready.exists():
                assert time.monotonic() < end
                time.sleep(0.005)
            fixture = json.loads(ready.read_text())
            assert alive(fixture["pid"])
            if mode == "cooperative":
                os.kill(w.p.pid, signal.SIGINT)
                reply, _ = w.settled()
                w.handoff()
                assert reply["failure"]["category"] == "interrupted"
                w.close()
            else:
                if mode == "stopped":
                    os.kill(w.p.pid, signal.SIGSTOP)
                    end = time.monotonic() + 5
                    while (
                        pathlib.Path(f"/proc/{w.p.pid}/stat")
                        .read_text()
                        .split(") ", 1)[1][0]
                        != "T"
                    ):
                        assert time.monotonic() < end
                        time.sleep(0.002)
                w.p.kill()
                w.p.wait(timeout=5)
                w.close()
            result = sweep()
            assert not alive(fixture["pid"])
            assert fixture["pid"] in result["reaped"]
            log(
                case=mode, discovery="all task children, no fixture PID input", **result
            )
        finally:
            w.close()
            sweep()


def pdeath_case(mode):
    p = subprocess.Popen(
        [str(ROOT / "pdeath"), mode], stdout=subprocess.PIPE, text=True
    )
    try:
        first = json.loads(p.stdout.readline())
        armed = first.get("armed", False)
        if armed:
            first = json.loads(p.stdout.readline())
        pid = first["spawned"]
        if mode == "race":
            p.wait(timeout=5)
            end = time.monotonic() + 5
            while alive(pid):
                assert time.monotonic() < end
                time.sleep(0.005)
            _, status = os.waitpid(pid, 0)
            assert os.waitstatus_to_exitcode(status) == 92
            log(case="parent_dies_before_prctl", exit=92)
        else:
            if not armed:
                assert json.loads(p.stdout.readline())["armed"]
            if mode == "thread-race":
                time.sleep(0.3)
                assert alive(pid) and p.poll() is None
                log(
                    case="spawning_thread_died_before_prctl",
                    child_alive=True,
                    parent_alive=True,
                    observation="getppid check does not detect prior spawning-thread exit",
                )
                return
            if mode == "normal":
                p.kill()
                p.wait(timeout=5)
            end = time.monotonic() + 5
            while alive(pid):
                assert time.monotonic() < end
                time.sleep(0.005)
            if mode == "normal":
                _, status = os.waitpid(pid, 0)
                assert os.waitstatus_to_exitcode(status) == -9
            else:
                assert p.poll() is None
            log(
                case="parent_death_" + mode,
                child_alive=False,
                parent_alive=p.poll() is None,
            )
    finally:
        if p.poll() is None:
            p.kill()
        p.wait(timeout=5)
        p.stdout.close()
        sweep()


for mode in ["cooperative", "hard_kill", "stopped"]:
    worker_case(mode)
for mode in ["normal", "race", "thread", "thread-race"]:
    pdeath_case(mode)
log(cleanup="no remaining children", children=sorted(children()))
