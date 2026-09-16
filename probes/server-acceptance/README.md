# 0056 gates 5 and 6: example journey and stock isolation

Run from rnx-bench. PostgreSQL 18 tools and the cached locked Cargo graphs are
needed. The cluster helper owns a throwaway Unix-socket cluster and reaps it;
no system server is used.

```sh
# Build the ordinary standalone server if not already built by gate 4.
cargo build --locked --offline --release \
  --manifest-path ../rnx/servers/http-postgres/Cargo.toml \
  --target-dir ../rnx/servers/http-postgres/target/plain
python3 probes/server-acceptance/journey.py

# Builds must finish before timing; do not run timings alongside other probes.
python3 probes/server-acceptance/build.py
python3 probes/server-acceptance/compare.py --repeat 1
python3 probes/server-acceptance/compare.py --repeat 2
```

The journey runs the **ordinary** binary with the shipped `examples/app.rn`.
A separate persistent Python process owns all HTTP clients; the parent reads
server events only to arrange overlap. Each slow request must still be running
when a healthy request arrives and completes on the other worker. This is
asserted independently for an awaiting and a CPU-bound handler. A failed
transaction is observed absent from a second connection; two next borrowers
visit both workers and the failed request's backend is reused only after the
rollback acknowledgement. SIGTERM must end cleanly with matching context
counts, joined drivers and no owned sockets or tagged backends. The separate
client is joined, and the private postmaster is reaped.

The stock build fixture archives exactly `032579a`, then builds that archive
and current rnx in separate targets with identical locked/offline release
commands and no RUSTFLAGS overrides. It records hashes, sizes and compiler
version, compares the default normal/build dependency feature graph byte for
byte after replacing only the checkout path, checks unchanged lockfile bytes,
and verifies the root workspace contains only rnx.

The comparator checks exit status and **all stdout/stderr bytes** across 25
cases, including CLI refusals, runtime/compile diagnostics, a budget halt,
stream output, structures, arguments, session reset/renumber, and JSON. For
seven performance workloads it warms each binary eight times and runs ABBA
blocks twice, 20 samples per block, on one inherited CPU affinity. Each sample
includes process spawn and wait without a shell. Two repeats retain every raw
sample and block median; no threshold relabels a positive delta as a speedup.

The root suites run separately and sequentially under `TERM=xterm`:

```sh
cargo test --locked --offline
cargo test --locked --offline --features test-support
cargo test --locked --offline --features 'test-support server-runtime'
cargo fmt --check
scripts/third-party-notices.sh --check
```

Those commands run from rnx, and their logs are copied into the results checks
directory. The built stock binary also runs `selfcheck`. Neither these commands
nor the API feature claim Windows/macOS server execution; this gate is Linux.
Results and exact provenance live in `results/server-acceptance-0056/`.
