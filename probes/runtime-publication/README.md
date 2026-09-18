# 0064 gate 2: product installation and publication

From `rnx-bench`, with `rnx` alongside it:

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support
python3 probes/runtime-publication/check.py
python3 probes/runtime-publication/finish.py
```

`check.py` requires a fresh `probes/runtime-publication/target`. It freezes the
support executable there before starting. Preserve `results/runtime-publication-0064`
before a rerun. `finish.py` uses the ignored `full` directory and a new store on
each invocation; it needs all new rnx implementation files staged because it tests
the actual complete source tree under the existing Git inventory contract.
Neither command touches user installation/cache/state. Remove only generated
`target`/`full` directories when reclaiming fixture storage.

The product matrix uses tiny Git-tracked trees with the real supported Cargo
layout, not fake installer code. It does not compile these dummy Rust sources or
claim a new Polars journey. Gate 1 already measured real adapters; gate 3 owns
session discovery and gate 4 its integrated end-user journey.

Test-support hooks pause/fail at snapshot, copy, Git, metadata, entry rename/sync
and selection write/rename/sync. Environment-injected smaller allowances exercise
exact boundaries without generating gigabytes. Copy read accounting observes the
allowance plus one detection byte. All hooks and injected limits compile out of
ordinary builds; `finish.py` explicitly tests that ordinary installs ignore them.

The Git wrapper delegates to real Git, observes descriptors after exec and traps
specific `hash-object -w` calls. It tests nonzero status, stdout/stderr overflow,
and SIGINT/SIGTERM while Git and its sleeping child are active. Direct Git is
waited; the process group is killed. An orphaned descendant may briefly be a zombie
awaiting init, but the driver refuses any remaining live descendant. Copy-stage
SIGKILL is tested separately, with reclamation by the next writer. This does not
claim safety after arbitrary SIGKILL of an active external writer outside the
owned process-group contract.

All 15 publication points have assertions on the old/current selection and entry
visibility. Completed-but-unselected entries are validated with real `runtime
select`. Selection rename failures require the honest “may already have changed”
message. Same-ID reinstall compares every retained file's bytes, inode and mtime,
including provenance, and source files/Git administration are checked for writes.
Hostile clean-filter and filesystem-monitor controls first prove their hooks can
run with ordinary Git, then prove installation does not run them. The source can
be dirty, unborn or a linked worktree; no installed synthetic commit is needed.

`finish.py` builds the ordinary product, installs/reinstalls the full working-tree
snapshot, archives its exact tool patch against the baseline commit and runs the
existing 13-group cache/legacy command fixture. That fixture needs
`probes/cache-commands/target/legacy-tool` from its documented build step. Its
published results are copied aside, the new results are retained here, and the
old results are restored even on failure. Do not rebuild different configurations
while a fixture uses the ordinary tool path.

The first matrix pass caught Git inheriting a group-writable umask. Git now sets
077 only in the child before exec. The final matrix also checks bounded actual
copy reads, retained traversal limits and no optional source-index refresh.
No performance claim is made; the later cost and regression gates remain open.
