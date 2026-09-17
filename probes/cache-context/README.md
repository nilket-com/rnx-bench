# 0061 gate 1: cache context and retained build ownership

This is an isolated prototype, not a cache implementation. The root product is
unchanged. Run from rnx-bench with rnx alongside and the accepted project tool's
release dependency cache available. Requirements: Linux, Rust/Cargo/rustup with
an installed active toolchain, Python 3, Git and strace. No network or database.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/cache-context/build.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cache-context/check.py
```

Preserve results/cache-context-0061 before rerunning; it is tracked evidence.
The build script copies the tool to an ignored workspace, adds context_probe.rs
as a binary and compiles/formats/lints it there. It verifies every imported
product Rust file is byte-identical and records hashes and the source commit.
The original Cargo.lock and dependency set are unchanged; only a binary target
is added. The root's formatting configuration is copied too. No new public API.

The Rust probe calls the real manifest parser, wrapper generator, bounded native
fingerprinter, ancestor inventory and serializers. Its new code canonicalizes
declaration roots, guards managed paths, refuses project-local config outside the
cache search chain, and applies the current Cargo config allowlist. A preflight
with no resolved packages checks cache context before metadata; the full audit
includes native package ancestors after metadata. The Python driver orchestrates
Cargo and assembles a diagnostic identity from those real records. Identity bytes
are not proposed as the final production format. Root selection/publication,
concurrency, receipt attachment, migration and eviction are not implemented.

The private cache has a user-facing symlink to a canonical directory, an allowed
net.offline setting and an installed toolchain selection. A private Cargo home
contains a separate allowed config. Cargo metadata runs in a temporary resolver
workspace; final metadata and build run inside entries/<key>/assembly with an
entry-owned target. A second consumer generates/resolves independently.

Inventories, canonical manifest/main, Cargo.lock and toolchain observations agree
across locations. The key document contains neither temporary workspace nor its
own final hash/path. Strace records actual config opens. An uncached-dependency
control at both locations fails with Cargo's offline diagnostic without passing
--offline, proving the allowed setting takes effect. No online comparator is run.

The fixture runtime is a tiny generated-wrapper-compatible Rust host, not Rune.
The adapter writes retained.txt to OUT_DIR during build and reads that exact file
at runtime. Two consumers see the same native path and retained path/value even
after temporary resolution workspaces are removed. Removing only retained.txt
makes the executable fail; restoring it restores success. This proves the entry's
retained directory matters, not just the executable bytes. This tiny entry's byte
count is recorded; it is not a prediction of the Polars cache's disk use.

Eighteen late candidate injections cover managed ancestors/stage and project-local
Cargo/toolchain files; each refuses before Cargo. Existing allowed config edits
and newly present audited candidates change the inventory. Unsupported config
keys refuse in preflight too. Generated input symlinks, a managed directory symlink,
a managed FIFO directory and a FIFO config candidate refuse without blocking.
The symlink selecting the user root succeeds. These are trusted-directory checks,
not an atomic filesystem snapshot or a sandbox against concurrent native code.

All commands have timeouts and are awaited; only the controlled fixture is built.
Full process-group interruption and shared entry publication are later gate 3,
not established by this prototype. No user cache, Cargo config or home file is
modified. Raw syscall traces, commands, inventories, identity and fixture sources
are retained. The isolated prototype is formatted and strict-Clippy clean.
