# 0062 gate 1: an adapter name authors an ordinary declaration

```sh
cargo build --locked --offline --release --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/adapter-authoring/build.py
python3 probes/adapter-authoring/check.py
```

Run from rnx-bench with rnx alongside it. This is an isolated prototype, not a
product `add` command. `build.py` copies the accepted tool modules and lockfile
into the ignored target directory, adds one probe binary, formats/builds it and
runs strict Clippy. Every imported Rust source must remain byte-identical to
the real tool. No new dependency is introduced. A separate target avoids
overwriting the product executable used for the lock comparisons.

The probe takes `MANIFEST NAME [NAME...]`, resolves the two catalogue entries,
checks their Cargo package/direct-runtime layout, serializes missing tables,
then parses the entire candidate with the real manifest parser. It checks that
the only semantic difference is the selected additions, and returns JSON with
candidate bytes, the parsed declaration, legacy wrapper and canonical shared
wrapper. It performs no write, Cargo invocation, build or publication.

The fixture independently writes hand-authored TOML controls. All 14 positive
cases compare exact candidate bytes, native declarations, same-base raw wrappers
and canonical wrappers. They then materialize candidate/control in separate
fixture projects and call the **real product `lock --offline`** for both. The
resulting canonical identity bytes produce equal assembly keys. The negative
closed-inline-table case must refuse without changing its original manifest.
No build is run, no receipt appears and no shared entry is created.

Cases include relative/absolute forms, redundant relative spelling, absent final
newline, preserved comments and unsorted pre-existing tables, an existing entry
with a canonically equivalent spelling, backslash/quote/Unicode paths, moved
relative layouts, and symlink-parent components whose lexical simplification
would select the wrong directory. Moving the source layout leaves the authored
manifest bytes identical but changes the canonical assembly key as 0061 requires.
Reversed requested names still produce sorted additions. A dotted-key sibling
and an inline child are legal; a closed inline `native` table cannot be extended.

The small native layout is a **metadata fixture only**: its Rust files do not
implement Rune or builders and are never compiled. Separate real Polars,
PostgreSQL and combined cases resolve the actual installed packages through
Cargo, without compiling them or calling their builders. Live registration,
query/session execution, command integration and atomic manifest publication
belong to subsequent gates.

Results live in `results/adapter-authoring-0062/`: original/authored/manual TOML,
probe output, canonical identity documents, exact Cargo locks and raw logs.
Temporary projects/cache are removed when the fixture ends. Earlier failed
scaffolding runs are labelled separately: missing imported Rust modules, a
synthetic fixture declaring one Cargo package twice under different aliases, and
a manual control assuming basic-string rather than literal-string TOML spelling.
None required a product change or a weakened assertion. All final positive cases
still demand exact control bytes and key equality.
