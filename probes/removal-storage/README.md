# 0066 gate 3 — real storage journey

Product revision: rnx `06a295e`, unchanged from accepted gate 2. Both ordinary and
test-support binaries are the frozen binaries from removal-commands/build.py.
Only the interrupted-removal sequence (pause, pending inspection and printed
resume command) uses test-support. Installation, migration, :dep,
listing, dry-run, ordinary removals and explicit rebuild use the ordinary tool.
The fixture archives all effective dogfood code and outputs; no product patch.

Requirements: the accepted gate-2 frozen binaries under
probes/removal-commands/target/bin, the genuine 7cd3205 old tool from
probes/native-inventory/target/stock/tools/project/target/release/rnx-project
(or RNX_REMOVAL_OLD_TOOL), current root and Jupyter release binaries, the notebook
venv with jupyter_client, local PostgreSQL tools, Rust/Cargo with registry sources
available offline, Git, strace, and several GB free for private assemblies.

```sh
python3 probes/removal-storage/setup.py
probes/jupyter-notebook/.venv/bin/python probes/removal-storage/journey.py
python3 probes/removal-storage/corrupt.py
python3 probes/removal-storage/checks.py
```

Use a fresh target/real and absent results/removal-storage-0066/journey.json.
For a rerun, preserve or remove only this fixture's previous target/real and
results directory, then repeat setup. Never reuse a half-completed journey:
its removals are deliberate and irreversible. The setup is not a user project.
The checks require a completed journey and no surviving fixture processes.

Setup archives the old root at 7cd3205 into a fixture Git checkout, installs with
the old tool, renames the original checkout, then builds an authentic SHA-256
Polars assembly plus an adapter which reads a retained OUT_DIR file. The initial
cache is absent. The runtime source and old lock provenance remain recoverable.

The ordinary current tool authenticates migration into a new BLAKE3 runtime ID.
The accepted session-dogfood driver then runs four real journeys (two scratches,
absolute and relative combined projects) against that selected installed runtime,
without RNX_DEP_RUNTIME. It creates the new Polars and combined assemblies in the
same store; only the old key may exist initially. Effective-driver changes are
limited to the installed runtime path, that initial old-key allowance and an
installed-default notice assertion. Compilation traps still prove attachment;
all Polars pipelines and typed PostgreSQL assertions are unchanged.

An old session and a kernel installed against the old artifact remain live while
both list and annotated dry-run inspect the stores, with both writer locks held
by the fixture. The kernel executes retained-output reads before and after each
inspection. Only after explicit shutdown and reap does removal begin. Killing
removal during unlink leaves a genuinely Polars-sized pending directory. The
printed command resumes it. The old unselected runtime is removed separately;
kept entry bytes/metadata, current runtime, selection, projects and kernelspec
are compared. A deliberately corrupted unselected installation copy is removable
without authentication. The supplementary corrupt.py case keeps a cloned
installation at its authentic ID, proves select refuses its damaged Git object,
and then removes it without invoking authentication; the real default is unchanged.

Finally the fixture deliberately removes the current combined assembly. Ordinary
launch refuses with exec tracing proving no compiler/Cargo invocation. Explicit
build reconstructs the same key from retained inputs. A new stock :dep session
then attaches to it, evaluates Polars and a typed PostgreSQL query, and is reaped.
The selection and installed source stay unchanged throughout.

This gate proves real ownership consequences and recovery, not timings or a
complete reference census. The recorded build durations are single-run fixture
observations. Gate 4 owns reclamation costs, matched launch timing and full
regression, including the previously observed handshake-test timing flake.
