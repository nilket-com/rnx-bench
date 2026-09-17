# 0058 gate 1: native Polars boundary and scoped engine-thread rerun

This is a prototype, not adapters/polars. It registers four real native types
through rnx's public Extensions interface, with a fixed three-row frame and fixed
CSV schema. No product API or root runtime change is hidden here.

The accepted stop is preserved in commit 2c4a278 and
results/polars-boundary-0058: direct collect panics inside current-thread Tokio
execution, while synchronous eval and session controls pass. The current probe
implements the revised call-owned scoped-thread boundary and writes separate
results/polars-engine-thread-0058 evidence. The old results are not overwritten.

```
cargo build --release --locked --offline --manifest-path probes/polars-boundary/Cargo.toml
python3 probes/polars-boundary/check.py --threads 1
python3 probes/polars-boundary/check.py --threads 2
cargo test --locked --offline --manifest-path probes/polars-boundary/Cargo.toml
cargo clippy --locked --offline --all-targets --manifest-path probes/polars-boundary/Cargo.toml -- -D warnings
```

The initial dependency fetch is online (`cargo fetch --manifest-path ...`). Run
Cargo commands serially in the same target directory. All fixtures reap their
processes and use private temporary files, never a user's data.

engine.rs moves owned Send engine inputs to a fresh plain scoped thread and joins
it before returning. The prototype routes collect, CSV reads and fixture-frame
materialization through that function; pure plan/expression construction and
bounded inspection stay on the caller. Rune wrappers are constructed on the
caller, and no Rune reference/value crosses the thread boundary. Every engine
thread asserts Handle::try_current fails. The probe directly names the already
resolved Tokio dependency solely for that assertion: graph-check.json proves
no new package, feature or version was resolved.

Counters distinguish engine-thread start, finish and join, active and maximum
active calls, and absence of a Tokio context. Nested engine work starts its own
scoped thread, then joins before the outer engine call continues. A separate pair
of engine calls uses a barrier to ensure both are alive before either collects.
The combined nested/overlap/error case must return both answers and exact counts
(5 started, 5 finished, 5 joined, 0 active, max at least 2, 5 context checks).
A Rust unit test catches the resumed panic only after the engine thread is joined;
production-style returned errors are separately gated from Rune. Spawn failures
are handled fallibly by source review, not forced through resource exhaustion.

The driver repeats four runtime controls: frame construction in run, collect in
run, collect in synchronous eval, collect in async-promoted eval. All must exit
zero with empty stderr. It then preserves the original registration/reuse/ADD/
error-recovery checks. CSV observations now run through file execution too.

The live session is sampled before collection, after it, while idle, after another
collect and after reset. Before returning to the prompt, engine counters must be
balanced. Polars' own persistent threads/event descriptors are reported separately
and can outlive reset; they end with process exit. No notebook, async cancellation
or performance acceptance is inferred from these observations.

CSV probes compare supplied schema, dtype overrides, inferred header names and
reading the first record as strings with has_header=false and n_rows=1. Only the
last preserves duplicate raw names. Production must validate and rewind the same
regular-file handle before typed reading; the prototype does not implement that
entire contract or claim consistent snapshots under concurrent file mutation.
The bounded observer is not the full preview formatter. Parquet remains gate 2.

Original provenance lives in results/polars-boundary-0058. Its private venv has
Python polars 1.44.2, while the native crate is 0.55.2 at a different source
revision. The original provenance.py records wheel hashes, compares installed
.py/.so bytes to the downloaded wheels, and inventories resolved licences. Use
its accepted commit to reproduce that historical graph; the rerun inherits those
identities and records the single direct dependency edge added for instrumentation.
There is no matched-engine boundary-performance claim or product redistribution
notices claim. A persistent adapter engine thread remains a later optimisation.
