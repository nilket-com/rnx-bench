# 0067 gate 4: one installed binary

This exercises the accepted product at rnx `7ae8863`, not an isolated candidate.
`setup.py` performs two real `cargo install --git ... --rev ... --locked` installs:
the published GitHub revision and a private fixture origin whose sole source
change is the repository URL. Only `rnx` is installed. The fixture checkout is
renamed before either user journey. `fixture.bundle` archives its commit against
the published revision; the normal replay creates its own local fixture revision.

Run from rnx-bench:

```sh
python3 probes/one-install/setup.py
python3 probes/one-install/journey.py published
python3 probes/one-install/journey.py fixture
python3 probes/one-install/selection.py
cargo build --manifest-path ../rnx/jupyter/Cargo.toml --release --locked --offline
probes/jupyter-notebook/.venv/bin/python probes/one-install/notebook.py
python3 probes/one-install/product-checks.py
python3 probes/one-install/check.py
```

Use a fresh **whole** `probes/one-install/target` and an absent
`results/one-install-0067` for a complete replay. Save any previous evidence before
moving those directories aside. Individual drivers deliberately refuse existing
caller, trap, result and document directories; they are not in-place resumable.
The two `journey.py` invocations can run concurrently. The recorded run did so;
its durations are observations, not cold-build or launch comparisons. Gate 5
owns matched timing. Installation shares a build target, and all Cargo homes use
a pre-existing registry cache; each journey starts with an empty **Git** cache and
an empty assembly cache. This is not a registry-download test.

Prerequisites: Rust/Cargo/Git, PostgreSQL 18 in `/usr/lib/postgresql/18/bin`,
bubblewrap with unprivileged user/network namespaces, strace, and the existing
Jupyter probe venv (`jupyter_client`, `nbformat`). No sudo, user kernelspec, user
runtime selection, or existing user assembly cache is used. Private PostgreSQL
clusters, PTYs and kernels are stopped by the drivers. The fixture and installed
artifacts remain under the ignored target for inspection.

Both origins prove decline/no writes, acquired coordinates, first Polars build,
same-PID handover, lost bindings with retained history, working directory,
CSV/Parquet pipeline, catchable error and retained frame, mixed Polars/Postgres
request, typed SQL, no-op requests, interrupt, reset, quit, EOF and a shell-executed
quoted scratch reopen command. A second stock session attaches offline inside a
network namespace with positive-tested Cargo/rustc compilation traps. Its file
trace proves the default does not consult a runtime store. Trace files are gzip
compressed losslessly; `journey.json` records the uncompressed trace hash.

`selection.py` installs a real retained runtime only *after* the no-store journey,
selects a nonexistent ID as a positive stale-store control, and proves stock Git
`:dep` ignores it with networking and compilation forbidden. It then explicitly
sets `RNX_DEP_RUNTIME` to the retained source and builds a real path assembly.
The stale selection stays unchanged. `notebook.py` installs the combined Git
artifact as a worker in a private kernelspec, tests errors and preview, restarts,
and saves a validated notebook. `check.py` archives the generated declarations,
lock pairs and receipts and checks that product sources match the checkpoint.

The normal user command is the published-origin install in `published-install.log`,
then `rnx`, `:dep polars`, and consent. There is no companion install or implicit
runtime-store installation on that path. A compiler/toolchain and native build
prerequisites are still required. The explicit path control deliberately retains
the older developer workflow; it is not a prerequisite for the default journey.
