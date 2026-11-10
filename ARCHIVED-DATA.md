# Archived benchmark evidence

## Lookup

ADR 0240 removes captured measurement data from git, without changing the
published numbers or pretending that a rerun reproduces original evidence.
Original repository/path/blob identities resolve through `INDEX.json` in
the `0240-data` archive. Its checksum and original bundle revisions are in
`ci/data_archive.json`. Links with a `path` query identify the original path
inside that index.

The archive currently exists only on the maintainer's host. Request a copy
when auditing original evidence. Nothing is fetched automatically. The
complete `files/rnx-bench/` snapshot and repository bundle preserve original
scripts, relative inputs and signatures; use that snapshot or a separate
bundle clone for historical measurement replays.

For supported report rendering from a fresh clone, set `RNX_DATA_ARCHIVE`
to the archive directory and run `python3 -B scripts/render_column_0233.py`
(or the corresponding renderer). Inputs are checksum-verified before use;
reports are written to this checkout. No measurements run. Some older
renderers produce standalone tables/reports rather than a README section.

Retained executable harnesses and build configuration moved from `results/`
to `probes/retained-results/`, byte-for-byte. They are historical source
snapshots, not a promise that their original working-directory assumptions
or absent data still work here. Replay using the original archived snapshot.
Current reusable benchmark drivers under `scripts/` retain their command-line
input/output contracts. Newly measured output belongs outside tracked git.
