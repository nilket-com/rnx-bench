# 0062 product catalogue gates 2–6

`contracts.py` exercises the real test-support product binary: listing without
project access, helper execution traps with positive controls and syscall traces,
bounded metadata/parser refusals, spelling and append controls, no-op identity,
editor races, the project lock, malformed temporaries, and both sides of rename
under injected errors and SIGINT/SIGTERM. Metadata-only fake adapters contain no
code that could be called as a builder. `strace` is required on Linux.

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml \
  --features test-support --bin rnx-project
mkdir -p results/adapter-commands-0062
python3 probes/adapter-commands/contracts.py
```

The ordinary release product is used for the real consumers. Before building,
stage any newly added rnx source files (native fingerprints enumerate Git's
tracked index). Keep the rnx working-tree bytes unchanged until all journeys and
measurements finish. Evidence records the measured checkout as base plus a saved
patch; later evidence-only edits naturally make these old project locks stale.

```sh
cargo build --locked --offline --release \
  --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/adapter-commands/setup.py
python3 probes/adapter-commands/postgres.py
python3 probes/adapter-commands/journey.py
python3 probes/adapter-commands/live.py
python3 probes/adapter-commands/measure.py
```

Setup requires a fresh ignored `target/cache`, `target/first` and `target/second`.
It first builds a base executable, adds Polars, checks refusal and unchanged old
artifacts, then explicitly locks/builds. A separately hand-written control has
exactly the same table bytes and assembly key and attaches with compiler
invocations trapped. Cached registry sources permit offline builds; target
compilation is real. `postgres.py` builds and executes both adapters together,
using the shared private-cluster helper and observing zero tagged backends and
postmaster reaping. It needs PostgreSQL 18's tools at the helper's stated path,
never the system cluster. Re-runs require fresh fixture-owned directories.

Both consumers execute the accepted frame/error/preview/reset PTY journey.
`live.py` adds a declaration while a session holds a binding: the running process
retains its value and Polars, and cannot see the newly declared PostgreSQL module.
`measure.py` repeats the 0061 timing contract: 720 retained observations, two
consumers × three modes × direct/default/verify, interleaved on one CPU with one
Polars thread, with every output validated. Run timing after builds/tests stop.

Regression drivers reuse the accepted commands with separate result paths:

```sh
python3 probes/adapter-commands/checks.py
python3 probes/adapter-commands/integrations.py
python3 probes/adapter-commands/scope.py
python3 probes/adapter-commands/fixtures.py
```

Run `fixtures.py` only after the real-product measurements: its historical
fixture rebuilds/cleans the tool's target between configurations. Root and tool
configurations are sequential. No accepted results directory is overwritten.
The replay scripts and their source hashes are retained with the new results.
Windows is type-checked, not executed; listing is available there and mutation
keeps the existing unsupported-supervision refusal.
