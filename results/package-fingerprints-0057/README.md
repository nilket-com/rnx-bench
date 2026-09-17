# 0057 gate 3: local content identity

Tool tests exercise the real filesystem and Git index, and Cargo resolves and
builds the three-crate transitive fixture offline. The mutation changes the
executable's output from 42 to 43 without changing Cargo.lock; the transitive
root fingerprint changes while the directly declared adapter's does not.

`repository-inventory.json` is an audit snapshot of the staged working tree,
not a product rnx.lock or receipt. The test inventories the actual PostgreSQL
adapter graph, including rnx. Later edits to evidence or documentation naturally
make this earlier snapshot stale. Source hashes in conditions.json identify the
implementation exercised. No stock executable or database is used here.

Reproduce from the rnx repository, with gate 3 files tracked/staged (the native
policy refuses untracked non-ignored files):

```
cargo test --locked --offline --manifest-path tools/project/Cargo.toml -- --test-threads=1
RNX_GATE3_REPO="$PWD" RNX_GATE3_INVENTORY=/absolute/outside/path/inventory.json cargo test --locked --offline --manifest-path tools/project/Cargo.toml repository_audit -- --ignored --nocapture
```

The default suite retains the gate 2 manifest-to-runner integration as ignored;
it needs a feature-built runner, not needed for this tool-only change.
Windows is type-checked, not executed. Root code and dependency graph do not
change. This gate does not implement product lock/build/run commands or receipts.
