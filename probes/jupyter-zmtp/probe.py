#!/usr/bin/env python3
"""Local interoperability and bounded-size counterexamples; not a kernel."""

import json, os, pathlib, queue, socket, struct, subprocess, threading, time, sys
import zmq
from jupyter_client.session import Session

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = pathlib.Path(
    os.environ.get("RNX_ZMTP_RESULTS", ROOT / "../../results/jupyter-zmtp-0048-extension")
)
BINARY = pathlib.Path(
    os.environ.get("RNX_ZMTP_BINARY", ROOT / "target/release/jupyter-zmtp-probe")
)
TIMEOUT = 5


def memory_limit():
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def rss(p):
    # Native + Rust resident memory, sampled externally; page-resolution observation.
    return int(
        pathlib.Path(f"/proc/{p.pid}/statm").read_text().split()[1]
    ) * __import__("os").sysconf("SC_PAGE_SIZE")


def log(**v):
    print(json.dumps(v), flush=True)


class Server:
    def __init__(self, empty=False):
        started = time.monotonic()
        self.errors = open(
            RESULTS
            / ("empty-stderr.txt" if empty else "transport-stderr.txt"),
            "w",
        )
        self.p = subprocess.Popen(
            [
                str(BINARY),
                *(["empty"] if empty else []),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.errors,
            preexec_fn=memory_limit,
            text=True,
            bufsize=1,
        )
        self.lines = queue.Queue()

        def reader():
            for line in self.p.stdout:
                self.lines.put(json.loads(line))

        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()
        self.address = self.lines.get(timeout=TIMEOUT)
        log(
            case="transport_ready",
            elapsed_ms=round((time.monotonic() - started) * 1000, 3),
        )
        self.ctx = zmq.Context()
        self.session = Session(
            key=b"" if empty else b"local-probe-key", signature_scheme="hmac-sha256"
        )
        self.shell = self.new(zmq.DEALER, "shell")
        self.control = self.new(zmq.DEALER, "control")
        self.hb = self.new(zmq.REQ, "hb")

    def new(self, kind, name):
        s = self.ctx.socket(kind)
        s.setsockopt(zmq.LINGER, 0)
        if kind == zmq.DEALER:
            s.setsockopt(zmq.IDENTITY, self.session.bsession)
        s.setsockopt(zmq.SNDTIMEO, 5000)
        s.connect(self.address[name])
        return s

    def stats(self, reset=False):
        self.p.stdin.write("reset_alloc\n" if reset else "stats\n")
        self.p.stdin.flush()
        return self.lines.get(timeout=TIMEOUT)

    def until(self, predicate):
        until = time.monotonic() + TIMEOUT
        while time.monotonic() < until:
            v = self.stats()
            if predicate(v):
                return v
            time.sleep(0.01)
        raise AssertionError("stats deadline")

    def request(self, content, sock=None, prefix=None):
        sock = sock or self.shell
        msg = self.session.msg("probe_request", content=content)
        msg["metadata"]["future_extension"] = True
        frames = self.session.serialize(msg)
        if prefix:
            frames = [prefix, *frames]
        sock.send_multipart(frames)
        assert sock.poll(5000), "reply deadline"
        identities, parts = self.session.feed_identities(sock.recv_multipart())
        answer = self.session.deserialize(parts)
        assert answer["parent_header"]["msg_id"] == msg["header"]["msg_id"]
        assert answer["content"]["echo"] == content
        if prefix:
            assert identities == [prefix]
        return answer

    def ping(self):
        start = time.monotonic()
        self.hb.send(b"heartbeat\0bytes")
        assert self.hb.poll(1000)
        assert self.hb.recv() == b"heartbeat\0bytes"
        return round((time.monotonic() - start) * 1000, 3)

    def close(self):
        self.ctx.destroy(linger=0)
        try:
            self.p.stdin.write("stop\n")
            self.p.stdin.flush()
        except BrokenPipeError:
            pass
        try:
            self.p.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(timeout=TIMEOUT)
            raise
        finally:
            self.p.stdin.close()
            self.thread.join(TIMEOUT)
            self.p.stdout.close()
            self.errors.close()
        assert self.p.returncode == 0
        final = self.lines.get(timeout=TIMEOUT)["shutdown"]
        assert final["publication_reserved"] == 0
        assert all(
            e["connections"] == e["routes"] == e["incoming_reserved"] == 0
            for e in final["endpoints"]
        )
        log(case="shutdown_credits", released=True)


def exact(sock, n):
    b = b""
    while len(b) < n:
        part = sock.recv(n - len(b))
        assert part
        b += part
    return b


def raw_dealer(address):
    host, port = address.removeprefix("tcp://").rsplit(":", 1)
    s = socket.create_connection((host, int(port)), timeout=TIMEOUT)
    greeting = bytearray(64)
    greeting[0] = 255
    greeting[9] = 127
    greeting[10] = 3
    greeting[12:16] = b"NULL"
    s.sendall(greeting)
    assert len(exact(s, 64)) == 64
    ready = b"\x05READY\x0bSocket-Type" + struct.pack(">I", 6) + b"DEALER"
    s.sendall(bytes([4, len(ready)]) + ready)
    flag = exact(s, 1)[0]
    n = struct.unpack(">Q", exact(s, 8))[0] if flag & 2 else exact(s, 1)[0]
    assert exact(s, n).startswith(b"\x05READY")
    return s


def endpoint(s, name):
    return next(e for e in s.stats()["endpoints"] if e["name"] == name)


def frame(b, more=False, command=False):
    f = (1 if more else 0) | (4 if command else 0)
    return (
        bytes([f, len(b)]) + b
        if len(b) < 256
        else bytes([f | 2]) + struct.pack(">Q", len(b)) + b
    )


def receive(raw):
    f = exact(raw, 1)[0]
    n = struct.unpack(">Q", exact(raw, 8))[0] if f & 2 else exact(raw, 1)[0]
    return f, exact(raw, n)


def handshake(
    s, name="shell", identity=None, kind="DEALER", props=None, version=3, split=False
):
    host, port = s.address[name].removeprefix("tcp://").split(":")
    r = socket.create_connection((host, int(port)), timeout=5)
    g = bytearray(64)
    g[0] = 255
    g[9] = 127
    g[10] = version
    g[11] = 1
    g[12:16] = b"NULL"
    if split:
        for b in g:
            r.sendall(bytes([b]))
    else:
        r.sendall(g)
    server = exact(r, 64)
    assert server[10:12] == b"\x03\x00"
    f, ready = receive(r)
    assert f == 4 and ready.startswith(b"\x05READY")
    pairs = [(b"Socket-Type", kind.encode())]
    if identity is not None:
        pairs.append((b"Identity", identity))
    if props:
        pairs += props
    b = b"\x05READY" + b"".join(
        bytes([len(k)]) + k + struct.pack(">I", len(v)) + v for k, v in pairs
    )
    wire = frame(b, command=True)
    if split:
        for b in wire:
            r.sendall(bytes([b]))
    else:
        r.sendall(wire)
    return r


def eof(r):
    try:
        while r.recv(8192):
            pass
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        r.close()


def raw_request(s, r, content, prefixes=[]):
    msg = s.session.msg("probe_request", content=content)
    frames = [*prefixes, *s.session.serialize(msg)]
    r.sendall(b"".join(frame(f, i < len(frames) - 1) for i, f in enumerate(frames)))
    answer = []
    while True:
        f, b = receive(r)
        answer.append(b)
        if not f & 1:
            break
    identities, parts = s.session.feed_identities(answer)
    result = s.session.deserialize(parts)
    assert result["parent_header"]["msg_id"] == msg["header"]["msg_id"]
    assert result["content"]["echo"] == content
    assert identities == prefixes
    return result


def run():
    s = Server()
    try:
        s.request({"hello": 42}, prefix=b"extra")
        s.request({"control": True}, s.control)
        assert s.ping() < 500
        stdin = s.new(zmq.DEALER, "stdin")
        s.request({"stdin": True}, stdin)
        stdin.close(0)
        log(case="signed_channels", passed=True, python_libzmq=zmq.zmq_version())
        # Real SUB with ZMTP heartbeat settings must stay compatible with 3.0.
        sub = s.ctx.socket(zmq.SUB)
        sub.setsockopt(zmq.LINGER, 0)
        sub.setsockopt(
            zmq.HEARTBEAT_IVL, 0 if "--diagnostic-no-heartbeats" in sys.argv else 100
        )
        sub.setsockopt(zmq.SUBSCRIBE, b"probe")
        sub.connect(s.address["iopub"])
        end = time.monotonic() + 5
        while True:
            s.request({"publish": 1}, s.control)
            if sub.poll(50):
                assert sub.recv_multipart()[0] == b"probe"
                break
            assert time.monotonic() < end
        time.sleep(0.4)
        s.request({"publish": 1}, s.control)
        if not sub.poll(500):
            log(case="heartbeat_downgrade_stop", stats=s.stats())
            raise AssertionError(
                "3.0 heartbeat-enabled client disconnected; see last_failure"
            )
        sub.recv_multipart()
        log(
            case="3_1_client_downgrade",
            heartbeat_enabled="--diagnostic-no-heartbeats" not in sys.argv,
            passed=True,
            trace=s.stats()["wire_trace"],
        )
        sub.close(0)
        before = s.stats()
        bad = s.session.serialize(s.session.msg("probe_request", content={}))
        bad[1] = b"0" * 64
        s.shell.send_multipart(bad)
        s.until(lambda v: v["bad_signature"] > before["bad_signature"])
        assert not s.shell.poll(50)
        log(case="wrong_signature", no_reply=True)
        for length in [1048577, 2**32 - 1, 2**64 - 2, 2**64 - 1]:
            r = handshake(s)
            r.sendall(b"\x02" + struct.pack(">Q", length))
            eof(r)
            log(case="declared_length_refused", length=length, body_sent=0)
        r = handshake(s, split=True)
        raw_request(s, r, {"split": True}, [b"prefix"] * 26)
        r.close()
        log(case="split_greeting_ready_and_32_parts", passed=True)
        r = handshake(s)
        r.sendall(b"\x01\x00" * 32 + b"\x00\x00")
        eof(r)
        log(case="33_empty_parts", refused=True)
        # More input may enter TCP buffers, but it must never enter an unbounded server queue.
        r = handshake(s)
        before = rss(s.p)
        sent = 0
        try:
            for _ in range(4096):
                r.sendall(frame(b"x" * 8192, True))
                sent += 8192
        except (ConnectionResetError, BrokenPipeError):
            pass
        eof(r)
        log(
            case="former_32MiB_case",
            attempted=33554432,
            tcp_bytes_sent=sent,
            rss_before=before,
            rss_after=rss(s.p),
            peer_closed=True,
        )
        # Valid lower boundary reaches application; one byte extra does not.
        for n in [1048576, 1048577]:
            before = s.stats()
            r = handshake(s)
            wire = frame(b"x" * n)
            try:
                r.sendall(wire)
            except (ConnectionResetError, BrokenPipeError):
                pass
            eof(r)
            after = s.stats()
            assert (after["messages_received"] > before["messages_received"]) == (
                n == 1048576
            )
            log(case="payload_boundary", n=n, reached_application=n == 1048576)
        # Collision injected using a declared name in the generated zero-prefix namespace.
        s.until(lambda v: all(e["incoming_reserved"] == 0 for e in v["endpoints"]))
        nxt = s.stats()["next_generation"]
        declared = b"\0" + (nxt + 1).to_bytes(8, "big")
        r1 = handshake(s, identity=declared)
        raw_request(s, r1, {"declared": True})
        before = s.stats()["generated_collisions"]
        r2 = handshake(s)
        raw_request(s, r2, {"anonymous": True})
        assert s.stats()["generated_collisions"] == before + 1
        dup = handshake(s, identity=declared)
        eof(dup)
        raw_request(s, r1, {"original_still_live": True})
        r1.close()
        s.until(
            lambda v: all(
                declared.hex() != i["id"]
                for e in v["endpoints"]
                if e["name"] == "shell"
                for i in e["identities"]
            )
        )
        r3 = handshake(s, identity=declared)
        raw_request(s, r3, {"reconnected": True})
        r2.close()
        r3.close()
        log(case="identities_reconnect_and_collision", passed=True)
        # Separate endpoint cap, with incomplete handshakes counted too.
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "stdin")["connections"]
                == 0
            )
        )
        peers = [handshake(s, "stdin") for _ in range(8)]
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "stdin")["connections"]
                == 8
            )
        )
        host, port = s.address["stdin"].removeprefix("tcp://").split(":")
        extra = socket.create_connection((host, int(port)), timeout=5)
        eof(extra)
        assert s.ping() < 500
        for r in peers:
            r.close()
        log(case="eight_connections_ninth_closed", passed=True)
        for count in [64, 65]:
            props = [(f"X-{i}".encode(), b"") for i in range(count - 1)]
            r = handshake(s, props=props)
            if count == 64:
                raw_request(s, r, {"metadata64": True})
                r.close()
            else:
                eof(r)
        for props in [[(b"socket-TYPE", b"DEALER")], [(b"Bad!", b"")]]:
            r = handshake(s, props=props)
            eof(r)
        log(case="metadata_count_duplicate_and_names", passed=True)
        # Handshake stall: drain the greeting then wait for the absolute timer.
        r = socket.create_connection((host, int(port)), timeout=5)
        exact(r, 64)
        start = time.monotonic()
        eof(r)
        elapsed = time.monotonic() - start
        assert 1.5 < elapsed < 3
        log(case="handshake_deadline", elapsed_ms=round(elapsed * 1000, 3))
        r = handshake(s)
        r.sendall(b"\x01\x01x")
        start = time.monotonic()
        s.request({"other_shell": True})
        assert s.ping() < 500
        r.settimeout(7)
        eof(r)
        elapsed = time.monotonic() - start
        assert 4.5 < elapsed < 6
        log(case="assembly_deadline", elapsed_ms=round(elapsed * 1000, 3))
        # Raw subscription changes, without client-side reference-count coalescing.
        r = handshake(s, "iopub", kind="SUB")
        for prefix in [b"", b"probe", b"probe"]:
            r.sendall(frame(b"\x01" + prefix))
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["subscriptions"]
                == 2
            )
        )
        s.request({"publish": 1}, s.control)
        f, b = receive(r)
        assert b == b"probe"
        receive(r)
        r.sendall(frame(b"\x00probe"))
        r.sendall(frame(b"\x00"))
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["subscriptions"]
                == 1
            )
        )
        s.request({"publish": 1}, s.control)
        assert receive(r)[1] == b"probe"
        receive(r)
        r.sendall(frame(b"\x00probe"))
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["subscriptions"]
                == 0
            )
        )
        r.close()
        log(case="subscription_reference_counts", passed=True)
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["routes"] == 0
            )
        )
        slow = handshake(s, "iopub", kind="SUB")
        slow.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
        slow.sendall(frame(b"\x01"))
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["subscriptions"]
                == 1
            )
        )
        slow_generation = endpoint(s, "iopub")["identities"][0]["generation"]
        fast = s.new(zmq.SUB, "iopub")
        fast.setsockopt(zmq.SUBSCRIBE, b"")
        s.until(
            lambda v: (
                next(e for e in v["endpoints"] if e["name"] == "iopub")["subscriptions"]
                == 2
            )
        )
        fast_generation = next(
            i["generation"]
            for i in endpoint(s, "iopub")["identities"]
            if i["generation"] != slow_generation
        )
        count = [0]
        done = threading.Event()

        def drain():
            while not done.is_set():
                if fast.poll(20):
                    fast.recv_multipart()
                    count[0] += 1

        t = threading.Thread(target=drain)
        t.start()
        try:
            before = s.stats()["pub_send_ok"]
            s.request({"publish": 1000, "paced": True}, s.control)
            during = []
            for i in range(8):
                start = time.monotonic()
                s.request({"during_publication": i}, s.control)
                during.append((time.monotonic() - start) * 1000)
                assert during[-1] < 500 and s.ping() < 500
                time.sleep(0.03)
            assert s.stats()["pub_send_ok"] < before + 1000
            s.until(lambda v: v["pub_send_ok"] >= before + 1000)
            until = time.monotonic() + 2
            while count[0] < 1000:
                assert time.monotonic() < until
                time.sleep(0.005)
            ids = [i["generation"] for i in endpoint(s, "iopub")["identities"]]
            assert fast_generation in ids and slow_generation not in ids, ids
            s.request({"publish": 1}, s.control)
            until = time.monotonic() + 2
            while count[0] < 1001:
                assert time.monotonic() < until
                time.sleep(0.005)
            assert fast_generation in [
                i["generation"] for i in endpoint(s, "iopub")["identities"]
            ]
            start = time.monotonic()
            s.request({"control": True}, s.control)
            ms = (time.monotonic() - start) * 1000
            assert ms < 500 and s.ping() < 500
            log(
                case="paced_pub_with_continuity",
                control_during_max_ms=max(during),
                fast_generation=fast_generation,
                slow_generation=slow_generation,
                received=count[0],
                control_ms=round(ms, 3),
                stats=s.stats(),
            )
        finally:
            done.set()
            t.join(5)
            fast.close(0)
            slow.close()
        s.until(lambda v: v["publication_reserved"] == 0)
    finally:
        s.close()
    s = Server(empty=True)
    try:
        s.request({"empty": True})
        log(case="empty_key", passed=True)
    finally:
        s.close()


if __name__ == "__main__":
    run()
