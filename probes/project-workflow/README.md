# 0057 gate 5: project command workflow

Run from rnx-bench, with rnx alongside it:

```
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
python3 probes/project-workflow/check.py
python3 probes/project-workflow/postgres.py
```

The first fixture creates a tiny Git-tracked, API-compatible Cargo crate in a
temporary directory. It tests orchestration rather than pretending to be Rune:
lock/build/run, exact public-file layout and Git ignores, no Cargo/rustc during
run, stale/tampered identity, failed builds, concurrent commands and edits,
SIGINT/SIGTERM, an interrupted lock-pair publication, relocation, and overrides.
A real build script spawns a sleeping child; interruption observes both gone.
Test-support pause hooks observe boundaries deterministically without sleeps
standing in for readiness. Neither hook exists in an ordinary tool build.

The second fixture uses the actual PostgreSQL adapter, plain extension and mapped
source from accepted gate 4. Run package-assembly/run.py first if its ignored
fixtures/cache are absent. It calls the product lock/build/run commands and
performs a typed query on the accepted private Unix-socket cluster helper.
Compilation cache is copied with reflinks when available; this is a warm build,
not a first-build measurement. All generated files remain in .rnx, and the
postmaster is independently observed reaped. It never uses the system cluster.

New rnx files must be staged before the real lock test, because the native path
contract refuses untracked non-ignored files. Avoid changing rnx files during the
real build: post-build checks correctly refuse those changes. Its lock/receipt
are temporary evidence snapshots, not locks for subsequent documentation edits.

Results are under results/project-workflow-0057. RNX_PROJECT_TOOL may select an
explicit tool executable for either fixture. Windows execution is not claimed;
the CLI explicitly refuses there pending owned subprocess supervision.
