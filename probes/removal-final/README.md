# 0066 closing gate

This gate freezes ordinary and support tools, runs regression, then measures on
an otherwise idle host. The production handshake timeout remains one second.
Its stream reader is lifted unchanged into module scope for a direct bounded
reader test; the subprocess refusal no longer demands that size win a race with
its valid timeout. Twelve concurrent support suites are retained without retry.

Run from rnx-bench with rnx alongside it; use a fresh probes/removal-final/target
and preserve prior results before rerunning. Keep the rnx checkout fixed until
all build-dependent replays finish: its whole tracked tree is a native input.
Requires the accepted native-inventory/inventory-workflow/inventory-final inputs,
removal-storage gate-3 stores, cached Cargo sources, PostgreSQL tools, bubblewrap,
Git, strace, Rust/Cargo and the normal root/Jupyter release builds. No user store
is selected. Historical fixture sources are adapted into separate result paths;
their accepted results are never overwritten.

```sh
python3 probes/removal-final/checks.py
python3 probes/removal-final/regress.py
python3 probes/removal-final/removal.py
# Only after builds/replays have stopped:
python3 probes/removal-final/costs.py
python3 probes/removal-final/measure.py
python3 probes/removal-final/collect.py
python3 probes/removal-final/finish.py
```

Checks run root default/support/combined suites serially, notices, a fresh default
release and selfcheck, then tool suites/clippy in both configurations. Regress
freezes both tool binaries, runs twelve support suites concurrently, compares
the protected root/default graph against d7d8b0d and the public docs, executes
the ignored integrations, and replays preparation/startup/commit, discovery,
reopen, runtime publication/repair, current workflow/cache publication/migration,
recovery and interactive contracts. The BLAKE3 fixture helper is compiled from
the existing dependency graph. Installed-default sessions use the final tool,
new scratch state and retained gate-3 native inputs, with compiler traps and real
typed PostgreSQL queries. Removal replays the 42 filesystem and 52 command groups
against the frozen binaries, including the six actual mount shapes.

Every top-level driver owns separate directories under target. Replays require
their group directories absent (preparation, startup, commit, discovery,
publication, repair-support/ordinary and supplemental groups). Scope can reuse
its own before directory; all other setups require fresh destinations. Cost
measurement requires target/costs absent. Launch requires launch-before,
launch-after and the launch journal absent. Never clear an accepted fixture to
satisfy these requirements; only this closing fixture's own targets/results.

Storage costs are single-run observations, not a universal threshold. Whole
Polars, combined and runtime entries from gate 3 are copied into private stores
and never executed. Listing/dry-run/ordinary removal and interrupted resume
report node counts (also checked against independent enumeration), logical bytes,
allocated estimates and wall times separately. statvfs free-space readings are
bracketed by os.sync outside the command timer. The host filesystem is shared,
so unrelated allocation can affect deltas. Copying requests no reflink and adds
no synthetic padding. Original metadata/selection and permanent lock inodes are
checked; retained control directories explain some unreclaimed blocks.

Launch measurement uses the exact 443-file zero-to-three roster from 0065, with
its full-size third adapter, one core and one Polars thread. Both tools use the
same BLAKE3 project inputs and direct artifacts. The baseline is the accepted
inventory-final/target/reuse binary, hash-checked against its archived result;
tool source is byte-identical between 4855dbd and d7d8b0d. The final ordinary tool
is frozen separately. There are 3000 retained samples: 48 everyday cells and two
verify cells, 30 samples each in two interleaved repeats. All output is validated.
All six first-adapter cells are reported for both revisions. The old 0065 noise
qualification is retained; there is no new absolute one-millisecond gate.

source.patch plus source-state.json preserve the measured rnx tree relative to
d7d8b0d. Apply with --index to reconstruct the tracked-file set for native-input
replays. Final plan/README closure text is deliberately written after those
replays, so it cannot stale a project during its build. Linux execution only;
no new Windows claim.
