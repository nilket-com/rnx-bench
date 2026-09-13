# probes

Small Rust binaries that isolate one cost each. Each takes a mode argument and
returns after that phase, so hyperfine measures whole-process deltas. Both
pin `rune = "=0.14.2"`; `companion-modules` adds `rune-modules = "=0.14.2"`
with the json, fs, time, http, toml, process, rand, base64 features and a
tokio current-thread runtime.

- `context-phases/` — none, context, runtime, compile, run. Basis for the
  "where rnx's startup goes" table and record 0030.
- `companion-modules/` — none, context, nohttp, modules, run (run = install
  everything, build a tokio runtime, drive one `async_call`). Basis for the
  adoption cost figures cited by record 0031.

`run.sh` builds both and writes `results/probes.json` and `results/probes.md`.
- `context-phases-emit/` — the same crate with Rune's `emit` feature on, which
  is what depending on `rune-modules` forces (its `rune` dependency keeps
  default features: `emit` + `std`, not `doc`). Matched against
  `context-phases` in `results/probes_emit.*`: binary 7.76 → 7.89 MiB,
  context and run phases within noise.
