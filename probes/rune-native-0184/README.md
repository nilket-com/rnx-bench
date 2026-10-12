# 0184: Rune native tier versus LuaJIT (ARCHIVAL probe sources)

Results: [RESULTS.md](RESULTS.md).

The files here are **byte-identical archival copies** of the sealed FUEL probe
package that produced those results. They are published so the method can be
read and checked. They are **not runnable from an arbitrary checkout** without
adaptation (see "What blocks a rerun"), and the exact engine source is not yet
publicly available, so **public end-to-end reproduction is pending**. Nothing
here implies a rerun was made from this directory.

## What it measures

Warmed per-invocation cost of small Rune kernels under Rune's experimental
native tier (a Cranelift tier inside the fresh-core VM), against LuaJIT with
and without its JIT, and against Rune's own interpreter.

Subjects:

- `fuel-on`: harness built from Rune fork commit
  346623b6c9ee33f15ea1bca3c143723e9e147d07 (branch `fuel/guarded-fold`, parent
  e1e1f30b), feature `native` (= `rune/fresh-core-native` + `rune/fresh-core`);
- `fuel-off`: the same source, harness lock and profile, without `native`;
- `luajit`: LuaJIT 2.1.1788856981 (built from LuaJIT commit c6ffc14), defaults;
- `luajit-joff`: the same binary with `-joff`.

That commit lives on a local branch of the Rune fork and is **not published**.
The fork's public main does not contain the native tier.

## Kernels

`kernels/*.rn` and `kernels/*.lua` are matching workload implementations (syntax,
line counts and numerical semantics differ, as the caveats disclose); each exports
`main(x)`.

| kernel | body | role |
|---|---|---|
| calls | `for i in 0..x { total = add(total, i) }` with `fn add(a, b) { a + b }` | sole primary (target ratio upper ≤ 1.25) |
| while | `while n < x { n += 1 }` | acceptance screen |
| numeric | `while n < x { total += n % 17; n += 1 }` | acceptance screen |
| fib | recursive `fib(x)` | control (fuel-on/fuel-off, upper ≤ 1.01) |
| shared_rows | small Vec-of-rows update with clone and alias | control (fuel-on/fuel-off, upper ≤ 1.01) |

## Inputs and K

`gen_inputs.py` draws each stream i.i.d. from Python's Mersenne Twister
(`getrandbits`) with seed **3028974873822931333**, and computes every expected
result with an independent Python model that runs the loops literally (all
intermediates asserted within ±2^31, so LuaJIT doubles and Rune's checked i64
agree exactly). The generated inputs (about 4.5 MB) are not committed;
`inputs/MANIFEST.json` (committed, sha256 `516720926a7b…490f`) records every
stream's sha256, range, prefix/tail statistics and expected checksums.

| cell | stream range | K1 | K2 |
|---|---|---|---|
| calls/calls_main | 9,000–11,000 | 100 | 10,100 |
| calls/tiny (fixed-cost diagnostic) | 0–3 | 1,000 | 101,000 |
| while/loop_main | 9,000–11,000 | 1,000 | 101,000 |
| numeric/loop_main | 9,000–11,000 | 1,000 | 101,000 |
| fib/fib_main | 18–21 | 100 | 10,100 |
| shared_rows/shared_rows_main | 0–1,000,000 | 1,000 | 101,000 |

## Design

- Each child process runs one kernel K times on the first K inputs, folding
  results into a checksum (`harness-rune/src/main.rs`, `harness-lua/repeat-input-v3.lua`).
  A block runs K1 and K2 back to back; the block slope is
  (wall(K2) − wall(K1)) / (K2 − K1) ns per invocation, wall time from the
  parent's CLOCK_MONOTONIC. Process start, input reading and output are
  therefore included in each wall time but cancel in the slope only to the
  extent they are equal between K1 and K2.
- Paired rounds: 10 rounds per cell; a round runs one block of every subject of
  the cell in a seeded random order, K order seeded too; rounds of all cells are
  interleaved in seeded order (SESSION-SEED.txt, 16553042724352686932). 200
  blocks, 400 children.
- Validity: rc 0, empty stderr, exact checksum line and, for Rune, the MAPS line
  (anonymous executable mappings, which shows whether native code was loaded).
  Invalid samples are kept, never retried; any invalid sample suppresses every
  interval.
- Readiness flags (pre-registered): load1 ≤ 1.5, MemAvailable ≥ 4 GiB, no new CPU
  4 thermal throttle during the block. Flagged blocks stay in the primary; a
  sensitivity analysis on complete unflagged rounds is reported beside it.
- Analysis (`analyze.py`): joint paired-round percentile bootstrap, B = 10,000,
  one vector of round indices per resample shared by every subject of the cell,
  seeded from BOOT-SEED.txt (12259218818769717712). Ratios with marginal 95%
  intervals, unrounded, each read on its own; no aggregate across kernels.
- Decision rules were sealed before the session. `test_analyze.py` holds the
  analyzer's synthetic controls (fabricated sessions; nothing timed).
- Timed children run under `taskset -c 4`, stdin /dev/null, per-child timeout
  120 s, all-phases session bound 5,400 s.

This is a slope-per-invocation method with its own repetition harness. It is
**not interchangeable** with the hyperfine whole-process timings in the
top-level README tables.

## Conditions

- Machine: nano, Intel Core i7-14700 (microcode 0x133), Linux 7.0.0-31-generic,
  64 GB RAM; logical CPU 4 for timed children; governor powersave, turbo on, SMT on.
- Session: 2026-10-12, start 01:20 -05:00, 971 s.
- Rust: rustc 1.98.1 (48a229cea 2026-09-01), cargo 1.98.1, LLD 22.1.8 (rust-lld),
  cc gcc 15.2.0; Cranelift 0.135.5.
- Profile: `cargo build --release --locked -j8 [--features native]`,
  `CARGO_INCREMENTAL=0`; opt-level 3, codegen-units 16, no LTO, panic unwind, no
  debug info (spelled out in `harness-rune/Cargo.toml`). Cranelift targets
  baseline x86-64.
- Python 3.14.4 for the controller, analyzer and generator.

## Pins (PINS.json, summarised; not distributed)

PINS.json (sha256 `4b3bee21ae5c…e3e3`) holds machine paths and binary hashes. Its
content that matters:

| pin | value |
|---|---|
| Rune commit | 346623b6c9ee33f15ea1bca3c143723e9e147d07 (tree a3ee0104…) |
| Rune base | e1e1f30bc87e3feb55da55e3ee5f0448f9bdc4c4 |
| Rune workspace Cargo.lock (gitignored in the fork) | 54422608ab72af88e9fa5d5ecc3286690cb3d14448f05b7931c28f9b4df41fdc |
| harness Cargo.lock (committed here) | b65e3a87220f0d6932caec8a5852c00a2865554a091d0e6250461ea3d326e22d |
| harness Cargo.toml | 5974e69fad5fdf2b3bd6cc45d52036594a40cbef7297813fee09b73261d95cd8 |
| harness main.rs | 98496e58755674f15732037aefb294aafa36f0580c34d377cf3814513a2b50d8 |
| fuel-on binary | 1bf2751753d291bb42090275ee994a133380a4b7d2576d82db736906b53ec971 |
| fuel-off binary | 7eeb0bf23cff195c5a5b0c00a7e83311f95c45fb240a7e1a2f40ce88b75b939d |
| LuaJIT binary (2.1.1788856981, commit c6ffc14) | a1ff02fbce1ed98f3e384e560158a456ffc26d43badac7a31e424af616c68320 |
| rustc binary | 859254978c0a0402c32f949f6de0d99aee73be8d15f45aac00ae1448aac51e74 |

Copied probe files covered by the sealed PINS.json match their entries
(controller.py `bc86ab73…`, analyze.py `4ae6b11f…`, test_analyze.py `8705377…`,
gen_inputs.py `13d3ef40…`, build.sh `4dd4a089…`, kernels, harnesses, seeds,
MANIFEST.json); copied tools match the sealed package. README.md, RESULTS.md
and the repository layout are publication additions.

## What blocks a rerun from this directory

- **Engine source**: commit 346623b6 is not public; the harness depends on it by
  an absolute path to a local worktree.
- **Absolute paths**: build.sh, the tools, the harness Cargo.toml and PINS.json
  name directories on the measuring machine (review, worktree and target
  directories, and the LuaJIT install). They were kept as measured, as in
  probes/rune-base-0168.
- **PINS.json is absent**: controller.py, analyze.py and test_analyze.py load it
  at import, and analyze.py refuses to run unless its own hash matches its pin.
- **inputs/ is absent** apart from MANIFEST.json; regenerate with gen_inputs.py
  and the seed above, then check the hashes against the manifest.
- **Prior-raw refusal controls**: test_analyze.py reads earlier sessions' raw
  files from local, undistributed receipt directories to prove the analyzer
  refuses them.
- **Layout and references**: in the sealed package `tools/` sat beside the probe
  directory, and the tools write logs into that package by absolute path.
  Docstrings cite sibling files of the sealed package (review go-aheads,
  READINESS.md, LAUNCH-COMMANDS.txt) and earlier probe revisions; none of
  those is distributed.
- `controller.py run` refuses any seed but the sealed SESSION-SEED.txt, and the
  tools hold a host-specific lock file and disk-space admission rules.

Adapting it means: publish the engine commit, rewrite the paths, rebuild both
subjects and LuaJIT, write a new PINS.json for the new binaries, regenerate the
inputs, and seal a new session seed. Such a rerun would be a new session, not
this one.

## Files

- `controller.py`: schedule, validation and the timed session (writes raw.jsonl).
- `analyze.py`: the sealed analyzer (raw.jsonl → RESULTS.json).
- `test_analyze.py`: synthetic controls for both.
- `gen_inputs.py`: input streams, expected results and MANIFEST.json.
- `build.sh`: the two Rune subject builds.
- `harness-rune/`, `harness-lua/`, `kernels/`, `inputs/MANIFEST.json`,
  `BOOT-SEED.txt`, `SESSION-SEED.txt`.
- `tools/`: launch readiness wait (`launch_ready.py`), native admission row check
  (`check_admit.py`), bounded build/test runner (`bounded.sh`), toolchain capture
  (`toolchain.sh`, environment keys and lengths only).
