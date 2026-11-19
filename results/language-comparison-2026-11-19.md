# rnx across runtimes on Strix · 2026-11-19

Published rnx `6e96db98`, default-feature locked release build. Intel(R) Core(TM) i9-14900K, Linux 7.0.0-31-generic, CPU 4. Whole-process milliseconds, median of 12 measurements after two warmups per cell. Lower is faster.

## Language fixtures

| Runtime | Startup | 10k JSON | Fib | Loops | Numeric calls | AWFY Sieve | AWFY Permute |
|---|---:|---:|---:|---:|---:|---:|---:|
| rnx | 4.14 | 18.16 | 12.86 | 5.27 | 5.84 | 6.84 | 22.27 |
| rnx native off | 4.19 | 18.02 | 21.08 | 8.61 | 11.23 | 13.79 | 41.80 |
| rnx legacy | 4.15 | 13.69 | 31.72 | 19.68 | 25.01 | 33.76 | 71.73 |
| Haskell (GHC -O2) | 1.98 | — | 2.24 | 2.43 | 2.60 | 2.10 | 2.69 |
| LuaJIT | 1.65 | 13.76 | 2.18 | 2.80 | 2.70 | 2.17 | 4.15 |
| Lua 5.4 | 1.69 | 29.36 | 6.18 | 2.55 | 4.21 | 3.84 | 11.42 |
| Bun | 2.80 | 4.00 | 5.25 | 4.53 | 6.95 | 4.48 | 8.61 |
| Node | 10.95 | 13.99 | 12.37 | 12.84 | 13.00 | 13.83 | 15.81 |
| Deno | 13.30 | 14.67 | 14.95 | 13.97 | 14.91 | 14.56 | 17.28 |
| Python | 7.17 | 22.30 | 14.34 | 10.92 | 12.59 | 11.01 | 16.44 |
| Perl | 1.97 | 48.47 | — | — | — | — | — |

| Runtime | List i64 | List bool | Shared rows | 1M i64 | 1M bool |
|---|---:|---:|---:|---:|---:|
| rnx | 7.94 | 8.16 | 4.61 | 31.23 | 31.60 |
| rnx native off | 30.23 | 39.22 | 4.43 | 167.57 | 222.94 |
| rnx legacy | 111.30 | 126.99 | 4.53 | 673.83 | 765.83 |
| Haskell (GHC -O2) | 3.00 | 3.13 | — | 8.86 | 10.06 |
| LuaJIT | 2.99 | 9.31 | 1.72 | 8.02 | 34.00 |
| Lua 5.4 | 17.29 | 18.03 | 1.70 | 97.99 | 101.09 |
| Bun | 9.34 | 9.23 | — | 30.96 | 32.21 |
| Node | 20.27 | 20.45 | — | 53.33 | 55.79 |
| Deno | 20.76 | 20.02 | — | 52.71 | 55.36 |
| Python | 22.59 | 21.96 | — | 103.71 | 99.67 |

Each compute process runs 16 kernel calls except the million-element lists, which run once. The vectors include construction and eight scans. JSON means 10,000 encodes, including the process launch. The Lua rows use the same pure-Lua encoder. Dashes indicate unmeasured cells. The broader historical table includes alternate encoders, distro Node, Ruby, JVM languages, Julia and R. [November 2 N6 matrix](cross-runtime-2026-11-02-c32a6ba7.md)

## Work per process in rnx and Haskell

Both runtimes ran all three call counts within each measurement block. The last columns are median within-block changes in milliseconds per extra call, calculated as (128-call time − 16-call time) / 112. The 64-call measurements expose curvature. These are end-to-end measurements from separate processes.

| Fixture | rnx 16 | 64 | 128 | GHC 16 | 64 | 128 | Additional call in rnx | Additional call in GHC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fib | 12.86 | 25.98 | 43.60 | 2.24 | 3.58 | 5.28 | 0.2739 | 0.0269 |
| Loops | 5.27 | 6.43 | 8.06 | 2.43 | 4.58 | 7.02 | 0.0240 | 0.0408 |
| Numeric calls | 5.84 | 6.92 | 8.74 | 2.60 | 4.58 | 7.13 | 0.0266 | 0.0408 |
| AWFY Sieve | 6.84 | 9.60 | 13.02 | 2.10 | 2.83 | 3.63 | 0.0554 | 0.0138 |
| AWFY Permute | 22.27 | 36.01 | 54.22 | 2.69 | 4.26 | 5.95 | 0.2861 | 0.0295 |
| List i64 | 7.94 | 15.37 | 25.19 | 3.00 | 6.17 | 9.98 | 0.1536 | 0.0622 |
| List bool | 8.16 | 15.61 | 25.51 | 3.13 | 7.13 | 12.27 | 0.1560 | 0.0818 |

## Measurement details

All 144 timed cells passed output checks both before timing and on every invocation. AWFY Sieve returns 669 per call and Permute returns 8,660. These are the two routing-matrix AWFY kernels. They use mutable flags, and recursive permutation counting with swap and swap-back, respectively. Each port verifies its result. The Haskell list kernels use unboxed mutable arrays. Haskell was compiled ahead of time with GHC 9.10.3 and `-O2`. The timings exclude that compilation. rnx script preparation is included. Native-off and legacy are explicitly selected only on their labeled rows.

Every block shuffles the order across runtimes, workloads and call counts with a recorded seed. One process ran at a time with affinity inherited from the driver. Each timing includes process creation and collection of its output. Single-CPU affinity can affect runtimes that use parallel compilation or collection. Independent per-process checksums detect result differences but do not force compilers to perform identical machine work.

The core and package thermal throttle counters were unchanged across all timed blocks.

Runtime versions were GHC 9.10.3, LuaJIT 2.1.1788856981, Lua 5.4.7, Bun 1.4.2, Node 22.22.1, Deno 2.9.6, Python 3.14.4 and Perl 5.40.1.

The measurement built a Git archive of the published revision. Exact commands, fixture hashes, executable hashes, run order and individual samples are in the [local receipt](../target/language-comparison-2026-11-19/RESULT.json), SHA-256 `6d35f2fe572a20172e31c16c15702902dac80d9c163d9583350c83c7528d9dfa`. [Measurement driver](../target/language-comparison-2026-11-19/input/measure.py) · [Haskell AWFY fixtures](../target/language-comparison-2026-11-19/input/Witness.hs).
