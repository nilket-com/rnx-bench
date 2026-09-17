# 0058 gate 2: product CSV and Parquet contract

Requires the gate-one private environment at
`../polars-boundary/.venv` (Python Polars 1.44.2 and runtime 1.44.2).
No global Python installation or user data is changed.

From rnx-bench:

```sh
cargo build --release --locked --manifest-path ../rnx/adapters/polars/Cargo.toml
probes/polars-boundary/.venv/bin/python probes/polars-contract/check.py
```

`--binary` overrides the ordinary product; `--output` selects a results directory.
The driver uses temporary inputs and outputs, subprocess deadlines, two Polars
threads and a clean rnx configuration environment. Run as an ordinary user for
the mode-000 unreadable-file case. It checks independent expected rows, Python
and Rune Parquet producers, all four dtypes/nulls, 16 CSV edge cases against the
pinned Python reader, repeated borrowed inputs after success/failure, empty
results, symlinks and named refusals. It neither times the pipeline nor claims
engine revision equivalence.

The two Rust file tests use the same private functions as production. One
replaces the pathname after raw-header validation, proving typed data comes
from the original open file after rewind. The other injects an actual writer
failure after 16 bytes, an engine flush failure and a final adapter flush
failure. It asserts retained files and refused retries, prints their sizes and
errors, then removes the fixture directory only after those observations.
Feature tests also prove panic join and no Tokio context on the engine thread.
Run these tests serially, with `--nocapture` to retain observations.

Saved results are evidence, not scratch space: use another `--output` directory
for an independent rerun or restore tracked results afterwards. Build feature
configurations serially; they share a target directory and executable name.
