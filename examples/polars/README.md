# Tiny Polars project

Keep the rnx and rnx-bench checkouts as siblings for the manifest's relative
native paths. Build rnx-project from rnx/tools/project first. Then lock, build and
run as described in rnx/adapters/polars/README.md. Pass an absolute, existing,
fresh output directory as the one script argument. Each run creates tiny.csv and
tiny.parquet there and refuses existing files.

Expected preview:

```text
DataFrame: 2 rows × 2 columns
"category": string | "total": i64
"a" | 2
"🦀" | 7
```

This directory is outside the native package roots, avoiding self-referential
lock fingerprints. rnx.lock and rnx.Cargo.lock are generated local identities;
none is shipped as a portable lock. All generated assembly, cache and receipts
remain under .rnx/. The gate 4 fixture copies this example to a temporary project
and runs the real lock/build/run commands, then uses its generated executable
as the notebook worker.
