# 0057 gate 6: regression and cost

The root suites run serially with `TERM=xterm-256color` and
`--test-threads=1`: default, test-support, and
test-support + server-runtime + project-sources. Tool tests and clippy run in
both feature configurations. Logs include the root packaged-manifest gates,
notices, default-graph comparison, formatting and Windows MSVC type checks.
Windows commands still refuse; a successful type check is not execution.

Build stock release binaries from 07f6709 and the accepted gate 5 tree in
separate target directories with `cargo build --release --locked --offline`.
Record their absolute paths and SHA-256 hashes in results/project-regression-0057/
build.json. `compare.py` checks exact exit/stdout/stderr for unchanged CLI cases.
`startup.py` uses hyperfine's no-shell mode, CPU 4, ten warmups and 100 samples
per binary, with before/after then after/before order. Run it without other
builds or tests active. It measures stock commands, never project verification.

Build the ordinary project tool with:

```
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/project-regression/project_cost.py
```

The cost fixture requires the accepted package-assembly plain and words fixtures.
It assembles real rnx plus PostgreSQL and plain extensions, with a mapped Rune
package. No database is involved in its timed expression. The first build starts
with an empty target directory but cached registry sources, offline. The warm
build follows it immediately, with no copied compilation cache. The run comparison
uses the same generated artifact and explicit source map on each side. Project
run additionally verifies input trees, lock, receipt, artifact and capability;
the difference is total verification/launch overhead, not SHA-256 alone.
The run clock includes Python spawn/wait on both sides and is kept separate from
the hyperfine stock measurements. Builds are wall-clock observations, not a
statistical estimate of compile speed. All generated files stay under ignored
target directories. Do not edit rnx during the project build: its complete tracked
root is part of the native fingerprint.

Run `summarize.py` after all fixtures to derive the counts and medians and
assert baseline Clippy/graph equality. Stored text logs have trailing whitespace
removed; JSON samples and diagnostic content are unchanged. Root Clippy currently
fails on the same pre-existing findings in both trees. The full root Windows
check requires an MSVC native toolchain absent here; the tool check succeeds.
