# Worker boundary probe — record 0046

Measured by Codex on nano, Linux, 2026-09-14. This is the pre-integration
transport gate, not a Jupyter kernel or an implementation of every worker gate.

```
cargo build --manifest-path probes/worker-boundary/Cargo.toml --locked
python3 probes/worker-boundary/probe.py --rnx /absolute/path/to/rnx
cargo check --manifest-path probes/worker-boundary/Cargo.toml --locked --target x86_64-pc-windows-msvc
```

Results: `results/worker-boundary-0046/`. The baseline rnx binary was the
release at 428d93d, preserved as `/tmp/rnx-0046/before`. Its source and the
probe lockfile, rather than that temporary path, are the reproducible inputs.

Python's `pass_fds` makes precisely the child control ends inheritable across
the first Unix exec. Rust's worker sets FD_CLOEXEC on both before spawning
anything. A real rnx `process::run` then starts a three-second sleeping child.
The worker exits while that child lives. EOF arrives immediately with isolation;
a deliberately inheritable negative control holds it for the sleep. Ordinary
Rust Command does not universally close inherited non-CLOEXEC descriptors.

The Windows parent uses STARTUPINFOEX's explicit handle list, with only those
control ends temporarily marked inheritable in addition to standard handles.
The Rust worker checks pipe type and access rights (NtQueryInformationFile),
then clears HANDLE_FLAG_INHERIT. This Rust mechanism type-checks for MSVC;
neither the Windows parent nor worker has executed here.

The scanner tests every split of a marker, byte-at-a-time input, stale nonce,
NUL/invalid UTF-8 and EOF in every partial prefix. Concurrent pipe collectors
retain at most 2 MiB per stream and continue draining discarded output to the
barriers. Delaying handoff preserves the identity attached at collection.
These initial gates do not yet establish the production worker's admission,
reset, interruption, fatal-error or late-writer contracts.
