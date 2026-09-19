# 0066 gate 2 — product removal commands

This exercises the real `rnx-project` product. The accepted gate-1 candidate and
its results are unchanged. `source/` archives every Rust file changed from rnx
`bafa2a0`; overlay it on that revision to reproduce this implementation.
`results/removal-commands-0066/build.json` records all tool source hashes and both
frozen release binaries. SHA-256 here identifies evidence, not product formats.

Requirements: Linux with guarded openat2, Python 3, Rust/Cargo, Git, strace and
bubblewrap with working unprivileged user namespaces. The six actual mount cases
use the accepted gate-1 bootstrap; no sudo or host mount change is needed. Cargo
sources must already be available for offline builds. Allow several GB for the
private retained assembly and its same-key replacement.

From the bench root:

```sh
python3 probes/removal-commands/build.py
python3 probes/removal-commands/filesystem.py
python3 probes/removal-commands/contracts.py
python3 probes/removal-commands/setup.py
python3 probes/removal-commands/rebuild.py
python3 probes/removal-commands/finish.py
```

`build.py` checks both configurations serially and freezes them under target/bin.
The filesystem and contracts drivers require target/cases and target/contracts
respectively to be absent. Setup requires target/real absent. Rebuild requires
results/removal-commands-0066/rebuild.json absent; preserve previous results
before a rerun. Run in a disposable checkout or save/restore the results directory
if retaining the checked-in evidence. Scripts otherwise overwrite their own logs.
Never point these drivers at a user cache.

Setup builds an authentic old consumer using the 7cd3205 tool. By default that
binary is the retained native-inventory fixture at
probes/native-inventory/target/stock/tools/project/target/release/rnx-project;
`RNX_REMOVAL_OLD_TOOL` can name a separately built binary from that revision.
It copies the 7cd3205 source from Git, installs it with the old tool, renames the
fixture checkout, and builds Polars plus a small retained-OUT_DIR reader from an
initially empty assembly cache. The old tool digest is recorded. No original
checkout path appears in the wrapper or project locks. The current launcher
copy is setup bookkeeping only; the rebuild test uses the old tool and frozen
support product, not that launcher.

The annotation templates are exact manifest/lock/receipt snapshots from the
accepted gate-1 old/new projects. Contracts change their reference fields on
purpose: annotations report recorded paths, not build authentication or freshness.
No dependency source, executable or original template path needs to exist to
inspect those documents. The generated/local and override cases are envelope
controls, not builds. The genuine shared receipt is also exercised in rebuild.

Coverage:

- 42 filesystem cases: no-lock inspection, old/new selection protection, busy
  writers, symlinks/hardlinks/permissions, special files, bounds, all three
  signals, guarded-open failure, six real mount shapes and retained lock inodes.
  The gate-1 candidate-only child-exec controls are excluded: product maintenance
  spawns no child. Its held lock's CLOEXEC bit is observed directly in /proc.
- 52 contract groups: CLI/root selection, bounded reports, old/current explicit
  references, relative/duplicate paths, local/override distinction, missing and
  changed documents, every parent-sync failure boundary, SIGKILL around the two
  rename-parent syncs, actual permission errors, and ordinary-build hook absence.
- Genuine old-tool rebuild: kill after both rename-parent syncs, execute the old
  tool's build with rustc execs traced, check the same key and a new artifact inode,
  inspect visible and pending copies, run the exact printed resume command, then
  compare every visible file's bytes/inode/mode/mtime/size and execute the old
  retained-output reader. A synthetic replacement alone does not pass this test.

Sync errors are test-support failures immediately before/after actual syncs,
not a claim about power-loss persistence. Signal tests use real signals.
Administration and deletion operate in private stores; no live consumer is
present during actual removal. Gate 1 proved inspection against live old sessions
and kernels. Gate 3 still owes the full current-default/combined-adapter journey;
gate 4 owns costs and broad regression.
