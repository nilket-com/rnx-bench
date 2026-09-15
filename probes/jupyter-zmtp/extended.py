#!/usr/bin/env python3
"""Remaining 0048 fixture cases; private harness, not a notebook adapter."""

import json, pathlib, socket, struct, time
from probe import (
    Server,
    handshake,
    frame,
    receive,
    raw_request,
    eof,
    endpoint,
    log,
    rss,
)


def settled(s):
    return s.until(
        lambda v: (
            all(e["incoming_reserved"] == 0 for e in v["endpoints"])
            and v["publication_reserved"] == 0
        )
    )


def heartbeat_cases():
    s = Server()
    raws = []
    try:
        for n in (0, 16):
            r = handshake(s)
            raws.append(r)
            context = bytes(range(n))
            r.sendall(frame(b"\x04PING\xff\xff" + context, command=True))
            f, b = receive(r)
            assert f == 4 and b == b"\x04PONG" + context
            r.sendall(frame(b"\x04PONG" + context, command=True))
            raw_request(s, r, {"pong_ignored": n})
            r.close()
        for b in (
            b"\x04PING\0",
            b"\x04PING\0\0" + b"x" * 17,
            b"\x04PONG" + b"x" * 17,
            b"\x04PANG\0\0",
        ):
            r = handshake(s)
            r.sendall(frame(b, command=True))
            eof(r)
        r = handshake(s)
        r.sendall(b"\x06" + struct.pack(">Q", 2**64 - 1))
        eof(r)
        log(
            case="heartbeat_body_boundaries",
            ping_body_max=23,
            pong_body_max=21,
            context_max=16,
            passed=True,
        )
        r = handshake(s)
        raws.append(r)
        start = time.monotonic()
        pings = 0
        while time.monotonic() - start < 6.2:
            r.sendall(frame(b"\x04PING\0\x01", command=True))
            assert receive(r)[1] == b"\x04PONG"
            pings += 1
            time.sleep(0.22)
        raw_request(s, r, {"idle_heartbeat_survives": True})
        r.close()
        log(
            case="idle_heartbeat_and_ignored_ttl",
            elapsed_ms=round((time.monotonic() - start) * 1000, 3),
            pings=pings,
        )
        r = handshake(s)
        raws.append(r)
        r.sendall(frame(b"a", more=True))
        start = time.monotonic()
        pings = 0
        while True:
            try:
                r.sendall(frame(b"\x04PING\0\0", command=True))
                assert receive(r)[1] == b"\x04PONG"
            except (ConnectionResetError, BrokenPipeError, AssertionError):
                break
            pings += 1
            time.sleep(0.15)
            assert time.monotonic() - start < 6.5
        elapsed = time.monotonic() - start
        assert 4.5 < elapsed < 6
        r.close()
        log(
            case="interleaved_pings_do_not_extend_assembly",
            elapsed_ms=round(elapsed * 1000, 3),
            pings=pings,
        )
        # Measured latency, with no claim that these few samples are a benchmark distribution.
        timings = []
        for i in range(100):
            begin = time.monotonic()
            s.request({"latency": i})
            timings.append((time.monotonic() - begin) * 1000)
        log(
            case="signed_echo_latency",
            samples=100,
            mean_ms=sum(timings) / len(timings),
            max_ms=max(timings),
        )
        r = handshake(s)
        raws.append(r)
        r.sendall(frame(b"\x04PING\0\0", command=True) * 10000)
        start = time.monotonic()
        s.request({"during_ping_flood": True}, s.control)
        control = (time.monotonic() - start) * 1000
        assert control < 500 and s.ping() < 500
        r.close()
        log(
            case="finite_ping_flood_fairness",
            pings_sent=10000,
            control_ms=round(control, 3),
        )
        settled(s)
    finally:
        for r in raws:
            r.close()
        s.close()


def aggregate():
    s = Server()
    raws = []
    try:
        s.ctx.destroy(linger=0)
        s.until(lambda v: all(e["connections"] == 0 for e in v["endpoints"]))
        records = []
        for cycle in range(3):
            before = s.stats()
            start = time.monotonic()
            for name, kind in [
                ("shell", "DEALER"),
                ("control", "DEALER"),
                ("stdin", "DEALER"),
                ("hb", "REQ"),
                ("iopub", "SUB"),
            ]:
                for _ in range(8):
                    r = handshake(s, name, kind=kind)
                    raws.append(r)
                    r.sendall(frame(b"x" * 1048576, more=True))
            held = s.until(
                lambda v: all(
                    e["incoming_reserved"] == 8 * 1048576 for e in v["endpoints"]
                )
            )
            assert sum(e["connections"] for e in held["endpoints"]) == 40
            assert held["allocation_live"] < 40 * 1048576 + 2 * 1048576, held[
                "allocation_live"
            ]
            assert held["largest_allocation"] <= 1048576
            for name in s.address:
                host, port = s.address[name].removeprefix("tcp://").split(":")
                extra = socket.create_connection((host, int(port)), timeout=5)
                eof(extra)
            held_rss = rss(s.p)
            for r in raws:
                r.close()
            raws.clear()
            # Stats sample allocator totals before endpoint counters: not an atomic
            # snapshot. Await completed task drops as well as released payload credits.
            after = s.until(
                lambda v: (
                    all(
                        e["connections"] == e["routes"] == e["incoming_reserved"] == 0
                        for e in v["endpoints"]
                    )
                    and v["allocation_live"] < 1024 * 1024
                )
            )
            assert after["allocation_live"] < 1024 * 1024
            records.append(
                dict(
                    cycle=cycle,
                    elapsed_ms=round((time.monotonic() - start) * 1000, 3),
                    before_live=before["allocation_live"],
                    held_live=held["allocation_live"],
                    after_live=after["allocation_live"],
                    peak_allocated=held["allocation_peak"],
                    held_rss=held_rss,
                    largest=held["largest_allocation"],
                )
            )
        assert (
            max(r["after_live"] for r in records)
            - min(r["after_live"] for r in records)
            < 128 * 1024
        )
        log(case="forty_connections_40MiB_and_recovery", cycles=records)
    finally:
        for r in raws:
            r.close()
        s.close()


def shutdown_states():
    # Each state is established independently, then server stop occurs with it pending.
    for state in ["greeting", "ready", "frame_length", "frame_body", "multipart"]:
        s = Server()
        r = None
        try:
            if state in ["greeting", "ready"]:
                host, port = s.address["stdin"].removeprefix("tcp://").split(":")
                r = socket.create_connection((host, int(port)), timeout=5)
                if state == "ready":
                    g = bytearray(64)
                    g[0] = 255
                    g[9] = 127
                    g[10] = 3
                    g[12:16] = b"NULL"
                    r.sendall(g)
                else:
                    r.sendall(b"\xff")
            else:
                r = handshake(s, "stdin")
                r.sendall(
                    {
                        "frame_length": b"\x02\0",
                        "frame_body": b"\x02" + struct.pack(">Q", 1048576) + b"x",
                        "multipart": frame(b"x", more=True),
                    }[state]
                )
            s.until(
                lambda v: (
                    next(e for e in v["endpoints"] if e["name"] == "stdin")[
                        "connections"
                    ]
                    == 1
                )
            )
            start = time.monotonic()
            s.close()
            elapsed = (time.monotonic() - start) * 1000
            assert elapsed < 5000
            log(case="shutdown_pending_" + state, elapsed_ms=round(elapsed, 3))
        finally:
            if r:
                r.close()
            if s.p.poll() is None:
                s.close()


def pending_writer(s, identity):
    r = handshake(s, identity=identity)
    r.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
    content = {"big": "x" * 250000}
    for n in range(40):
        parts = s.session.serialize(s.session.msg("probe_request", content=content))
        r.sendall(b"".join(frame(p, i < len(parts) - 1) for i, p in enumerate(parts)))
        time.sleep(0.01)
        ids = endpoint(s, "shell")["identities"]
        old = next((i for i in ids if i["id"] == identity.hex()), None)
        assert old is not None, ids
        if old["writing"]:
            time.sleep(0.04)
            again = next(
                (
                    i
                    for i in endpoint(s, "shell")["identities"]
                    if i["id"] == identity.hex()
                ),
                None,
            )
            if again and again["writing"]:
                return r, again
    r.close()
    raise AssertionError("failed to establish a pending writer")


def stale_reply_and_writer_shutdown():
    for mode in ["reconnect", "shutdown"]:
        s = Server()
        r = None
        try:
            r, old = pending_writer(s, b"delayed-reply")
            assert old["writing"] > 0
            if mode == "reconnect":
                r.close()
                s.until(
                    lambda v: all(
                        i["id"] != b"delayed-reply".hex()
                        for e in v["endpoints"]
                        if e["name"] == "shell"
                        for i in e["identities"]
                    )
                )
                r = handshake(s, identity=b"delayed-reply")
                raw_request(s, r, {"only_new_reply": True})
                new = next(
                    i
                    for i in endpoint(s, "shell")["identities"]
                    if i["id"] == b"delayed-reply".hex()
                )
                assert new["generation"] != old["generation"]
                r.settimeout(0.15)
                try:
                    extra = r.recv(1)
                    raise AssertionError(("stale reply", extra))
                except socket.timeout:
                    pass
                log(
                    case="pending_reply_not_retargeted",
                    old_generation=old["generation"],
                    new_generation=new["generation"],
                    old_write_bytes=old["writing"],
                )
                r.close()
                s.close()
            else:
                start = time.monotonic()
                s.close()
                elapsed = (time.monotonic() - start) * 1000
                assert elapsed < 5000
                log(
                    case="shutdown_pending_writer",
                    elapsed_ms=round(elapsed, 3),
                    write_bytes=old["writing"],
                )
        finally:
            if r:
                r.close()
            if s.p.poll() is None:
                s.close()


def handshake_boundaries():
    s = Server()
    try:
        for n in [8192, 8193]:
            r = handshake(s, props=[(b"X", b"x" * (n - 34))])
            if n == 8192:
                raw_request(s, r, {"ready_max": True})
                r.close()
            else:
                eof(r)
        r = handshake(s, identity=b"x" * 255)
        raw_request(s, r, {"identity_max": True})
        r.close()
        r = handshake(s, identity=b"x" * 256)
        eof(r)
        r = handshake(s, props=[(b"X-unknown", b"\0\xff")])
        raw_request(s, r, {"unknown_metadata": True})
        r.close()
        for bad in ["version", "mechanism", "as_server"]:
            host, port = s.address["stdin"].removeprefix("tcp://").split(":")
            r = socket.create_connection((host, int(port)), timeout=5)
            from probe import exact

            exact(r, 64)
            g = bytearray(64)
            g[0] = 255
            g[9] = 127
            g[10] = 3
            g[12:16] = b"NULL"
            if bad == "version":
                g[10] = 2
            if bad == "mechanism":
                g[12:17] = b"PLAIN"
            if bad == "as_server":
                g[32] = 1
            r.sendall(g)
            eof(r)
        log(case="ready_identity_and_greeting_boundaries", passed=True)
    finally:
        s.close()


if __name__ == "__main__":
    heartbeat_cases()
    aggregate()
    shutdown_states()
    stale_reply_and_writer_shutdown()
    handshake_boundaries()
