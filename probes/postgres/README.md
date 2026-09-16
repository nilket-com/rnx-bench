# 0052 ownership prototype — stopped before the adapter

Codex, nano/Linux, 2026-09-16. Uses rnx at `aee1d83` (plan `cb4f519`),
tokio-postgres exactly 0.7.18, and PostgreSQL 18.6. No product adapter exists yet.

```sh
cargo build --locked --release --manifest-path probes/postgres/ownership/Cargo.toml
PYTHONDONTWRITEBYTECODE=1 python3 probes/postgres/ownership.py
```

The final command **exits 2 intentionally** when it reproduces the retained-
binding stop condition. It starts its own initdb cluster in a mode-0700
TemporaryDirectory, with no TCP listener. All queries use that Unix socket.
Finally it stops the server, verifies its PID disappeared and removes the
cluster. It never uses the system server. Requires PostgreSQL binaries under
`/usr/lib/postgresql/18/bin` and Linux `/proc`.

The executable uses the real rnx library/worker, not a Rust stand-in for Rune.
`pg_probe::query(url, seconds, timeout_ms, refuse)` is prototype-only. It opens
one connection, drives its Connection future alongside the statement future
inside that single host future, and streams one integer result. There is no
spawn. The synthetic conversion refusal occurs after receiving a real row;
it tests destruction, not the final adapter's type conversion contract.
The public runtime Handle retained by the trace guard only lets that guard
record task counts even when the future is dropped outside block_on. It does
not poll, spawn, drain, abort or advance the runtime.

The parent proves a socket opened and the server query became active before
letting each cleanup case pass. It reads `/proc/<worker>/fd` after settlement
and **before acknowledgement or another input**. Parent sleeps/psql monitoring
do not turn the worker's runtime. `connected`/`dropped` trace lines contain the
Tokio task count and process socket count. Successful destruction records zero
tasks and baseline sockets. The existing HTTP drain returns without block_on
when its task count is zero, as verified in rnx's execute.rs.

Seven cases pass:

1. Completed query.
2. Deadline caught in Rune with match.
3. Refused conversion after receiving a row.
4. SIGINT during a pending query.
5. A bound, started future raced through Rune select, then left unpolled while
   the script sleeps, then discarded by a panic in that same input.
6. The same held-future window followed by a loop exhausting the worker's real
   two-billion-instruction budget. No synthetic Rust budget replaces it.
7. Laziness: a successful input binds an unawaited future; no socket opens.

The pending-drop and budget cases prove their new binding was not published,
but only after the pre-next-input descriptor check. The stderr observation
marker includes padding: the parent stream collector withholds a possible
barrier prefix. A shorter marker was visible only at the final barrier, which
made the first fixture incorrectly miss the observation window. The fixture
now observes the real open socket while the script is sleeping after select.

The eighth case exposes the limitation:

- Input 1 successfully retains `q = pg_probe::query(...)`, still unpolled.
- Input 2 selects between q and a timer. The fixture observes the query active
  and interrupts the worker.
- Input 2 settles as interrupted, but the *same socket inode* remains open.
  The old session binding still owns q. There are no spawned tasks and no
  `dropped` event. HTTP's drain cannot release it.
- In the final run the query has a 600 ms statement timeout. After a passive
  800 ms parent wait, without an ack/input/runtime turn, the socket is still
  open and the backend has become idle. Server timeout does not free the
  client's unpolled future or close an otherwise-live session.

`results/postgres-0052/ownership.json` is the final run; `ownership-first.json`
is an earlier complete reproduction with a 90-second server timeout in the
retained case. `ownership-cleanup.json`, build/clippy logs, binary hash and
resolved graph make provenance explicit. No benchmark or whole-adapter gate
is claimed by these observations.

This proves call-owned connections are cleaned up **when the host future is
actually dropped**, but interruption of a Rune execution does not always drop
that future. Record 0052 requires a lifecycle decision before adapter work:
a registration-only extension cannot cancel resources retained by earlier
session bindings on its own. A later lifecycle interface or an explicit
contract change needs review. No extra runtime turn, forced reset, or detached
worker is used to make the stop condition pass.
