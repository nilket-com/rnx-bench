# 0061 gate 6: regression and record closure

Run from rnx-bench with rnx alongside it. Commands are serial: never rebuild a
different feature configuration while a fixture is using its executable.

```sh
python3 probes/cache-regression/checks.py
python3 probes/cache-regression/scope.py
python3 probes/cache-regression/integrations.py
python3 probes/cache-regression/fixtures.py
python3 probes/cache-regression/collect.py
```

Requires the cached Cargo dependency sources, PostgreSQL private-cluster tools,
and the accepted package-assembly plain/words fixtures. The 0060 Polars artifact
is used for the override PTY replay; `RNX_POLARS_ARTIFACT` may name an equivalent
built artifact. All caches and clusters are fixture-owned. These are correctness
checks, not timing samples or cold-build measurements.

`checks.py` records every command and status, running the root default,
test-support and combined test-support/server-runtime/project-sources suites
with one test thread, followed by notices, ordinary release/selfcheck, both tool
suites, strict all-target tool Clippy, notices and Windows MSVC type-check.
Windows is not executed. `integrations.py` explicitly builds project-sources and
runs the otherwise ignored real manifest handoff and native inventory audit.

`scope.py` extracts the published pre-cache root at `83398d9` into an ignored
directory (no Git worktree), compares default cargo trees with only checkout-path
normalization, verifies the root has one workspace member and asserts the root
source/manifests/lockfile/notices, other packages and tool dependency graph files
are unchanged. It makes no new startup performance claim for unchanged root code.

`fixtures.py` preserves accepted results. It archives transformed copies and
hashes of each original script under the new result directory, retaining original
`__file__` locations for sibling imports and ignored build directories:

- Gate 4's baseline/current build, 13 command groups, 0059/0060 contract replays,
  Polars override PTY journey, 37 publication cases, and ordinary release smoke
  are rerun with only their output destination redirected.
- The 0057 sixteen-group local workflow is also replayed. Its lock commands use
  the frozen pre-cache tool so its local-format assertions remain meaningful;
  every build and launch uses the current tool. The transformed source is saved.
  Shared locking, publication and migration have their separate current-command
  fixtures above; the old workflow is not presented as proof of those semantics.
- The real PostgreSQL workflow uses current lock/build/run throughout, a fresh
  private cache, mapped Rune source and the plain/native adapters. Its historical
  local-target seeding block is removed because it has no role in a shared build.
  The private cluster is stopped and its postmaster independently checked gone.

New outputs go to `results/cache-regression-0061/`; published earlier results are
not overwritten. Raw logs, transformed scripts and status records are retained.
The collector binds the replay's source-patch references to the published
implementation and hashes the ordinary and test-support binaries.
The final evidence names any failed attempt or platform qualification rather than
silently weakening a gate. Gate 5's accepted Polars timing is not rerun as part of
this correctness sweep.
