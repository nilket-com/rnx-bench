# 0059 stage two: metadata default and explicit full verification

Prerequisites are the accepted Polars gate-five project/cache and the old
ordinary tool from 48831ec at probes/project-run-stage/target/before. The accepted
stage-one ordinary tool is saved at this directory's ignored target/stage-one;
rebuild 347acd8 in isolation there if reproducing on a fresh checkout. Never use
the new tool under those labels. Hashes of every measured binary are recorded.

From rnx-bench, build the current ordinary release and debug test-support tool:

```sh
cargo build --locked --release --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
python3 probes/project-run-default/contracts.py
python3 probes/project-run-default/inventory.py
python3 probes/project-run-default/measure.py
```

Preserve results/project-run-default-0059 before rerunning; it is tracked evidence.
Stage new rnx inputs before real project lock/build, and do not edit rnx during
measurements. The scripts never need a user kernelspec, database or project.
The preexisting PostgreSQL workflow separately uses a throwaway cluster.

contracts.py builds a tiny API-compatible Rust fixture in a temporary Git tree.
It tests product CLI orchestration, not Rune evaluation: flags/forwarding, version
migration, zero/full artifact read counts, mismatch and identical replacement,
source edits with restored timestamps, failed/interrupted refresh, changed-during-
verification refusal and overrides. Count and pause hooks exist only under
test-support. Unit tests check intentionally undetected same-size/restored-time
artifact corruption using inert bytes, never executing malformed machine code.
Both default acceptance and --verify refusal are asserted there. The actual
Polars example and PostgreSQL workflow provide the real application controls.

measure.py compares old, intermediate stage-one, new default, --verify and direct
in two interleaved repeats of twenty samples per workload/product (400 total).
All launches are ordinary release binaries without test support or profiling.
Every output/status/stderr is checked, and a journal retains every sample.
Old tools receive a valid v1 receipt and current tools a valid v2 receipt for the
same artifact/lock; preparing those bytes is outside timing. That prevents
migration from masquerading as a repeated default-launch cost. All public/source
inputs and the artifact are identical within the comparison. Output-directory
setup and lock/build are outside timing. CPU affinity and one Polars thread are
fixed before launch; caches are warm, both workloads warmed, no samples dropped.

Legacy migration, metadata mismatch and first override establishment are measured
separately, five observations each. Overrides declare an executable rather than
native source packages and therefore do not incur the native-source inventory;
their number must not be labelled as the generated project's migration time.

inventory.py creates an isolated copy of the current tool with clocks around Git,
native tree reads/hashing and ancestor audit, plus their inclusive parent interval.
It adds one stderr record before exec and does not change validation. Child groups
are disjoint; their parent total is not added to them. The remaining setup is the
parent minus children. Twenty paired profile/control launches are separate from
the acceptance timings. Full instrumented files are retained. The measured
native-tree bucket includes metadata/open/read work and both required tree/content
digests, not just SHA throughput. No inventory policy has changed.

Tool tests/clippy/format/notices and Windows type-check logs are retained. Windows
execution is not claimed and product commands still refuse without supervision.
The old sixteen-group workflow and real PostgreSQL fixture passed; their tracked
0057 results were restored after the rerun. Source patch and hashes identify the
measured implementation before evidence/README edits; recorded local locks are
snapshots, not reusable locks for a later checkout.
