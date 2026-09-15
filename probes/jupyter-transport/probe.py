#!/usr/bin/env python3
"""Local interoperability and bounded-size counterexamples; not a kernel."""

import json, pathlib, queue, socket, struct, subprocess, threading, time
import zmq
from jupyter_client.session import Session

ROOT = pathlib.Path(__file__).resolve().parent
TIMEOUT = 5


def log(**v):
    print(json.dumps(v), flush=True)


class Server:
    def __init__(self, empty=False):
        self.errors = open(
            ROOT
            / "../../results/jupyter-0047"
            / ("empty-stderr.txt" if empty else "transport-stderr.txt"),
            "w",
        )
        self.p = subprocess.Popen(
            [
                str(ROOT / "target/release/jupyter-transport-probe"),
                *(["empty"] if empty else []),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.errors,
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
        r = s.request(
            dict(value=42, extra="tolerated"), prefix=b"extra-routing-envelope"
        )
        log(
            case="signed_roundtrip",
            header_version=r["header"]["version"],
            extra_routing_identity_preserved=True,
            heartbeat_ms=s.ping(),
        )
        before = s.stats()
        bad = s.session.serialize(s.session.msg("probe_request", content={}))
        bad[1] = b"0" * 64
        s.shell.send_multipart(bad)
        after = s.until(lambda v: v["bad_signature"] > before["bad_signature"])
        assert not s.shell.poll(100)
        log(
            case="wrong_signature",
            no_reply=True,
            accepted_unchanged=after["accepted"] == before["accepted"],
        )
        for name, frames in [
            ("short_multipart", [b"<IDS|MSG>", b""]),
            (
                "binary_buffer",
                s.session.serialize(s.session.msg("probe_request", content={}))
                + [b"unsupported"],
            ),
        ]:
            n = s.stats()["rejected"]
            s.shell.send_multipart(frames)
            s.until(lambda v: v["rejected"] > n)
            assert not s.shell.poll(50)
            log(case=name, refused=True)
        before = s.stats()
        s.request(dict(publish=50), s.control)
        after = s.until(lambda v: v["pub_send_ok"] >= before["pub_send_ok"] + 50)
        log(
            case="pub_without_subscriber",
            send_calls_succeeded=50,
            subscriber_count=0,
            delivery_not_proven=True,
        )
        sub = s.ctx.socket(zmq.SUB)
        sub.setsockopt(zmq.LINGER, 0)
        sub.setsockopt(zmq.RCVHWM, 1)
        sub.setsockopt(zmq.RCVBUF, 1024)
        sub.setsockopt(zmq.SUBSCRIBE, b"probe")
        sub.connect(s.address["iopub"])
        until = time.monotonic() + TIMEOUT
        while True:
            s.request(dict(publish=1), s.control)
            if sub.poll(50):
                assert sub.recv_multipart()[0] == b"probe"
                break
            assert time.monotonic() < until
        before = s.stats()
        s.request(dict(publish=20000), s.control)
        time.sleep(0.6)  # observation window, not a delivery handshake
        start = time.monotonic()
        s.request(dict(control="responsive"), s.control)
        control_ms = (time.monotonic() - start) * 1000
        after = s.stats()
        log(
            case="unread_subscriber",
            additional_send_ok=after["pub_send_ok"] - before["pub_send_ok"],
            timeouts_or_errors=after["pub_send_timeout_or_error"]
            - before["pub_send_timeout_or_error"],
            control_ms=round(control_ms, 3),
            heartbeat_ms=s.ping(),
        )
        sub.close(0)
        # A bounded counterexample, not an exhaustion test: only 4 MiB is sent.
        before = s.stats(reset=True)
        s.shell.send(b"x" * (4 * 1024 * 1024))
        after = s.until(lambda v: v["rejected"] > before["rejected"])
        assert after["largest_allocation_request"] >= 4 * 1024 * 1024
        log(
            case="application_limit_is_late",
            application_limit=1024 * 1024,
            payload_bytes=4 * 1024 * 1024,
            largest_allocation_request=after["largest_allocation_request"],
            rejected_after_receive=True,
        )
        # Header-only counterexample: the peer has not provided its claimed body.
        raw = raw_dealer(s.address["shell"])
        try:
            s.stats(reset=True)
            announced = 64 * 1024 * 1024
            raw.sendall(b"\x02" + struct.pack(">Q", announced))
            after = s.until(lambda v: v["largest_allocation_request"] >= announced)
            log(
                case="length_header_reserves_before_body",
                wire_bytes_after_handshake=9,
                announced_body_bytes=announced,
                body_bytes_sent=0,
                largest_allocation_request=after["largest_allocation_request"],
                heartbeat_ms=s.ping(),
                stop_condition="receive allocation is not bounded by application checks",
            )
        finally:
            raw.close()
    finally:
        s.close()
    s = Server(empty=True)
    try:
        s.request(dict(empty_key=True))
        log(case="empty_key_roundtrip", passed=True)
    finally:
        s.close()
    log(cleanup="both servers exited zero and all sockets closed")


if __name__ == "__main__":
    run()
