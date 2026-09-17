# 0058 gate 5: tiny Polars product costs

Run from rnx-bench on Linux. Native rnx inputs must remain unchanged during the
project build and measurements. All workspace state lives in ignored target/;
results/polars-cost-0058 is tracked evidence, so preserve it before a rerun.

```sh
python3 probes/polars-cost/setup.py
python3 probes/polars-cost/timing.py
probes/polars-cost/target/python/bin/python probes/polars-cost/ownership.py
python3 probes/polars-cost/provenance.py
python3 probes/polars-cost/summarize.py
```

Prerequisites: accepted ordinary rnx-polars and rnx-project release binaries,
Cargo's cached locked dependencies, uv and the exact gate-one cached wheels.
Setup refuses an existing cold target or Python venv. For a fresh setup rerun,
remove only this fixture's target/cold and target/python directories first.
Do not run setup, ownership, compilation or other benchmark drivers concurrently
with timing. The project and aligned controls may reuse their object caches.

Setup measures an empty target build with two jobs and cached downloads, a warm
build, private venv creation and installation from cached wheels. It is not a
network install measurement. The resulting cold-build binary hash equals the
ordinary accepted binary on this host; no cross-machine reproducibility claim.

The two programs expose init and pipeline modes. Init actually registers/imports
Polars and constructs a literal. Pipeline includes create-new CSV, raw-header
validation and same-handle rewind, explicit schema read, native filter/group/sum/
sort, collect, uncompressed create-new Parquet, flush/close, read-back, preview
comparison and a repeated collect. Both emit the same small text. Python's
row iteration is only the final two-row presentation, never a query UDF. No
upstream table formatter or arbitrary per-row compute callback enters the race.

Primary products: pinned Python 1.44.2, ordinary rnx-polars 0.55.2 and verified
rnx-project run. Generated-direct uses the exact project artifact, entry and
source map. Aligned-direct additionally builds the ordinary wrapper with
rnx/project-sources so its dependency versions/features equal the generated
assembly (excluding the two wrapper packages). The ordinary graph difference is
recorded, not silently removed from the primary comparison.

Timing pins one allowed CPU and one Polars thread before launch, warms both
workloads, and uses normal Python bytecode caching. Each of two repeats contains
30 samples for every product/workload, with fixed-seed interleaved order. The
clock surrounds no-shell subprocess spawn/capture/wait; assertions and fresh
output-directory creation/removal are outside it. A per-sample journal retains
observations even on an interrupted run. GNU time peak RSS uses three separate
launches per cell, includes native threads, and is not concurrent process-tree
RSS summation. No fsync durability is measured by the pipeline.

The preliminary first block disabled Python bytecode writes by inheriting a
correctness-fixture setting. It is retained under preliminary-no-bytecode and
excluded from the comparison. It was interrupted during the second block; only
the complete first block had been saved. The corrected driver journals each
sample and enables normal cached imports. No versions, native compiler flags or
thread counts were selected after inspecting which result won.

Provenance verifies exact wheel hashes and every installed Python/shared-library
code file against those wheels. The Python tag and Rust crate have different
engine revisions. Complete wheel compiler/allocator settings are not exposed by
build_info. Consequently this is a product launch comparison: boundary-only
attribution and matching allocator/CPU-dispatch claims remain unproved. Never
subtract the two workloads to label the difference VM or engine compute time.

Ownership is separate. A two-million-row CSV demonstrates tracked native
allocation and the sampled ceiling; /proc snapshots distinguish joined scoped
threads from Polars' persistent pool and prove no retained input file handle.
The collect probe observes the native engine thread still present after 50 ms
before signalling. A same-poll file completion retains success; an explicit
subsequent await observes the pending signal after collect returns. All children
have external deadlines, kill-and-reap cleanup, and recorded exit outcomes.
The observed signal latency is not a cancellation bound.

Tree fingerprint bytes and executable sizes/hashes are recorded separately.
Project verification cost includes the tool's inventory, hashing, map publication
and verified launch; it is not just a cost per source byte. Archived project locks
are local identities captured before later evidence edits and are not reusable
locks for another checkout.
