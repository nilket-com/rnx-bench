# 0061 gate 5: two real Polars consumers, one shared assembly

Run from this repository with rnx beside it at the measured gate-4 revision
`3c4ed67`. No changes to product code or timing instrumentation. The fixture
creates its own cache under this probe's ignored `target/`; it never selects the
user's cache. Both project manifests use the installed native roots in `../rnx`.
Their different scripts print their own consumer marker and execute the shipped
CSV/filter/group/aggregate/sort/Parquet/read-back/repeated-collect pipeline.

```sh
cargo build --locked --offline --release --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/cache-polars/setup.py
python3 probes/cache-polars/journey.py
python3 probes/cache-polars/attach.py
python3 probes/cache-polars/measure.py
```

`setup.py` requires that its cache and two project directories do not exist.
For a new cold run retain or remove the **whole** previous `target/` only after
all its users have stopped. Moving it does not preserve the recorded cache
identity: this is preparation for a new build, not cache relocation. The Polars
dependency sources must already be available to Cargo; every Cargo command is
offline. The fresh entry target is never seeded or copied from another target.
The cold build uses the host's available CPUs; pinned launch and attachment
measurements run later without a compiler running.

The setup records first lock and cold compilation separately, then locks a second
project and attaches with Cargo compilation/metadata and rustc compilation trapped.
Three positive controls prove the traps fire; only `cargo -V` and `rustc -Vv` pass.
One entry, equal executable identity and differing project-lock digests are
asserted. The first attachment and ten further pinned attachments include full
artifact hashing and receipt publication; these are not everyday launch costs.

The journey drives both projects through a 120×30 xterm-256color PTY, retaining
frames and a lazy plan across inputs and a missing-column error, checking Parquet
readback, and resetting bindings without losing the extension. Eval output is
also compared with the direct artifact. Every terminal is quit and reaped.

The measurement fixes one CPU and `POLARS_MAX_THREADS=1` before spawn. Both
projects have pipeline, eval and spawn-to-first-prompt rows, each launched through
the metadata default, `--verify`, and the artifact directly. Two seeded interleaved
repeats of twenty observations per cell retain all **720 samples**. One warm-up per
cell is outside timing. Temporary output directory creation and cleanup are
outside the pipeline clock; every sample checks exact output and exit status.
The pipeline itself verifies its Parquet roundtrip and repeated collect. Sessions
time PTY setup/spawn through the exact first prompt, then quit and reap outside
that interval. There is no shell in the timed path. The 25 ms default-over-direct
gate is checked separately for each project, mode and repeat, after saving all
samples and summaries, including a failing measurement if one occurs.

Results: `results/cache-polars-0061/`. Setup includes manifests, scripts, lock
pairs, receipts, ready document, build logs and tool/artifact hashes. Machine and
timer conditions accompany raw samples. Directory bytes use `du` for the whole
entry (deduplicating hard-linked Cargo outputs); the file-wise subtotals are also
recorded, but may double-count those outputs. Keep assembly, target and artifact
together: the result is not an executable-only cache.

This gate measures product reuse, not hermetic or reproducible compilation,
source relocation, a `:dep` command, or an engine-speed comparison with Python.
Root regression and the remaining command regression sweep belong to gate 6.
