# Cargo target config regression (0067 follow-up)

Requires clang and mold on PATH, the existing Cargo registry cache and a Cargo
Git checkout of rnx 0a420d4. The fixture copies Cargo's Git cache into its private
home and shares the registry cache. It never edits the user's Cargo config.

Build the current tool, then run from any directory:

```sh
cargo build --release --locked --manifest-path ../rnx/tools/project/Cargo.toml
python3 probes/cargo-target-config/check.py --tool ../rnx/tools/project/target/release/rnx-project --work "$PWD/target/cargo-target-config-review"
```

Use a new `--work` directory on every run. Logs, locks and build outputs remain
there. The cold Polars build retains roughly 1.5 GB; no timing win is asserted.
The target section is exactly slim's clang/mold config. Both consumers use the
same cache root, Cargo home, Git revision and native declarations. Their assembly
identities must differ solely when the config changes. The fixture then restores
the config, builds and runs the CSV/group/sum/Parquet round trip. `[patch]` must
refuse without publishing a lock.
