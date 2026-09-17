# 0061 gate 3: shared-entry publication and interruption

From rnx-bench with rnx alongside, Git, Python 3, the installed Rust toolchain,
and the tool's release dependencies already cached:

```sh
python3 probes/cache-publication/build.py
python3 probes/cache-publication/check.py
```

Preserve `results/cache-publication-0061` before rerunning. The builder copies the
actual product sources, adds one private driver, and checks imported source bytes
against rnx after formatting. Build and strict Clippy run with test-support. The
Cargo graph is unchanged. The saved source patch applied to the recorded rnx base
reconstructs the product code; source hashes and the probe binary hash identify
what ran. Nothing uses the user's real cache.

The private production `cache_entry` module owns the per-key lock, input
revalidation, stable build directory, Cargo child group, artifact installation,
ready document and full validation on attachment. `cache_storage` carries the
checked path/configuration rules previously proven in the gate-one prototype.
The driver holds a project lock first, supplies a bounded project snapshot check,
and writes **fixture receipts** after acquisition. Product lock format 2, receipt
v3 and CLI selection are gate 4, not claims made by this fixture. Missing-cache
refusal runs the production readiness/checked-artifact boundary, not a shared
product `run` command that has yet to be integrated.

The native crates are deliberately small, generated-wrapper-compatible fixtures.
They compile with real Cargo, and the executable reads the consumer's main.rn as
text from its working directory. This proves separate application consumption,
not Rune parsing; the real Polars project journey remains gate 5. A build script
writes a retained OUT_DIR file and can hold compilation open. The executable reads
that same retained file. A test waits for the script's PID before signalling.
The build script does not inherit the per-key lock descriptor.

The matrix checks:

- Two projects on one key issue exactly one Cargo build and attach the same
  artifact. Both execute and read their own source text. Different keys reach
  their build scripts concurrently before either is released.
- Compiler/Cargo shims log invocations. An attachment succeeds with compilation
  and metadata trapped; a miss with that trap fails as a positive control.
- SIGTERM and SIGINT interrupt a builder inside Cargo's running build script.
  The tool kills/reaps its Cargo group; the observed build-script PID disappears.
  The blocked waiter subsequently acquires, sees no readiness, becomes the
  builder, and succeeds. There are two build invocations, not a false hit.
- SIGTERM and SIGKILL separately kill a blocked waiter. The builder remains alive
  and completes; a fresh process attaches with compilation trapped. No receipt
  is left by the dead waiter. SIGKILL of an active builder is **not** the existing
  owned-child interruption guarantee and is not claimed here.
- Failures before Cargo, after Cargo, before ready, after the ready temp-file
  write, after readiness, before attachment, and during fixture receipt
  publication. Retries distinguish an unpublished directory from a valid hit.
- Native edits and external/managed Cargo config changes refuse readiness;
  project source/lock edits permit the independently valid assembly but refuse
  its project attachment. A source edit while waiting is rechecked after locking.
- Malformed, unknown-field, wrong-version/key/path readiness, corrupt artifact,
  managed entry/ready/lock/artifact symlinks, FIFO ready/lock, writable entry,
  relative selected root and missing entry refuse. A user's symlink to the root
  succeeds. Published ready bytes are never silently replaced on refusal.

All deadlines are fixture bounds, not cache-hit performance evidence. No cache
launch timing, Windows execution, Polars build, source-check weakening, or public
receipt migration is inferred from this gate.
