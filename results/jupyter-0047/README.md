# Record 0047: pre-implementation gates

Measured by Codex on nano/Linux, 2026-09-14. Both probes reached a stop condition.
No kernel implementation or user kernelspec installation followed them.

## Transport

`transport.jsonl` is the first run and `transport-confirmation.jsonl` the rerun.
The Rust probe uses locked zeromq 0.6.0, hmac 0.13.0 and sha2 0.11.0; complete
versions/features/declared licences are in `rust-packages.json`, `rust-features.txt`
and the probe's Cargo.lock. Python packages are frozen in
`probes/jupyter-transport/requirements.txt` (jupyter_client 8.10.0, pyzmq 27.2.0,
nbclient 0.11.0, JupyterLab 4.6.3, Playwright 1.62.0).

| observation | confirmation run |
| --- | --- |
| signed exchange, extra identity/fields | passed |
| wrong signature | no dispatch or reply |
| empty-key exchange | passed |
| malformed multipart / extra binary buffer | application refused |
| PUB send with nobody subscribed | 50 successful sends, no recipient |
| unread subscriber | 61 sends then one timeout/error at the 250 ms probe bound |
| control / heartbeat during that interval | 1.215 / 0.567 ms |
| incoming 4 MiB vs 1 MiB application cap | 4,194,313-byte allocation before refusal |
| 9-byte length header, zero body bytes | 67,108,967-byte allocation request |

The last row announced a 64 MiB frame on the probe's own loopback connection.
This is a bounded counterexample, not an exhaustion measurement. The allocator
instrument measures the largest allocation request, not RSS or total live memory.
The two runs reproduced the same sizes. The application sees neither a completed
message nor a signature to verify before this reservation. The locked codec source
and its lack of configurable frame/multipart caps explain it; file hashes and
locations are in `source-audit.json`.

This fails the planned transport-bound gate. Positive interoperability does not
justify proceeding around it. PUB send cancellation/reuse and full kernel
message handling are not certified by the simple fixture.

## Containment

`containment.jsonl` and `containment-confirmation.jsonl` use the actual 0046 rnx
release and a process::run timeout of 2,000 ms. Ordinary deadline expiry and
cooperative interruption end the child group. After a hard worker kill, a child
is still alive 2.5 seconds later. The same is true when SIGINT was first queued
to a stopped worker. In the confirmation run, a setsid descendant is also alive
past that deadline after an otherwise successful cooperative interruption.

The wait deadline belongs to host.rs's supervisor loop inside the worker. It is
not an OS timer in the launched child. The permitted 90,000 ms maximum therefore
does not bound a survivor after the supervisor dies. The child fixture's own
30-second sleep is not evidence of any remaining rnx enforcement. Linux subreaper
mode lets the harness adopt and explicitly kill/reap its owned survivors; both
traces record successful cleanup. No Windows execution claim is made.

This fails the containment gate. A reviewed containment mechanism or an explicit
change to the guarantee is needed; interrupt-first alone cannot satisfy it.

## Scope and reproduction

Commands are in the two probe READMEs. The clean-target offline release build
used cached crate downloads and took 8.12 s, with maximum build RSS 525,956 KiB.
`binary.json` describes the standalone transport fixture, not a kernel binary.
`planned-browser.json` records the pinned Chromium revision selected by Playwright;
it has not been downloaded or exercised. The eventual screen gate is headless
Chromium driving a real JupyterLab page. No screenshot or notebook result is
claimed yet. The production rnx source was not changed, so its full suites were
not rerun for these external probes.
