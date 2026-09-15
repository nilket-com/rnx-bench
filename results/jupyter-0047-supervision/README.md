# Record 0047: integrated Linux supervision, 2026-09-15

Measured on nano with Rust 1.98.1. This is the next implementation step after
rnx `4b5fa0a`, not completion of record 0047. Exact source and release binary
hashes are in `source-and-binary-sha256.json`; the source was uncommitted while
measured. The adjacent implementation commit contains that source. Commands and
Python package versions are preserved in `exit-status.json` and `versions.txt`.
Reproduce with `bash probes/jupyter-supervision/run.sh` from the bench root.

All four supervision fixtures pass twice. Both original 0048 wire fixtures pass
twice against the same extracted transport/library (under `wire/` and
`wire-confirmation/`). Both kernel test configurations pass 22 tests. The
separately run root suites pass sequentially under TERM=xterm-256color: 344
and 385 tests. Their full outputs and counts are preserved. Formatting and both
notices checks pass. The kernel's notices now include jiff, used for message
UTC dates. Root source, manifest, lockfile and notices remain byte-identical to
4b5fa0a; `root-isolation.json` records this and the single root workspace member.

## What the fixtures establish

Persistent values, unit silence, compile/runtime diagnostics, retained and
redefined closure origins, immutable parent headers, silent/count/history
choices and unsupported user expressions all pass through real jupyter_client.
The working directory differs from the connection-file directory and is kept.
Colon commands remain source. A requested restart ends the old kernel; a newly
launched kernel has a different session id, counter 1 and no old bindings.

A flushed progress line arrives before its 500 ms sleep completes (400 ms gate).
Unflushed partial text arrives byte-exact at the barrier. Split valid UTF-8 is
preserved; invalid and incomplete bytes become U+FFFD with metadata. Both streams
retain 2,097,152 bytes and report exactly 360,448 discarded from 300 writes of
8,192 bytes, then a subsequent cell succeeds. The component tests exercise every
barrier split, stale identity/nonce text, NUL and a partial marker prefix.

With one active input, 70 small queued requests produce six KernelBusy replies.
Six 900,000-byte inputs produce two; six 140,000-NUL inputs also produce two,
proving admission charges escaped serialized payload rather than only decoded
source. Over-cap source is refused without echoing it as execute_input. Queued
requests after a stop_on_error failure are aborted without execution/counts;
new requests remain usable, and stop_on_error=false permits the next request.

Synchronous-loop, awaited-sleep and supervised-child interrupts settle and allow
another cell, under a one-second gate. Logged elapsed times begin before the
control interrupt request, not process startup. Async CPU work still does not
settle within the fixture's 150 ms observation after interrupt; shutdown forces
it down in about 1.018 seconds, inside the five-second kernel deadline and the
client's 5.5-second tolerance. This is not a new cooperative interrupt capability.

The kernel itself discovers and reaps the escaped double-fork descendant on
shutdown and worker death. The fixture independently checks its PID is gone;
those PIDs are never supplied to the kernel. Observations are about 32–33 ms
for shutdown and 16–17 ms after worker death. No Windows cleanup claim follows.

Blocked stream and result handoffs fail in 5.001–5.003 seconds, within the
4.9–6-second fixture gate, with no ack recorded. Sending another settlement
every two seconds cannot renew the deadline. Partial stderr barriers and
malformed settlements cause WorkerDied/nonzero exit, with no execute_result,
successful idle or acknowledgement. These use the production Worker API and a
feature-gated external example; the serving binary has no fault-injection switch.

The private nbclient kernelspec executes cells, captures text and a named error,
saves `executed.ipynb`, and reopens it successfully. It changes no user kernelspec
and provides no JupyterLab screenshot or installer evidence.

## Bound ownership and remaining work

Transport payload credits remain attached until callbacks finish. The separately
admitted execution queue charges full serialized bytes before copying, retains
credit for the active request, and has no extra unbounded inbound channel. The
control collector holds at most eight parsed 256-KiB-bounded replies plus its
current frame; parsed allocation overhead is not equated to serialized size.
Each stream keeps a 2-MiB operation buffer plus a separate 2-MiB lifetime late
buffer, bounded marker lookbehind and fixed-size reads/publications. Late bytes
are attributed at collection time; causal ambiguity during another operation is
unchanged from 0046. Publication credits include queued and writing messages.

The ordered publishing owner performs bounded synchronous transport admission,
not frontend delivery. Stream/result/error/reply/idle handoff occurs before
acknowledgement. Shutdown uses one deadline from the first shutdown request;
waiting for the shutdown reply to reach the socket does not grant another five
seconds. Duplicate requests cannot refresh it. The worker has one reaper; Linux
startup checks subreaping, /proc discovery and pidfd signalling before spawning.

Windows cross-check succeeds for portable code plus the explicit unsupported
launcher, **not Windows worker supervision**. Other-platform containment,
kernelspec installation, actual JupyterLab operation/screens and ready/cold/warm
benchmark comparisons are still open. Size/hash/linked-library output describes
this serving build but does not claim a clean build time or startup performance.
The shared parent-death change remains outside this implementation. Hard kernel
death cannot run a Linux sweep, and OS-uninterruptible work can defeat cleanup.
