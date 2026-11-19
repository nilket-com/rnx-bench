# Source to completion on Strix · November 19, 2026

Measured on Strix (Intel Core i9-14900K) on November 19, 2026, using published rnx `6e96db98`. Values are **milliseconds from source to exit, median of 12 samples**, with all processes pinned to CPU 4. Lower is faster. Each compute process runs 16 kernel calls, except the million-element lists, which run once. A dash marks an unmeasured cell.

| Runtime | Print 42 | 10k JSON | Fib | Loops | Numeric calls | AWFY Sieve | AWFY Permute |
|---|---:|---:|---:|---:|---:|---:|---:|
| rnx | 4.51 | 18.36 | 13.30 | 5.50 | 5.73 | 7.11 | 22.35 |
| rnx native off | 4.62 | 18.24 | 21.19 | 8.63 | 11.39 | 13.77 | 41.83 |
| rnx legacy | 4.45 | 13.90 | 31.81 | 19.90 | 25.37 | 33.99 | 71.85 |
| Haskell (runghc) | 67.58 | — | 194.78 | 149.61 | 183.74 | 196.56 | 282.02 |
| Haskell (GHC -O2, build + run) | 242.66 | — | 283.56 | 284.28 | 283.80 | 303.56 | 322.96 |
| LuaJIT | 1.69 | 14.47 | 2.29 | 2.66 | 2.67 | 2.26 | 2.95 |
| Lua 5.4 | 1.56 | 29.46 | 6.14 | 2.51 | 4.30 | 3.85 | 11.50 |
| Bun | 2.85 | 4.40 | 5.89 | 4.37 | 6.89 | 4.97 | 8.68 |
| Node | 11.31 | 14.42 | 12.59 | 13.17 | 12.94 | 14.27 | 15.74 |
| Deno | 41.50 | 83.41 | 44.15 | 44.21 | 42.99 | 44.09 | 46.29 |
| Python | 7.33 | 22.65 | 14.51 | 11.13 | 12.62 | 11.03 | 16.68 |
| Perl | 2.00 | 48.68 | — | — | — | — | — |
| Kotlin | 2,773.37 | 3,135.97 | — | — | — | — | — |
| Scala | 2,216.93 | 2,846.94 | — | — | — | — | — |

| Runtime | List i64 | List bool | Shared rows | 1M i64 | 1M bool |
|---|---:|---:|---:|---:|---:|
| rnx | 8.14 | 8.11 | 4.74 | 31.80 | 31.99 |
| rnx native off | 30.67 | 39.26 | 4.67 | 167.81 | 222.90 |
| rnx legacy | 111.79 | 127.27 | 4.66 | 674.25 | 766.53 |
| Haskell (runghc) | 556.27 | 579.75 | — | 2,976.75 | 3,101.11 |
| Haskell (GHC -O2, build + run) | 327.58 | 322.84 | — | 334.17 | 330.34 |
| LuaJIT | 3.10 | 9.55 | 1.76 | 8.32 | 34.42 |
| Lua 5.4 | 17.27 | 17.81 | 1.70 | 98.56 | 101.05 |
| Bun | 9.23 | 9.52 | — | 31.09 | 34.40 |
| Node | 20.42 | 20.50 | — | 53.23 | 56.11 |
| Deno | 52.66 | 54.47 | — | 134.10 | 87.10 |
| Python | 22.65 | 21.80 | — | 103.96 | 100.05 |

## What the timer includes

The timer starts immediately before launching the runtime or compiler. It stops after the program has exited and its output has been collected. Each invocation gets a fresh process and an empty temporary directory. Source generation, toolchain installation, fetching library dependencies and deletion of scratch output are outside the timer. Operating-system file caches stay warm.

- **rnx** reads the fixture's `.rn` file with the published default-feature release executable. The three rows select default execution, native off and the legacy engine. Compute uses a work budget of `2^40 − 1`.
- **Haskell** uses a separate [single-module source file](../scripts/haskell/from-source) for each workload. The print-only program is `main = print (42 :: Int)`. The direct script row runs `runghc Fixture.hs [rounds]`. The optimized row runs `ghc -O2 -fforce-recomp -outputdir DIR -o DIR/program Fixture.hs` followed immediately by that executable. Each invocation builds its own objects and executable. The standard library and the installed array package are available to both modes.
- **Kotlin and Scala** use the repository's [JVM source fixtures](../scripts/jvm). `kotlinc` and Scala's `dotty.tools.dotc.Main` compile to a fresh directory, followed by a new `java` process invoking the generated main class. The timing includes both process launches. The runtime libraries, org.json and ujson are already installed. These fixtures cover printing 42 and encoding JSON.
- **Python, Perl, JavaScript and Lua** execute source files, including for the print-only cells. Deno uses `--no-code-cache` and a fresh Deno directory. The driver disables Bun's persistent transpiler cache, Node's compile cache and Python bytecode writes. The Lua JSON rows use the pure-Lua encoder. Runtime binaries and installed libraries are reused throughout.

## Compiler and program times

Each number is the median of its own 12 observations. The two component medians can sum to a slightly different value from the median total.

| Runtime | Fixture | Build (ms) | Run (ms) | Total (ms) |
|---|---|---:|---:|---:|
| Haskell (GHC -O2, build + run) | Print 42 | 240.52 | 2.10 | 242.66 |
| Haskell (GHC -O2, build + run) | AWFY Sieve | 301.19 | 2.36 | 303.56 |
| Haskell (GHC -O2, build + run) | AWFY Permute | 319.85 | 3.08 | 322.96 |
| Kotlin | Print 42 | 2,758.19 | 15.35 | 2,773.37 |
| Kotlin | 10k JSON | 3,056.09 | 78.96 | 3,135.97 |
| Scala | Print 42 | 2,125.73 | 93.12 | 2,216.93 |
| Scala | 10k JSON | 2,655.18 | 191.28 | 2,846.94 |

The [earlier Strix run](language-comparison-2026-11-19.md) measured launch and execution of an already compiled Haskell program and varied work per process. Those results remain useful for repeated execution of a built binary.

## Verification and provenance

All 130 runtime/workload combinations passed the prior fixture checksum or canonical JSON check before timing, during two warmups and on every measured run. Sieve returns 669 per call and Permute returns 8,660. The list fixtures construct each list once per kernel call and scan it eight times, including the million-element cases. JSON cells serialize 10,000 times and print the last value. Encoder choices differ across runtimes.

The driver shuffles all cells in each block with seed 20261120. Runs are sequential on strix, Intel(R) Core(TM) i9-14900K, Linux 7.0.0-31-generic. Thermal throttle counters over the timed blocks were core 112,348 → 112,348, package 3,450,731 → 3,450,731.

Toolchains were GHC 9.10.3, Kotlin 2.4.20, Scala 3.9.0, OpenJDK 25.0.5, LuaJIT 2.1.1788856981, Lua 5.4.7, Bun 1.4.2, Node 22.22.1, Deno 2.9.6, Python 3.14.4 and Perl 5.40.1. The [rnx source revision](https://github.com/nilket-com/rnx/commit/6e96db9815971789cc4d9e1b25d8337b4728252f) and release executable were the same as in the earlier Strix run. Its archive build omits embedded Git revision metadata.

Raw commands, fixture hashes, individual nanosecond samples, compiler-phase splits and thermal counters are retained outside Git in `target/source-comparison-2026-11-19/RESULT.json`. SHA-256 `2d30344547c2e393125da9b398b96f2ccf30f4a6ceb17ee17d4217722a669a7a`.
