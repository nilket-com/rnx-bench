# Record 0050: file modules

The executable resolution fixtures and comparison against Rune 0.14.2 live
in rnx's `tests/fixtures/modules`, `src/program.rs` tests and `tests/modules.rs`.
The runner diagnostics, method naming and source allowance are tested there.

Build rnx at plan `e6c56cd` and the implementation with the same toolchain:
`cargo build --release --locked`, preserving each executable separately.
Then run:

```
python3 probes/file-modules/measure.py /path/to/before /path/to/after
```

This checks full stdout, stderr and status for twelve single-file cases,
including failures and debug-source, plus the four timed commands. It then
runs hyperfine on core 4, no shell, 10 warmups, 100 runs. Raw outputs, source,
binary hashes, toolchain and timings live in `results/file-modules-0050`.
Sequential measurements include drift and do not establish a speedup.

The `windows-check` crate includes the real program loader, runner, declaration
and method modules. Its unchanged surrounding presentation and execution
interfaces are signature-only stubs. `cargo check --locked --tests --target
x86_64-pc-windows-msvc --manifest-path probes/file-modules/windows-check/Cargo.toml`
checks their Rust types; it executes nothing and does not establish a working
Windows rnx executable. The root build's native dependency limitation remains.
