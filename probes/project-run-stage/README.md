# 0059 stage one: ordinary launches with full verification

This is the product implementation of single-file hashing and validated-map
reuse, before the metadata default. No artifact check is skipped. The accepted
before executable is saved in ignored target/before and its hash is compared
with the accepted attribution probe's stock-tool hash in the original run.

For a fresh reproduction, build tools/project from rnx 48831ec in an isolated
checkout/archive and copy its ordinary release rnx-project to target/before.
Build today's ordinary tool with cargo build --release --locked --manifest-path
../rnx/tools/project/Cargo.toml --bin rnx-project. Existing cached Polars gate-five
project/assembly inputs are prerequisites. Stage new rnx source files so the
Git-tracked native input inventory can see them; do not edit rnx during the run.

Run `python3 probes/project-run-stage/measure.py` from rnx-bench. Preserve the
results/project-run-stage-0059 directory before rerunning: it is tracked evidence.
Setup refreshes the private example's project lock/build outside the timer. Both
product tools validate the same fresh locks, artifact and source contents.

Two warm interleaved repeats, 20 samples per product/workload, one pinned CPU
and one Polars thread. All 240 samples are checked for output/status/stderr and
journalled. No samples are dropped. The external clock measures ordinary process
spawn/capture/wait; no profiling clock runs in these binaries. Map inode/mtime
are sampled outside timing around after launches to prove no publication occurred.
The script uses private fresh output directories and never overwrites user data.

Outside timing, a same-size in-place artifact edit with restored mtime must still
refuse by hash before any script output. A finally restores the original byte and
timestamps and checks the whole digest. An incorrect derived map must be replaced
from the lock, after which the ordinary script runs. Those controls distinguish
this stage from a metadata-only fast path and a filename-only map cache.

The implementation's shared-reader tests cover content/allowance equivalence and
injected growth/early EOF between metadata and read. Map publication counters live
only in unit-test closures. Ordinary executable observation uses filesystem
identity, not a product test hook. The unreadable-file test is exercised as the
non-root user; root would bypass mode checks and that branch is explicitly noted.

The accepted 0057 workflow check is replayed through the changed debug/test-support
binary; original tracked results are restored after saving changed observations
here. It covers public file layout, no Cargo during run, stale/tampered inputs,
publication failures, interrupts, relocation and overrides. Two earlier assembly
integration tests stay ignored in the tool suite; this evidence does not count
them as passed. The real Polars product lock/build/run is the integration here.
