# 0063 gate 3: real startup and handover

Build the product binaries, then run from the bench root:

```sh
cargo build --locked --manifest-path ../rnx/Cargo.toml --bin rnx
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
python3 probes/session-startup/setup.py
python3 probes/session-startup/check.py
```

The fixture uses real project lock/build/attachment and real product sessions.
A tiny runtime facade re-exports the actual rnx library. The catalogue-shaped
Polars adapter is deliberately a fault injector, not the Polars engine. The
fixture extension owns a non-Send tracked operation and logs polls and drops by
PID. Gate 4 will run the real engine and database journey.

Run setup after every tracked root-source change. Native source fingerprints
include the root repository; new files must be staged before setup. The private
cache and projects live below ignored `target/`; registry sources must be
available for offline builds. Each changed source identity retains another whole
cache entry. Run feature suites to completion before rebuilding the shared root
binary in another configuration. TERM is xterm-256color; PTYs are 120 columns.

The startup probe is a subprocess of the tool with a dedicated Unix socket.
Version-only success is a negative readiness control. Actual readiness requires
settings, extension builders, eval of 42, cleanup, an exact versioned frame and
zero exit. The matrix injects builder errors, panic, abort, a blocked builder,
output flood, readiness-looking stdout, malformed/truncated control bytes and a
tracked destructor failure. Every refusal checks the old PID's exact poll/drop
log before any new input, then completes the same future with its original value.
The blocking case is timed externally and probe PIDs are checked after refusal.

A successful handover checks the old operation and value dropping, the same PID
starting a new context, bindings gone, history saved, fresh numbering, builders
once per probe/replacement process, and a second dependency request accepted as
a no-op using the replacement's fresh association. The mixed-name notice checks
F3's Adding and Already declared lines. Direct private-probe controls prove
settings selection/fallback, no history input, no entry evaluation, and sealing
the readiness descriptor before a builder spawns a child.

This is Linux correctness evidence, not performance evidence. These adapters are
trusted native code; process-group containment is not a sandbox for deliberately
escaped descendants. The probe cannot guarantee that a later replacement startup
will succeed. Gates 4–6 retain the real applications, postcommit failure matrix
and timings. Output diagnostics are bounded tails, escaped at the REPL boundary.
