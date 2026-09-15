# Record 0048 heartbeat extension and completed prototype gates

Measured on nano/Linux, 2026-09-15, after plan revision `29f6fda`.
Prototype sources are `probes/jupyter-zmtp`; reproduce with its `run.sh`.
Both complete wire-fixture passes exit zero with client heartbeats enabled.
Eleven Rust tests, formatting and Windows MSVC type checking pass. This is
ready for review, not automatic adoption into 0047 or Windows execution.

## Heartbeat contract

RFC 37 permits 16 context bytes and a two-byte TTL. Including the name-length
byte and name, PING is 7–23 body bytes; PONG is 5–21. The proposed 22 bytes
"after the name" was corrected in the plan before implementation. The parser
caps the command before allocation and checks the exact grammar afterward.
PONG uses the connection's bounded writer; valid inbound PONG and TTL are
ignored. Interleaved commands do not reset the data-message deadline. No
other 3.1 features are advertised or silently accepted.

The original PING failure and its traces remain under `jupyter-zmtp-0048/`.
The new raw/client checks cover empty and 16-byte context, 17-byte refusal,
short TTL, malformed names, oversized declared command, ignored PONG/TTL,
idle heartbeat traffic beyond six seconds, and PING inside an unfinished
multipart. The latter closes at its five-second lifetime; the client's
150 ms polling cadence makes observation slightly later (confirmation 5159.828
ms, within the stated 4.5–6 s observation interval). No timer is extended.

## Gate map

| Requirement | Evidence |
| --- | --- |
| Short/long framing, header splits, coalescing, truncation, invalid flags | Rust parser tests plus byte-split wire handshake |
| Length checked before narrowing/allocation | u64::MAX and u64::MAX-1 header-only wire refusals; unit credit assertions |
| Frame/multipart 1 MiB and 32 parts | exact/excess wire and unit cases, including 33 empty parts |
| Handshake 8 KiB, 64 properties, identity 255 bytes | exact/excess wire cases; duplicate/unknown metadata and invalid greeting cases |
| Eight slots per endpoint | eight accepted, ninth refused; all five endpoints simultaneously full |
| Incoming 8 MiB per endpoint / 40 MiB total | three repeated forty-connection cycles, allocator totals and RSS |
| Completed inbound message ceiling | no extra completion queue: one retained message per connection, at most eight per endpoint, structurally below 64 |
| Subscription 128 prefixes, 256 bytes, 65535 references | unit endpoints/excess; raw reference-count and filtering checks |
| Reply/publication byte and entry limits | unit exact/excess capacities, current-write credit, and failed atomic fanout after partial reservation |
| 16 MiB total publication obligations | eight subscribers holding two 1 MiB capacities each; overflow/failure and full release |
| Declared/anonymous/reconnected identities | wire tests, generated collision injection, independent endpoint registries |
| Stale pending reply | actual blocked writer, old connection retired, same name reconnects under a new generation and receives only its own reply |
| Slow subscriber isolation | paced run with original reading generation preserved, all messages and final marker received |
| Control/heartbeat fairness | checks during unfinished input, pending paced publication and a finite 10000-PING flood |
| Absolute handshake/assembly/write deadlines | wire handshake/assembly checks; Rust partial-progress writer deadline test |
| Cancellation/teardown | wire shutdown during greeting, READY, frame length, body, multipart and blocked writer; unit partial-write/current-plus-queue release |
| Whole shutdown | all fixture final snapshots show zero connection/route/payload/publication credits; task records retain their slot until joined |

The stronger eight-message structural bound does not require adding a 64-entry
queue just to fill it in a test. If integration adds such a queue, ownership
credits and the 64-entry limit must be preserved there. See `accounting.md`
for the source-side ownership argument and distinctions from total RSS.

## Selected confirmation observations

- Reading subscriber generation 32 survived; stalled generation 31 retired.
  All 1000 paced publications plus the final marker arrived on the reader's
  original connection. Control calls made while publication was still pending
  took at most 0.994 ms in the confirmation. The producer requested a 2 ms
  pause per message; this is a tested offered load, not peak throughput or a
  promise of lossless delivery at arbitrary rates.
- Forty simultaneous 1 MiB retained payloads held 42,304,648 requested Rust
  allocation bytes in the later cycles, including overhead. After each cycle,
  requested live allocation returned to 116,696 bytes. Largest single request
  was 1,048,576 bytes. RSS was measured separately (roughly 44–45 MiB while
  full). These are measured values, not a fixed process-wide memory ceiling.
- The blocked old reply had 250499 wire bytes. Reconnecting moved from generation
  4 to 5; no old reply appeared. Shutdown of a blocked writer completed in 4.415
  ms in the confirmation, within the five-second bound.
- The 100 signed-echo samples averaged 0.433 ms, maximum 1.329 ms. These are
  local fixture observations, not a kernel startup benchmark. Transport-ready
  timings are also recorded separately at process launch.

Exact values from both passes are in `summary.json` and the raw JSONL files.

## Corrections found during completion

One aggregate repetition sampled allocator totals before all closing task drops
were reflected, although the later-sampled payload counters were zero. Stats
are not an atomic cross-thread snapshot. `early-snapshot-failure.txt` preserves
that failure. The fixture now awaits both zero counters and allocator quiescence
within the original five-second bound, then checks stability over three cycles.
No timeout was removed or increased.

Source inspection also found that completed JoinSet records could outlive their
admission permits. The listener now retains each permit in a bounded map until
that task is joined, including failed tasks. Thus churn cannot grow completed
records outside the connection cap. All final runs use that correction.

## Scope and provenance

`run.sh` rebuilds, runs the Rust suite, runs both wire fixtures twice and records
exit codes. The final four exits are zero. Initial intermediate files (`writer`,
`aggregate-quiescence`) document focused checks; the confirmation files and
hash manifest identify the final sources. Compiler/client versions, Windows
check, clean-build timing, package licence declarations and hashes are preserved.
The clean build ran separately from the latency stage; no before/after speedup
is asserted. Declarations are not a final distribution notices audit.

No root-rnx code or dependency changed, so its suites were not rerun. No kernel
was installed, no notebook screen gate passed, and Windows was not executed.
The prototype closes its previous command-compatibility stop; 0047 still needs
a reviewed integration decision and its own kernel acceptance gates.
