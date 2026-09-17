# 0058 gate 1: native Polars boundary, stopped

This is a prototype, not adapters/polars. It registers four real native types
through rnx's public Extensions interface, with a fixed three-row frame and fixed
CSV schema. No product API, root runtime change, extra dispatch thread or runtime
switch is hidden here.

```
cargo build --release --locked --offline --manifest-path probes/polars-boundary/Cargo.toml
python3 probes/polars-boundary/check.py
```

The initial fetch is online (`cargo fetch --manifest-path ...`). The fixture
expects the current stop: direct native collect panics under rnx's current-thread
Tokio execution in a file and async-promoted eval. It captures that failure, then
runs independent synchronous controls. An unexpected success fails this fixture
and requires revising the evidence, not quietly passing the stopped design.

The synchronous control proves four-type registration, borrowed frame/plan/
group-by/expression and expression-array reuse, ADD returning an expression,
comparison methods, repeated aggregation/collection and error recovery. The
observer uses public per-column access with ten rows and eighty string characters;
it is not the product preview formatter. No Parquet or timing gate is claimed.

CSV probes compare supplying a schema, dtype overrides, inferred header names,
and reading the first record as string data with has_header=false and n_rows=1.
Only the last preserves duplicate names without deduplication. This offers a
same-parser header-validation route, not a second CSV parser; production must
validate and rewind the same regular-file handle before typed reading. File
mutation between passes would still not be an atomic snapshot guarantee.

The session remains alive between observations. /proc task/descriptor snapshots
are taken before first collect, after it, while idle, after the second collect
and after reset. No further input drives the idle observation. The two engine
threads and three event descriptors persist until process exit, as global engine
state. The fixture waits for and reaps every child. No notebook or async ownership
pass is inferred from these synchronous observations.

Provenance setup (private environment only):

```
uv venv probes/polars-boundary/.venv
uv pip install --python probes/polars-boundary/.venv/bin/python polars==1.44.2
python3 probes/polars-boundary/provenance.py
```

provenance.py downloads the exact matching wheels into an ignored directory,
checks PyPI SHA-256 digests, and compares installed Python/native code bytes to
the wheels. It records the resolved Cargo package/feature graph, SPDX declarations and hashes of common
licence filenames, the published Rust crate's VCS identity, Python tag identity
and both workspace manifests. This is a probe licence inventory, not complete
product redistribution notices. Python build_info supplies only a version;
matching-engine boundary attribution remains unproved.

All results are under results/polars-boundary-0058. Threads are pinned to two by
POLARS_MAX_THREADS in the native fixture; there are no performance measurements.
The initial build errors were fixture mistakes (Rune's function macro replaces
the callable name; Polars' current constructors/accessor names differ). They are
retained as such, not treated as engine incompatibilities. The runtime stop is
reproduced by the final compiled binary and its trace.
