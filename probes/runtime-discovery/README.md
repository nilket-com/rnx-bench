# 0064 gate 3: installed runtime discovery

Build the product tool with test support, then run from the bench root:

```sh
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
cargo build --locked --manifest-path ../rnx/Cargo.toml --bin rnx
python3 probes/runtime-discovery/check.py
python3 probes/runtime-discovery/reopen.py
```

Start with this probe's `target/` absent; remove that whole ignored fixture directory
before rerunning both drivers. No user installation, cache, source or history is
modified. Results are written to `results/runtime-discovery-0064`. The first driver
freezes the test-support tool, so subsequent tool feature builds cannot replace it.
TERM is xterm-256color with a 120-column terminal.

The protocol matrix uses the production installer with tiny tracked catalogue
layouts. It exercises absent/current/override selection, full content validation
before scratch creation, consent changes, malformed and oversized documents,
managed symlinks, missing Git and the F2 CLI errors. Six real stock-session PTYs
start an HTTP future via select, request a dependency, then confirm the binding
and the original HTTP result survive each failed preparation or decline. The hold
server is a joined fixture thread, and every session/helper is waited.

The reopen driver copies the tracked working rnx snapshot and substitutes only
the native adapter bodies/manifests with small named functions. It installs two
snapshots, renames the fixture checkout, then creates a scratch via real describe,
prepare, Cargo build and startup check using the first installation. After choosing
the second, the old scratch reopens through the product. Its real carrier proves an
associated describe ignores an invalid override; ordinary eval ignores a corrupted
default document. Manifest and receipt remain unchanged. This is ownership evidence,
not a Polars/PostgreSQL engine or timing claim; those journeys remain gate 4.

`source.patch` records the exact working source behind these builds against
`c6fc230`. The fixture mutations above are reproducible from these scripts. Evidence
and status edits written afterwards are not claimed as measured source. The first
scaffolding run recreated current.json with an ordinary host mode and correctly
failed the private-file check; the final driver restores its private mode.
