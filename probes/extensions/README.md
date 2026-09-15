# 0051: an external executable assembled with rnx

Measured by Codex on nano, 2026-09-15. This is a separate workspace and
lockfile. Its only direct dependency is rnx, by sibling checkout path.
The fixture's transitive package versions match rnx's locked versions.
`app` supplies three native functions; `broken` selects assembly failures
using `RNX_FIXTURE_CASE`. The fixture timer's thread is test machinery,
not a recommended timer implementation for production adapters.

From rnx-bench:

```sh
cargo build --locked --release --manifest-path ../rnx/Cargo.toml
cargo build --locked --release --manifest-path probes/extensions/Cargo.toml
PYTHONDONTWRITEBYTECODE=1 python3 probes/extensions/check.py probes/extensions/target/release/app
python3 probes/extensions/terminal.py probes/extensions/target/release/app
probes/jupyter-notebook/.venv/bin/python probes/extensions/notebook.py probes/extensions/target/release/app
cargo doc --locked --no-deps --lib --manifest-path ../rnx/Cargo.toml
python3 probes/extensions/api.py
cargo run --locked --release --manifest-path probes/extensions/Cargo.toml --example paths
```

The notebook check reuses the pinned environment and isolated installer from
`probes/jupyter-notebook`. It installs only in temporary directories, executes
a saved notebook, and restarts the real kernel using this application's worker.
The saved notebook passes nbformat validation. No user kernelspec is changed.
`terminal.py` uses a real Unix PTY, with byte assertions for tab completion
before and after reset. It needs no Python terminal-emulator dependency.

For timings, preserve a release binary from rnx `d7e43a2` (code of `b775a40`)
and pass its absolute path:

```sh
python3 probes/extensions/measure.py /path/to/rnx-before ../rnx/target/release/rnx probes/extensions/target/release/app
```

This first asserts stdout, stderr and status equality for all 18 single-file
and CLI-error cases and four timed commands. It then uses core 4, hyperfine
without a shell, 10 warmups and 100 runs. Do not run builds alongside it.
Results, sources, commands, versions, binary hashes and raw samples live in
`results/extensions-0051`. The temporary comparison-source paths in that export
are historical; the script recreates the same cases for each run.

Allocator check: build stock and app with `--features test-support`, preserve
the two binaries, then run `memory.py STOCK APP`. It measures the baseline,
the peak increase for a 1 MiB allocation, and a worker refusal at a one-byte
ceiling. The message includes each process's actual live count; only the
wording and failure category are identical. Repeat both builds with
`--no-default-features` and feed `:memory\n:q\n` through `--no-splash` with
`TERM=xterm` and an absent `RNX_CONFIG`: both must print the report in
`no-count.json`. Restore ordinary release builds before comparing startup.
The feature-variant hashes are in `verification.json`; these variants were
built before a helper was moved above the test module to satisfy clippy.

Namespace observations from pinned Rune 0.14.2:

- `paths-array.rs.txt` intentionally fails: `function` takes one component,
  not a multi-component array. Its compiler output is retained.
- A string containing `::` registers a literal component, not a nested
  function callable with Rune's path syntax.
- A native type with `item = ::other` installed in the fixture module stays
  `::other::Elsewhere`, and that absolute type path resolves. Declaring an
  `other` crate also permits the relative `other::Elsewhere` spelling.
- `broken`'s `replace` case adds `fs::extension_probe`, proving that a trusted
  builder can replace its lent module and that rnx does not confine it.

`examples/restored_hook.rs` installs an extension, returns normally from
`main_with` on session EOF, then panics. With piped empty input, TERM=xterm
and absent settings, exit 101 and exactly `previous hook restored` on stderr
prove that the previous hook is restored. The assembly fixture separately
checks suppression on the builder thread and delegation on another thread.

`mismatch/` is an intentionally failing independent workspace. Run
`cargo check --locked --manifest-path probes/extensions/mismatch/Cargo.toml`:
Rune 0.13.4 and rnx's 0.14.2 produce E0631 at the builder parameter. The earlier
0.14.1 exact-pin attempt is preserved in `mismatch-patch-pin.log`: Cargo
rejects conflicting compatible pins during resolution rather than building
two Module types. Neither negative fixture enters the application's graph.

`windows-check/` includes the actual extension assembly source with only a
HostFunction data stub; check it with `--target x86_64-pc-windows-msvc`.
The full library/binary check stops in ring because lib.exe is unavailable.
The isolated check does not verify whole-program Windows integration or
execution. Linux assembly, PTY, worker and notebook checks are executed.
