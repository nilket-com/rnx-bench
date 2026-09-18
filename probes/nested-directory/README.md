# 0065 F2: observe directories once, then measure the unchanged gate

The accepted first stop is retained at rnx 2bf4871 / bench fc30b5c. This iteration
implements only F2's per-directory collection and no-nesting independent path.
It fixes the floor but stops on the first-adapter increment. No gate threshold or
post-measurement implementation is changed.

Prerequisites and timing protocol are the accepted nested-product README's. Keep
its targets and results: run.py copies those drivers, changes only the outer path
assignment and result directory, then executes the effective driver saved here.
The same fixtures, seeds, 4500-sample protocol and 360 fallback samples run.
The oracle, mutation and same-process assertions are unchanged.

```sh
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project-assembly-probe
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/run.py replay
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/run.py checks
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/run.py measure
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/run.py fallback
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/trace.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-directory/collect.py
```

Finish builds/checks before timing. Preserve results before reruns; replay needs
target/matrix and target/extra absent. Measure needs target/baseline, target/format,
target/reuse and samples.jsonl absent. Fallback needs fallback-samples.jsonl absent
and refuses if the accepted source fixture already has an adapter target directory.
It creates and removes only its own 4097 ignored files there; no other consumer
may use that fixture concurrently. No global cache or runtime entries are removed.

The initial wrapper changed both its outer assignment and an inner substitution
needle, making the generated replay driver resolve its target under results and
refuse before tests. It now changes the outer assignment once. No assertion changed.

The 4500 headline samples span 75 cells (two repeats, 30 observations per cell),
with 360 fallback samples separate. The zero-adapter gate passes; all six first-
adapter mode/repeat increments fail the 1 ms bound. Later increments pass.
Trace.py runs after timing and records statx/ENOENT counts, not traced latency,
for the same one-native lock on the format-only, previous stopped and F2 tools.

The root narrative names remaining gate-5 work and the stop. collect.py preserves
the current source/binary identities and patch from 2bf4871. The signed root commit
preserves measured source; content hashes alone are not a source archive.
