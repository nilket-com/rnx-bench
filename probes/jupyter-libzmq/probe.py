#!/usr/bin/env python3
"""Local interoperability and bounded-size counterexamples; not a kernel."""

import json, pathlib, queue, socket, struct, subprocess, threading, time
import zmq
from jupyter_client.session import Session

ROOT = pathlib.Path(__file__).resolve().parent
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
        self.errors = open(
            ROOT
            / "../../results/jupyter-0047-replacement"
            / ("empty-stderr.txt" if empty else "transport-stderr.txt"),
            "w",
        )
        self.p = subprocess.Popen(
            [
                str(ROOT / "target/release/jupyter-libzmq-probe"),
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


def run():
    s = Server()
    try:
        log(
            case="native_version",
            version=s.address["libzmq"],
            frame_limit=1048576,
            hwm=64,
            linger=0,
            address_space_limit=512 * 1024 * 1024,
        )
        r = s.request({"value": 42, "extra": "kept"}, prefix=b"extra-routing-envelope")
        log(
            case="signed_roundtrip",
            version=r["header"]["version"],
            heartbeat_ms=s.ping(),
        )
        before = s.stats()
        bad = s.session.serialize(s.session.msg("probe_request", content={}))
        bad[1] = b"0" * 64
        s.shell.send_multipart(bad)
        s.until(lambda v: v["bad_signature"] > before["bad_signature"])
        assert not s.shell.poll(100)
        log(case="wrong_signature", no_reply=True)
        for name, frames in [
            ("short", [b"<IDS|MSG>", b""]),
            (
                "extra_buffer",
                s.session.serialize(s.session.msg("probe_request", content={}))
                + [b"buffer"],
            ),
        ]:
            before = s.stats()
            s.shell.send_multipart(frames)
            s.until(lambda v: v["rejected"] > before["rejected"])
            log(case=name, refused=True)
        # Oversized declared frame is disconnected without sending its body.
        raw = raw_dealer(s.address["shell"])
        before = rss(s.p)
        raw.sendall(b"\x02" + struct.pack(">Q", 64 * 1024 * 1024))
        assert raw.recv(1) == b""
        log(
            case="oversized_header",
            declared=64 * 1024 * 1024,
            body_sent=0,
            peer_eof=True,
            rss_before=before,
            rss_after=rss(s.p),
        )
        raw.close()
        # Finite, capped counterexample: 4096 legal 8 KiB frames, no final part.
        raw = raw_dealer(s.address["shell"])
        try:
            baseline = s.stats()
            base_rss = rss(s.p)
            frame = b"\x03" + struct.pack(">Q", 8192) + b"x" * 8192
            for stage in (1, 2):
                raw.sendall(frame * 2048)
                time.sleep(0.2)  # observation window, not a delivery guarantee
                stats = s.stats()
                current = rss(s.p)
                start = time.monotonic()
                s.request({"other_peer": stage})
                shell_ms = round((time.monotonic() - start) * 1000, 3)
                start = time.monotonic()
                s.request({"control": stage}, s.control)
                log(
                    case="unfinished_multipart",
                    parts_sent=2048 * stage,
                    body_bytes=8192 * 2048 * stage,
                    application_parts_delta=stats["parts_received"]
                    - baseline["parts_received"],
                    rss_before=base_rss,
                    rss_now=current,
                    rss_growth=current - base_rss,
                    other_shell_peer_ms=shell_ms,
                    control_ms=round((time.monotonic() - start) * 1000, 3),
                    heartbeat_ms=s.ping(),
                )
                baseline = (
                    s.stats()
                )  # exclude our complete shell/control requests in next delta
            before = s.stats()
            raw.sendall(b"\x00\x00")
            after = s.until(lambda v: v["rejected"] > before["rejected"])
            log(
                case="final_part_releases_message",
                application_parts_delta=after["parts_received"]
                - before["parts_received"],
                rejected=True,
            )
        finally:
            raw.close()
        # Both real subscribers confirm subscription by receiving before the flood.
        slow = s.new(zmq.SUB, "iopub")
        slow.setsockopt(zmq.SUBSCRIBE, b"probe")
        slow.setsockopt(zmq.RCVHWM, 1)
        fast = s.new(zmq.SUB, "iopub")
        fast.setsockopt(zmq.SUBSCRIBE, b"probe")
        for sub in (slow, fast):
            end = time.monotonic() + 5
            while True:
                s.request({"publish": 1}, s.control)
                if sub.poll(50):
                    sub.recv_multipart()
                    break
                assert time.monotonic() < end
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
            before = s.stats()
            s.request({"publish": 20000}, s.control)
            after = s.until(lambda v: v["pub_send_ok"] >= before["pub_send_ok"] + 20000)
            assert count[0] > 0
            log(
                case="slow_and_reading_subscribers",
                send_successes=20000,
                reading_peer_received=count[0],
                send_errors=after["pub_send_timeout_or_error"],
                heartbeat_ms=s.ping(),
                delivery_not_guaranteed=True,
            )
        finally:
            done.set()
            t.join(5)
            slow.close(0)
            fast.close(0)
    finally:
        start = time.monotonic()
        s.close()
        log(
            case="native_shutdown",
            exit=0,
            elapsed_ms=round((time.monotonic() - start) * 1000, 3),
        )
    s = Server(empty=True)
    try:
        s.request({"empty_key": True})
        log(case="empty_key", passed=True)
    finally:
        s.close()


if __name__ == "__main__":
    run()
