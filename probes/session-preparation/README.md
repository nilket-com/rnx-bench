# 0063 gate 2: product preparation and cancellation

This uses the product root and project tool, not gate 1's copied implementations.
`setup.py` creates a Git-indexed, tiny runtime facade over the real rnx library,
a tracked-future fixture, and catalogue-shaped `polars` and `postgres` adapters.
The latter deliberately register nothing: this is preparation ownership, not a
Polars/PostgreSQL integration or performance claim. Gate 4 uses the real adapters.

Build and run from the bench checkout:

```sh
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
cargo build --locked --manifest-path ../rnx/Cargo.toml --bin rnx
python3 probes/session-preparation/setup.py
python3 probes/session-preparation/check.py
```

Run root feature suites serially, including completion of integration tests,
before rebuilding their common binary in another configuration. The fixture
pins TERM=xterm-256color and a 120-column PTY. It never touches user history,
settings, projects or the user's shared cache. All generated files and the
private cache are under this probe's ignored `target/`. Source checkouts need
registry dependencies already available for the offline builds.

Run setup before a fresh matrix (including after any rnx tracked-source edit).
It restores the original manifest, relocks, and builds/attaches its fixture
assembly. Existing valid entries are reused; an interrupted unpublished entry
is handled by the product. Source edits change the key. Keep disk space for
multiple whole cache entries; this driver does not evict them.

## What is real

The carrier is obtained from `rnx-project session`, not fabricated for positive
association cases. Real lock decoding, Cargo-lock pair checking, receipt
validation, shared ready validation and artifact stamp/hash checking are used.
Touching the actual artifact and launching through ordinary eval refreshes its
receipt; the original live-session carrier must still be accepted. Source
changes alone allow preparation. Declaration, executable and roster changes,
malformed receipts/locks and malformed carriers refuse.

The workflow calls actual add, lock, build and attachment under the existing
project lock. Test-support failures cover both sides of manifest and lock
publication. The recorded diagnostics state that project files may persist.
A real per-key lock held by the driver makes preparation wait; SIGINT to the
session cancels its helper while preserving the old session. A Cargo wrapper
substitutes only the compilation body with a waiting child; the actual tool
owns and kills that process group. The driver checks that neither process is
still running (a transient orphan zombie is not called running or reaped).

Every `preserve-*` terminal case binds `held = 42`, constructs a non-Send tracked
future and polls it via Rune `select` before requesting a dependency. The exact
poll/drop log is checked **before another input**. Then the fixture releases the
future and it returns its original 73. No old-runtime progress is supplied during
preparation. The inherited-carrier case is an actual stock child spawned by a
Rune call in an associated parent session, with the child operating its own PTY.
The nonterminal case proves the line after `:dep` is evaluated, not consent.

## Staging and limits

Gate 2 intentionally cannot report ready or restart. After a successful build
and final checked-artifact validation, it reports that startup checking is not
yet enabled. A real settings-aware startup probe is gate 3; version-only success
must never be used in its place. Pending replacement through the entry stack
was proven by gate 1 and is enabled only with that startup gate.

This matrix is Linux-only. No latency, Windows execution, actual engine loading,
postcommit cleanup or replacement-success claim is made here. Cargo's existing
process-group containment does not contain trusted native code that escapes its
group. Preparation output is streamed terminal-safely with an 8 MiB total cap;
no unbounded diagnostic tail is retained. No old runtime is entered by the
preparation supervisor.

`results/session-preparation-0063` keeps PTY transcripts, matrix assertions,
check logs, binary hashes and the exact source patch against `cf6b6bf`. The patch
includes new files, so the source behind the evidence can be reconstructed even
though the later evidence text changes the repository fingerprint.
