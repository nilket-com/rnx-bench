# 0058 gate 3: bounded preview

Use gate one's pinned private Python environment. From rnx-bench:

```sh
cargo build --release --locked --manifest-path ../rnx/adapters/polars/Cargo.toml
probes/polars-boundary/.venv/bin/python probes/polars-preview/check.py
```

The driver writes temporary Parquet fixtures, invokes real Rune scripts, and
checks preview bytes and native opacity. It covers 0/9/10/11/100 rows,
1/7/8/9/100 columns, 79/80/81/100000-scalar names/cells, Unicode and controls,
a byte-limited frame, nullable strings and bit-exact floating-point spelling.
Preview is called twice on each bound frame. Separate eval controls prove it
has no stream side effect and the ordinary renderer leaves native values opaque.

`--binary` chooses another product; `--output` keeps reruns separate from the
committed evidence. Text specimens are the returned strings without extra
terminal styling. Product Rust tests exercise the exact byte-cap boundary and
structural scalar bound independently. No performance or notebook claim.
