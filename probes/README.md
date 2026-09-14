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
- `http-lifecycle/` — no Rune; reqwest 0.12.28 on a current-thread tokio
  runtime against two loopback fixtures that report a clean `Ok(0)` EOF
  apart from a read error. Basis for record 0034's decision 3: tasks alive
  after a request (2), after cancelling a request to the second fixture
  while the first's socket sits healthy in the pool (3), whether the
  cancelled socket closes without a runtime turn (it does not), what a
  bounded drain reaches with the client kept (2: the healthy dispatcher and
  the pool's task, the healthy socket stays open and is reused) and dropped
  (0 in ~6 ms, clean EOF on the pooled socket). Output in
  `results/http_lifecycle.txt`, two consecutive runs.
- `context-registration/` — Rune default-context profiling: per-module,
  per-stage and per-trait installation costs, with the instrumentation
  patches and an upstream-main source check. Measured by Codex on
  2026-09-13; formerly its own repository, folded in here unchanged apart
  from the crate name. Raw results and provenance in its `results/`.

- `fs-portability/`: record 0035 filesystem code and unit gates type-checked for Windows independently of the TLS toolchain; no Windows execution claim.
- Record 0037 extends `fs-portability/` to type-check the path module. Its
  before/after measurement driver is `scripts/measure_path_0037.py`; raw
  startup timings, binary hashes, session memory and test totals are in
  `results/path_0037_*`. Run the driver from the repository root with the
  before and after release binary paths as its two arguments.
- `time-candidates/` — three one-file binaries (jiff 0.2.24, chrono 0.4.44,
  time 0.3.47) doing the five things record 0038 needs: now as RFC 3339,
  a negative timestamp, local time under `TZ=Europe/Paris`, parsing, and
  the overflow refusal. Sizes, build times and outputs in
  `results/time_0038_candidates.txt`. Basis for record 0038's crate choice.
