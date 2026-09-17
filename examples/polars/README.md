# Tiny Polars project

Keep the rnx and rnx-bench checkouts as siblings for the manifest's relative
native paths. Build rnx-project from rnx/tools/project first. Then lock, build and
run as described in rnx/adapters/polars/README.md. Pass an absolute, existing,
fresh output directory as the one script argument. Each run creates tiny.csv and
tiny.parquet there and refuses existing files.

To explore the same extension interactively, from the rnx-bench directory:

```sh
rnx-project lock --manifest examples/polars/rnx.toml
rnx-project build --manifest examples/polars/rnx.toml
rnx-project session --manifest examples/polars/rnx.toml
```

At the prompt, use a fresh output filename (existing files are refused):

```rune
fs::write_new("explore.csv", "category,value\na,1\na,2\nb,3\n").unwrap();
let frame = polars::read_csv("explore.csv", [("category", "string"), ("value", "i64")]).unwrap();
println!("{}", frame.preview().unwrap());
let result = frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).collect().unwrap();
println!("{}", result.preview().unwrap());
result.write_parquet_new("explore.parquet").unwrap();
```

The working directory stays where you launched the command. The session does not
run main.rn or import mapped Rune packages; it opens the executable's native
extensions. Reset clears bindings but retains Polars. A separate expression can
use `rnx-project eval --manifest examples/polars/rnx.toml -- 'polars::lit(1).is_ok()'`.
Both commands check project inputs and never build; add `--verify` before the
source boundary to request a full artifact hash.

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
