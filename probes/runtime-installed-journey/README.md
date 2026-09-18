# 0064 gate 4: ordinary installed-runtime journeys and F3 recovery

From the bench root, with this probe's `target/` and `repair-target/` absent:

```sh
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
python3 probes/runtime-installed-journey/repair.py
python3 probes/runtime-installed-journey/setup.py
python3 probes/runtime-installed-journey/journey.py
python3 probes/runtime-installed-journey/publication.py
```

Setup copies the tracked working snapshot exactly, commits that isolated fixture,
and builds an ordinary release launcher and tool from it. The source patch against
6198669 is archived. No prototype implementation is used. The installer then copies
that same snapshot, including both real adapters. The source is physically renamed
before the first installed assembly build. All projects, history, state, cache,
installation and build outputs live in the ignored target. Existing global registry
sources are used with offline Cargo; the target and shared assembly cache are cold.
Do not run tool configurations concurrently in one target directory.

The journey reuses the accepted session-dogfood driver with only the runtime root
changed and additional assertions on the stock notice's installation ID, canonical
path and provenance. Both adapter engines are real. The four journeys exercise
first stock Polars build, second stock attachment with compiler traps, printed
scratch reopening, then absolute/relative mixed Polars/PostgreSQL projects with a
private cluster and a typed query. The second combined consumer also traps compile.
Bindings, numbering, cwd, history, same PID, terminal ownership and cleanup retain
the existing assertions. An explicit-override notice/decline is checked separately.

`repair.py` runs ordinary git status with umask 002 and a stat change to force an
index rewrite. Reinstall and select both repair mode 0664 to 0600 without changing
bytes, inode or mtime. Corrupt objects and corrupt source bytes refuse under both
commands without permission writes; source permission drift stays refused.
To run the same cases against setup's ordinary release binary, use:

```sh
RNX_REPAIR_TARGET="$PWD/probes/runtime-installed-journey/target/ordinary-repair" \
RNX_REPAIR_TOOL="$PWD/probes/runtime-installed-journey/target/bin/rnx-project" \
RNX_REPAIR_RESULT=ordinary-repair.json \
python3 probes/runtime-installed-journey/repair.py
```

That separate repair target must be absent before its run. For a complete rerun,
remove only this probe's two ignored directories. Setup resets the append-only phase
journal; results are overwritten under `results/runtime-installed-journey-0064`.
The 90-case publication replay in `publication/` uses the unchanged accepted driver,
with only its W/O paths redirected; `publication-driver.json` records this substitution.
These are correctness journeys. Their observed cold-build durations are not gate 5's
matched cost experiment, and no cross-platform execution is claimed.
