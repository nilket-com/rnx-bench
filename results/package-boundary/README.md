# Step-five package boundary evidence

Status: prototype complete on Linux; awaiting review. No rnx production files
changed and no project manifest syntax selected.

- `source/results.json`: nine source-root cases, physical paths, full module
  items, candidate order, compile errors and runtime origin.
- `native/results.json`: generated-input hashes, native-source mutation with
  unchanged Cargo.lock, run/eval/session/notebook outputs, restart, executable
  override and private postmaster reaping.
- `native/Cargo.toml.txt`, `main.rs.txt`, `local.rs.txt`, `Cargo.lock`: generated
  inputs and exact native Rust resolution. Relative paths describe the generated
  project under the probe's ignored target directory, not this results directory.
- `conditions.json` and the two `*-graph.json` files: provenance and dependency
  inventory. Instructions and qualifications: `probes/package-boundary/README.md`.

The first decision is now concrete: remapping physical source roots works, but
these dependencies remain modules in the consumer's Rune crate. `self` and
`super` survive renaming; `crate` means the consumer. Loading still requires a
module declaration, and per-package transitive dependencies need another rule.

The native default and override are both viable in the measured form. The lock
proposal needs one addition: identify local source contents, since Cargo.lock
alone does not detect their changes. These are evidence for the next draft, not
an implemented package contract.
