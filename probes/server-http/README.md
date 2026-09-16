# 0054 gate 3: HTTP before a server API

Measured by Codex on Linux, 2026-09-16, against the archived rnx revision in
`results/server-http-0054/run-{0,1}/conditions.json`. This is a **private
prototype**, not a server command or public factory. Gates 4–6 (HTTP scheduling
measurements, transaction integration and database shutdown) remain separate.

```sh
python3 probes/server-http/build.py
python3 probes/server-http/wire.py --output results/server-http-0054/run-0
python3 probes/server-http/wire.py --output results/server-http-0054/run-1 --signal TERM
```

Run from rnx-bench. The build archives the exact rnx HEAD in a temporary directory,
adds `probe.rs` as a private cfg(test) module and adds server-only dev dependencies
there. It never edits the rnx checkout. The locked graph, including features and
edges, is `graph.json`; `Cargo.lock` pins it. The first build needed network for
httpdate, which the client graph did not use. Subsequent builds use locked,
offline resolution. Hyper 1.11.1, hyper-util 0.1.20 and http-body-util 0.1.5 are
unchanged versions from the root graph; httpdate 1.0.3 and tokio-macros 2.7.2
are additional packages. `ADDITIONAL-NOTICES.md` contains their shipped licences.
The archive retains rnx's existing notices. No binary is checked in.

The Rust test executable runs only `server_http_probe::server`; Python drives
actual TCP sockets without an HTTP client normalizing the bytes. `build.json`
is a local build receipt, not checked in; each result directory copies its
hashes, source revision, exact build command and manifest into `conditions.json`.
`results.json` holds asserted wire observations; `events.jsonl` holds admission,
VM, teardown, response, socket and sampling events. `memory.json` is an independent
10 ms `/proc` RSS/descriptor sample. These files include fixture logging overhead
and are not gate 4 performance measurements. No database is started or contacted.

## Ownership and bounds exercised

One shared compiled Rune Unit, two worker threads with current-thread runtimes
and LocalSets, four charged active credits per worker, and one central FIFO of
sixteen complete requests. A fresh real-battery context is built on its worker
for each handler. HTTP state, lifecycle and RuntimeContext are per handler.
The coordinator has its own runtime and never runs a VM. Worker inboxes hold
only the already charged four active credits: they are not additional admission
queues. A bounded eight-entry completion channel returns those credits after
logical teardown. JoinSets reap completed tasks and worker tasks are capped at
four, so their handle collections cannot become another completed-work queue.
One oneshot reply belongs to each connection; closed receivers drop late results.

The four POST routes are `/healthy` (byte echo), `/await` (ten-second await),
`/cpu` (a whole-budget loop), and `/fail` (a Rune panic). The last is deliberately
**not** a transaction test; gate 5 must integrate that owner. Query switches under
`/healthy` supply malformed responses, header bounds, raw-header echo and a
fixed 2.5-second blocking native call. They are test instrumentation, not framework
API. That native call is labelled separately from the CPU-budget cases.

The prototype uses the exact plan limits: 32 connections; 16 KiB parser buffer;
64 request fields; 8 KiB target; 1 MiB counted body; 16 queued plus 8 active;
1 MiB response body; and 64 fields/16 KiB name+value bytes on the response wire.
For the last bound, validation conservatively reserves three fields for
Connection, Content-Length and Hyper's Date, and their byte charges. This leaves
61 handler fields. The fixture proves 64 wire fields and exactly 16,384 wire
header name/value bytes, and refuses the next handler field/byte. It reserves
Date even if a handler supplies one itself. Protocol syntax (colons and CRLF)
is not charged to the application byte account. The head parser's own buffer
also includes wire syntax, and can refuse a head before its application header
byte allowance is exhausted. A status such as 204 may omit framing fields on
wire; the reservation remains conservative.

HTTP/1.0 receives 505; only 1.1 is supported here. Each connection serves one
request and closes. There is no compression, upgrade, pipeline execution, TLS,
public bind, implicit HEAD or path decoding. The parser owns framing. The fixture
also sends a second request after a declared body and proves it is never run.
Response length assertions parse Content-Length: searching response bytes for
`HTTP/1.` would mistake those bytes in a body for another response.

Absolute clocks are 5 s from accept for the head, 5 s from valid head for body,
2 s from complete body for admitted work, and 1 s from response dispatch for a
write. The clock fixtures allow 4.7–6.5 s for a nominal 5 s event and 1.8–3 s for
the admitted deadline. A 5 ms coordinator tick detects signals and reaps queued
cancellations. Write-deadline checks also use that cadence. These tolerances
separate the tested clock from no deadline or a fresh timeout for every byte.

The ordinary CPU loop returns budget failure (500), not 504, in the recorded
runs. A rejection is timestamped inside an observed CPU execution interval,
proving the coordinator actually progressed during the loop. The separate
native-stall case returns 504 near 2 s while its active credit survives to about
2.5 s. A queued request behind occupied native polls expires without building a
context. None of these outcomes claims native-call preemption or a universal
wall-clock bound on a CPU budget under arbitrary OS contention.

Both disconnect fixtures use RST deliberately, so they test **detected**
disconnect, not how quickly the network reveals a silent peer. Cancellation
removes queued payloads and revokes/drops the running owner; teardown events
must arrive before the two-second timeout could explain their disappearance.

## Parser and memory evidence

The wire corpus includes fragmented and silent heads, slow bodies, oversized
heads/targets/field counts, false and conflicting lengths, a Content-Length near
2^63, a declared chunk length of 2^62, overflowing chunk lengths, 10,000 tiny
chunks, over-cap chunk data, oversized cumulative chunk extensions, and ordinary
and oversized trailers. Parsed trailers refuse. Hyper's pinned decoder also
caps trailer bytes at 16 KiB and applies the configured trailer field count;
chunk extensions have a cumulative 16 KiB limit. The exact parser/decoder/I/O
source hashes are in the receipt. These source facts complement the wire tests;
a builder setting alone is not the evidence.

Three receive batches each hold 32 incomplete bodies, one byte short of 1 MiB,
without building any context, then disconnect all peers. The fixture records
tracked live allocations and RSS while held and after release, and asserts
idle tracked allocation falls below 1 MiB. Forty enormous declared lengths per
batch are rejected without allocating from that declaration. The observed held
allocation is about 51.5 MB, **not 32 MiB**: Vec growth, parser state and other
allocations are real. Idle RSS need not return to startup because allocators keep
pages. Neither these observations nor the logical caps bound arbitrary VM/native
allocation or the kernel's socket buffers.

A slow-write fixture sets SO_SNDBUF to 16 KiB on accepted sockets and uses a tiny
client receive window, forcing real write backpressure for the capped 1 MiB
response. This is an explicit test injection, selected by
`RNX_HTTP_SMALL_SEND_BUFFER=1`, and is recorded in conditions. A normal OS send
buffer can accept the whole response before that write deadline; the wire test
must not claim it exercised a blocked write merely because its client did not
read. The slow-reader result requires an observed `write deadline` event.

## Signals, shutdown and limits of this gate

The existing rnx SIGINT handler remains in place; the coordinator polls its
flag. No tokio SIGINT listener replaces it. A separate Linux SIGTERM handler
sets the prototype's shutdown flag. Run 0 exits through SIGINT, run 1 through
SIGTERM. The stock test in `results/server-http-0054/stock-interrupt.txt`
executes the existing synchronous-session interrupt test with test-support
and requires one test, not a zero-test feature-disabled invocation.

On teardown the prototype cancels owners, drops queued requests, disposes
connection tasks, awaits handler tasks, then drains each worker runtime only
after its owners end. It joins both worker threads and asserts zero socket
FDs, zero charged active slots, zero connection permits, zero runtime tasks,
and equal context construction/retirement counts. Python waits for exit and
joins its monitor. Failure cleanup kills/reaps the fixture process group.

This gate proves transport/admission and the idle end of the fixture, not the
whole gate-6 shutdown matrix. In particular it has no SQL backend or pending
rollback, and it does not prove rollback-before-credit-return. It also does not
publish a factory, choose a pool, measure steady-state HTTP throughput, promise
CPU preemption, execute on Windows, or establish isolation from trusted native
code. Those remain in 0054's later gates and server-entry decision.
