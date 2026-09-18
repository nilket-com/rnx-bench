# 0063 gate 4: real dependency sessions

This drives ordinary product binaries through PTYs and builds the actual Polars
and PostgreSQL adapters from this checkout. No adapter, engine, query or build
body is replaced. Linux, the cached registry sources, and PostgreSQL 18's server
tools at `/usr/lib/postgresql/18/bin` are required.

From the bench root:

```sh
cargo build --locked --manifest-path ../rnx/Cargo.toml --bin rnx
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/session-dogfood/setup.py
python3 probes/session-dogfood/check.py
```

Setup freezes copies of those ordinary binaries so later feature-suite builds
cannot replace a tool midway through the journey. Stage new root source files
before setup and freeze tracked root inputs until the driver finishes. The
source patch in the results reconstructs the measured source before evidence
and plan edits change the repository fingerprint.

Use a fresh ignored `target/` for the full driver. It requires an absent private
cache and state root for the cold-target control. Registry sources are already
cached: this is **not** a cold download measurement. Two assemblies (Polars and
Polars plus PostgreSQL) are built; allow several minutes and several GB of disk.
No user projects, history, settings, kernelspecs, shared cache or system database
are used. The private cluster starts with no TCP listener and is stopped by its
context manager. The PTY is xterm-256color, 120 columns, and Polars uses one thread.

The first stock session declines without creating state, then consents, compiles,
probes and replaces the same PID. The replacement prints the reopen command. Its
state path includes an apostrophe and a space, and the driver executes the exact
printed command through `/bin/sh` to reopen the retained project.

The second stock session runs with Cargo and rustc compilation traps. Positive
controls establish that both traps reject compilation; actual resolution/version
commands still delegate to the real tools. It must attach with an empty compile
log and the identical assembly key and artifact digest. This is not inferred
from latency. The trap records the first real builds without preventing them.

The projects with absolute and relative runtime declarations start with Polars.
`:dep --offline polars postgres` must say Adding postgres and Already declared
polars, preserve the native roster across replacement, add a lifecycle declaration
in the same path form, and execute a parameterized query on a private cluster.
The second project attaches to the combined assembly with compilation forbidden.

Each replacement checks prompt 1, same PID and terminal ownership, old bindings
missing, unchanged working directory, and no child processes at handover. Saved
history is recalled with up-arrow and discarded with Ctrl-C; its binding is still
missing, proving no replay. Frames are bound and transformed across inputs,
survive a missing-column error, and go through Parquet write/read equality. Quit
reaps every session, and the observer verifies no tagged database backend remains.

Times are descriptive consent-to-prompt observations, not the gate 6 matched
latency benchmark. Gates 5 and 6 retain postcommit faults and closing regressions.
