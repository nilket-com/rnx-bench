# 0061 gate 4: real commands, explicit migration

```sh
python3 probes/cache-commands/build.py
python3 probes/cache-commands/check.py
python3 probes/cache-commands/replay.py
python3 probes/cache-commands/polars_override.py
python3 probes/cache-commands/publication_replay.py
cargo build --locked --offline --release --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/cache-commands/ordinary.py
```

Preserve `results/cache-commands-0061` before rerunning. Requires the same cached
Rust dependencies, Git and Python as the accepted tool probes. The Polars override
journey additionally needs the already-built 0060 Polars artifact, or its path in
RNX_POLARS_ARTIFACT. No downloads, user cache or user kernelspecs are involved.

`build.py` archives the published rnx 814d20f tool source and builds a frozen
legacy executable. It uses a separate target directory for that baseline, then
cleans/rebuilds only the current tool package in the ordinary tool target. This
avoids Cargo's same-name binary/dependency output collision encountered when the
two source locations shared a target. Dependency caches remain available. Do not
run builds that replace the measured tool executable while these fixtures run.

`check.py` uses real lock/build/run/session/eval commands. A tiny Git-tracked Rust
runtime reports argv rather than evaluating Rune; a build script records OUT_DIR
outside the native tree. A format-1 lock and version-2 receipt are genuinely built
by the old tool. Current launches preserve their bytes and local artifact; a
current build stays local. Only explicit relock selects format 2. The next build
runs the build script in the shared target, creates a separate artifact, and
leaves the local artifact untouched. The second project's build attaches without
compiler compilation/metadata, with traps enabled. Launch traps also forbid
version queries, proving run/session/eval need no Cargo or rustc process.

The 13 groups include v3 bindings, default versus --verify byte-read accounting,
touch/replacement refresh, the documented restored-mtime in-place miss, full
source checks, unused-map scope, context/root/ready/deletion refusals, attachment
and refresh failures, lock-pair rollback/interruption recovery, and overrides
(including switching from shared to override and migrating a v1 receipt).
The driver runs under the normal host umask, which exposed Cargo's group-writable
target-directory issue. Production now gives the Cargo child a private umask;
it does not alter the parent or relax ownership checks.

`replay.py` archives transformed copies of the accepted 0059 and 0060 contract
fixtures. Only successful lock creation is routed to the frozen tool, to keep
those tests' explicit local/v1/v2 assumptions. All build and launch operations use
the current tool. Original hashes and transformed scripts are retained; their
receipt, byte-accounting, argv and refusal assertions are unchanged. New shared
lock publication is tested independently by check.py, not claimed from this replay.

`polars_override.py` invokes the unchanged 0060 PTY journey with a fresh private
override project and a copy of the known Polars executable. It covers real Rune
frames, reset, errors, Ctrl-C, EOF, working directory, settings, mapped-source
staleness, and byte-identical eval versus direct. It does not claim a fresh shared
Polars build; that is gate 5. `publication_replay.py` repeats all 37 gate-three
cases against current product sources in its isolated build, with output redirected
to this gate's results rather than changing the accepted gate-three evidence.
`ordinary.py` proves real shared lock/build/eval with both families of fault hooks
set but compiled out.

The source patch against 814d20f preserves the measured implementation. Binary
hashes identify the current/frozen tools; build location can change debug binary
bytes on a rerun. This is not a bit-reproducible-build or latency claim. The real
shared Polars costs and matched launch measurements remain gate 5.
