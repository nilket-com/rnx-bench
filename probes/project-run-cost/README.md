# Project run cost attribution, before the 0059 design

Run from rnx-bench after the accepted 0058 Polars project fixture exists:

```sh
python3 probes/project-run-cost/prepare.py
python3 probes/project-run-cost/measure.py
```

Both write `results/project-run-cost-0059`; preserve recorded evidence before
rerunning. The ignored target directory owns the instrumented tool source and
build. Preparation archives only the committed `tools/project` package from rnx,
adds timers in that copy and builds with its unchanged lockfile, offline. No
product source changes. The archive revision and binary/lock hashes are recorded.
Preparation reuses its previous build cache. Normal Cargo dependencies must
already be cached, as must the gate-five Polars fixture and its generated project.

The measurement refreshes that fixture's lock/build with the stock tool outside
timing, since rnx documentation edits invalidate native path fingerprints. It
uses the same generated artifact and inputs for all three launches: stock tool,
instrumented tool and generated-direct. Twenty samples per workload/product,
two fixed-seed interleaved repeats: 240 total. Every output, exit and stderr
contract is checked. A per-sample journal retains all completed observations.
Both workloads are warmed; all launches use one pinned allowed CPU and one
Polars thread. No samples are removed. No cold-cache or durability-throughput
claim is made. This is the same warm-launch scenario as 0058.

Instrumentation uses disjoint Instant intervals around groups of existing work.
No filesystem, digest, identity, validation or error branch is skipped. It emits
one JSON line to captured stderr just before exec. Stock launches have no such
output. Paired total times measure whether instrumentation changed the result
materially. The timer vector, serialization, startup/argument handling, some
small equality checks and exec/spawn/wait overhead are outside the named groups;
the phase sum is not claimed to cover every nanosecond. No timer is inside a
hashing or file-read loop. The full instrumented files and a diff are preserved.
An unused emit helper warning occurs only in the copy's library target; the
instrumented product binary uses it. Neither is a shipped tool modification.

The native_inventory interval includes Git enumeration, ancestry/config audit
and working-tree hashing, not solely SHA throughput. Artifact fingerprinting
includes its regular-file/path checks, read and digest work. Map publication
includes encoding, writing, fsync, rename and directory fsync. Do not describe
any of these intervals as a measurement of one syscall or hash instruction.

No cache policy has been adopted. This probe supplies measurements for a draft;
it does not implement a fast mode or waive 0057 verification rules.
