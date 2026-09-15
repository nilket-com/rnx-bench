# Record 0048 prototype — 2026-09-15

Plan `1f689be` preceded implementation. Source: `probes/jupyter-zmtp`, with its
own lockfile and five Rust tests. **0048 is not accepted for adoption; 0047
remains stopped.** No production rnx code changed.

## Required client gate fails

The pinned environment reports Python 3.14.4, pyzmq 27.2.0, jupyter_client 8.10.0
and libzmq 4.3.5. The server advertises 3.0, and the client's greeting advertises
3.1. NULL/READY complete and the client sends a 3.0 prefixed subscription:
`01 70 72 6f 62 65` (subscribe to probe). Ordinary publications work.

With HEARTBEAT_IVL=100 ms, the same client then sends command body
`04 50 49 4e 47 00 00`: PING with zero TTL and empty context. The server's
bounded parser records this body and closes the unsupported-command connection,
as the current record requires. No silent ignore or PONG extension was added.

`heartbeat-stop.jsonl` and `heartbeat-stop-confirmation.jsonl` reproduce the
failure, including greeting/READY/subscription byte traces and the command in
last_failure. The corresponding stderr files preserve the assertion. The
confirmation uses session-ID identities for its DEALER sockets. Exit status 1
is expected and recorded in `exit-status.json`. Both runs confirm cleanup.
This contradicts the assumption that advertising 3.0 suppresses client PING;
it does not by itself establish whether to implement an extension or narrow
accepted client settings. That is the next reviewed decision.

## Independent diagnostic coverage

`diagnostic-no-heartbeats.jsonl` and `diagnostic-confirmation.jsonl` explicitly
turn off the client heartbeat setting and exit zero. This is not a workaround
counted as passing the required gate. The initial `transport.jsonl` contains
boundary observations before command tracing was added; its run stopped at the
same heartbeat assertion. The confirmation files describe the final sources.

What passed in the implemented tests:

- Signed exchanges on shell/control/stdin, additional routing frames, wrong-key
  silence, empty-key mode and binary REP heartbeat.
- Split greeting/READY, 32-part acceptance and 33-empty-part refusal, 64/65
  metadata properties, duplicate names, and 1 MiB versus 1 MiB+1 payloads.
- Declared lengths 1 MiB+1, u32::MAX, u64::MAX-1 and u64::MAX refused without a
  body. Rust unit tests verify credit release and checked header handling.
- Declared/anonymous IDs, live duplicate refusal, reconnect after retirement,
  and a declared zero-prefixed name forcing generated-ID collision handling.
- Eight connections with a ninth refused, roughly two-second handshake and
  five-second assembly deadlines, and subscription reference-count changes.
- Reply/publication preflight unit tests, and released credits after shutdown.

The former 32 MiB unfinished-part attempt now encounters connection closure.
The 32-part cap applies before the 1 MiB cap for its 8 KiB parts. The sender can
write additional bytes into TCP buffers before observing closure: confirmation
sent 917504 bytes, which is not the amount retained by the server. Sampled RSS
was 4018176 before and 4132864 after, not a measured peak. Do not interpret that
small difference as a proved total memory bound.

The unpaced PUB flood delivered some data to the reading subscriber and control
remained responsive (confirmation 0.265 ms). However both subscribers had closed
by its final snapshot. That observation does not pass the sustained-healthy-peer
gate; the fixture needs a paced workload with verified connection continuity.
Other outstanding coverage includes all aggregate-bound combinations,
connection-level delayed stale replies, all pending teardown states, independent
allocation accounting and throughput/latency characterization. These are
unpassed gates, not silently removed requirements.

## Build and scope

Five Rust tests pass. Rust formatting and Python undefined-name checks pass.
The Windows MSVC target type-checks, with its log preserved, but was not run.
A fresh-target offline release build took 5.37 seconds. Compiler/platform
versions, package licence declarations, binary/source hashes and build logs
are alongside this file. Licence declarations are not finished notices.
No libzmq or C++ build is in the server graph. Library dependencies shown by
ldd and the binary sizes are evidence for this prototype, not kernel costs.

The prototype stops for protocol review. Neither 0047 nor 0048 is marked
implemented; there is no kernel installation, browser capture or production
process change. rnx's full suites were not rerun for this isolated probe.
