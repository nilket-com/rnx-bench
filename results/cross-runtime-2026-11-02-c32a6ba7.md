# Cross-runtime matrix, 2026-11-02 (UTC)

Intel i7-14700, Linux 7.0.0-31-generic; CPU 4 affinity inherited by
all child threads. rnx `c32a6ba7`, public Rune N6 `a68e739e`. Default native
on, native off and legacy use the same locked production binary.

Times are **whole-process milliseconds, mean ± sample standard deviation**.
Startup, compilation, native preparation and recursive first-call fallback are
included. Compute runs call each kernel 16 times (seed `i % 97 + 1`); the two
million-element cases run once. Sixteen calls make the fast compute cells partly
a startup comparison. The rnx compute commands set `--budget 1099511627775`
(`2^40-1`), rather than the CLI default of 2,000,000; other runtimes have no
equivalent work limit. JSON and startup use the default budget.

Hyperfine `-N` executes without a shell: 5 warmups/50 samples for startup,
3 warmups/30 samples for JSON and compute. Startup evaluates **and prints** 42;
the JSON programs serialize 10,000 times and print the last value. Before any
timing, every included program exits 0, prints one line, and matches the other
implementations (sorted-key canonical JSON, otherwise an integer checksum).
JavaScript numbers stay within the exact-integer range on these inputs; Rune
additionally enforces checked integers and a work budget.

**† marks a thermally throttled batch**, from before/after core or package
throttle counters. Those wall times describe that session, with reduced
confidence in comparisons. No batches are silently replaced. CPU affinity
penalizes runtimes with parallel JIT/GC work, including JVM, Julia, Deno and Bun.
The ± values show observed spread, not a confidence interval or proof of a rank.
There is no aggregate score.

## Startup and JSON

Encoder choices and APIs differ; these timings do not isolate implementation
language. Lua and Perl rows retain both encoders. Node official and distro
builds are separate even when their version strings agree.
Lua's encoder suffix applies only to JSON; its compute programs do not call an
encoder. The compute table uses the fixed cjson-labelled sample set for each Lua
runtime, with duplicate encoder-labelled samples excluded from that table.

| Runtime | Startup | 10k JSON † |
|---|---:|---:|
| rnx default | 3.091 ± 0.050 | 13.516 ± 0.082 |
| rnx native off | 3.088 ± 0.026 | 13.478 ± 0.069 |
| rnx legacy | 3.090 ± 0.046 | 13.659 ± 0.260 |
| Bun | 1.405 ± 0.023 | 2.802 ± 0.129 |
| Node official | 10.093 ± 0.171 | 13.214 ± 0.330 |
| Node distro | 52.012 ± 1.894 | 54.605 ± 0.597 |
| Deno | 9.588 ± 0.477 | 9.115 ± 0.440 |
| Python | 6.162 ± 0.062 | 22.691 ± 0.220 |
| Perl JSON::PP | 0.563 ± 0.020 | 51.521 ± 0.738 |
| Perl JSON::XS | 0.552 ± 0.015 | 6.319 ± 0.095 |
| Ruby | 26.479 ± 0.239 | 35.785 ± 0.235 |
| LuaJIT cjson | 0.317 ± 0.014 | 6.348 ± 0.119 |
| LuaJIT json.lua | 0.317 ± 0.012 | 13.744 ± 0.532 |
| Lua 5.4 cjson | 0.294 ± 0.012 | 7.114 ± 0.098 |
| Lua 5.4 json.lua | 0.287 ± 0.007 | 30.427 ± 0.214 |
| Kotlin jar | 25.586 ± 1.198 | 82.979 ± 2.815 |
| Scala jar | 89.419 ± 1.357 | 194.717 ± 4.350 |
| Julia | 95.519 ± 1.855 | 349.595 ± 11.051 |
| R | 71.182 ± 0.354 | 782.030 ± 16.440 |

## Compute

`n/a` means no matching port in this refresh, not a failure or estimated time.
Lua pairs come from the pinned routing sources; JavaScript/Python ports cover
only simple scalar and list kernels. The million-element Lua sources use the
same list algorithm with its construction count changed from 10,000 to 1,000,000.
Each list case includes **both construction and eight reads**, rather than
claiming a separately timed append-only operation.

Native regions cover admitted scalar loops, homogeneous integer/Boolean list
reads/writes/iteration/appends, and scalar direct self recursion. `fib` and
numeric/list kernels use those paths. Sieve combines native list loops with
interpreted surrounding methods. Recursive first calls can replay in the
interpreter until sufficient engine stack room exists; later calls can complete
native. That first-call behavior is included here. Permute uses a guarded named
receiver with scalar fields, one integer list, closed helpers and self recursion;
its setup and verification stay interpreted. `shared_rows` keeps its string/table
search in the interpreter.

| Runtime | fib † | loops | numeric calls † | sieve † | permute † | shared rows | list i64 † | list bool † | 1M i64 † | 1M bool † |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rnx default | 13.087 ± 0.529 | 4.255 ± 0.080 | 4.579 ± 0.068 | 5.805 ± 0.058 | 23.445 ± 0.456 | 3.521 ± 0.078 | 7.021 ± 0.092 | 7.524 ± 0.256 | 32.373 ± 0.446 | 32.509 ± 0.215 |
| rnx native off | 22.239 ± 0.512 | 8.010 ± 0.146 | 10.987 ± 0.208 | 13.515 ± 0.146 | 45.981 ± 1.462 | 3.498 ± 0.069 | 32.522 ± 0.344 | 43.647 ± 0.954 | 193.915 ± 4.933 | 246.826 ± 10.401 |
| rnx legacy | 35.337 ± 0.625 | 20.639 ± 0.128 | 27.367 ± 1.438 | 34.975 ± 0.464 | 80.872 ± 2.291 | 3.512 ± 0.125 | 118.801 ± 3.012 | 140.749 ± 3.572 | 719.989 ± 16.675 | 851.567 ± 13.431 |
| Bun | 5.296 ± 1.337 | 3.659 ± 1.272 | 6.195 ± 1.923 | n/a | n/a | n/a | 8.727 ± 1.519 | 9.422 ± 1.184 | 32.238 ± 2.559 | 34.108 ± 1.433 |
| Node official | 11.784 ± 0.572 | 12.279 ± 0.537 | 12.234 ± 0.703 | n/a | n/a | n/a | 19.587 ± 0.704 | 20.070 ± 0.811 | 55.281 ± 0.324 | 58.042 ± 0.389 |
| Node distro | 55.368 ± 2.165 | 53.862 ± 0.577 | 54.182 ± 0.319 | n/a | n/a | n/a | 61.411 ± 3.368 | 61.069 ± 0.911 | 95.738 ± 0.984 | 99.675 ± 1.401 |
| Deno | 8.923 ± 0.256 | 8.780 ± 0.444 | 8.764 ± 0.706 | n/a | n/a | n/a | 14.551 ± 1.444 | 14.931 ± 1.678 | 49.236 ± 0.453 | 51.761 ± 0.577 |
| Python | 14.243 ± 0.253 | 10.824 ± 0.186 | 12.223 ± 0.178 | n/a | n/a | n/a | 23.628 ± 0.394 | 22.650 ± 0.317 | 113.640 ± 3.874 | 109.231 ± 2.120 |
| LuaJIT | 1.322 ± 0.268 | 1.522 ± 0.018 | 1.485 ± 0.018 | 0.970 ± 0.021 | 4.055 ± 5.023 ‡ | 0.409 ± 0.009 | 1.839 ± 0.022 | 9.231 ± 0.099 | 7.320 ± 0.201 | 42.809 ± 0.465 |
| Lua 5.4 | 5.437 ± 0.088 | 1.384 ± 0.041 | 3.511 ± 0.053 | 2.709 ± 0.035 | 12.244 ± 0.904 | 0.352 ± 0.005 | 17.438 ± 0.254 | 18.683 ± 0.385 | 103.973 ± 0.911 | 108.921 ± 0.865 |

Perl, Ruby, Kotlin, Scala, Julia and R have startup/JSON cells only. Compute uses one fixed cjson-labelled capture for each Lua runtime, without averaging the encoder-labelled duplicates.

‡ LuaJIT permute: median 1.898 ms, maximum 25.353 ms. Its standard deviation exceeds its mean; extreme samples dominate the mean. This batch also showed thermal throttling (†).

### Reading the tables

From the rendered sample means, rnx default is 1.70× faster than native off on fib and rnx default is 1.96× faster than native off on permute. rnx default is 4.63× faster than native off on the integer list, and rnx default is 5.80× faster than native off on the Boolean list. Against LuaJIT, LuaJIT is 9.90× faster than rnx default on fib and LuaJIT is 3.82× faster than rnx default on the integer list, while rnx default is 1.23× faster than LuaJIT on the Boolean list. On numeric calls, rnx default is 1.35× faster than Bun, rnx default is 2.67× faster than official Node, and rnx default is 2.67× faster than Python. At startup, LuaJIT is 9.75× faster than rnx default and Bun is 2.20× faster than rnx default. These are ratios of whole-process sample means, not confidence-bound rankings.

## Versions and provenance

- **rnx default**: rnx 0.0.0; rune 0.15.0 (git a68e739e6213dd02877258503f16df7ddaae6fc7)
- **rnx native off**: rnx 0.0.0; rune 0.15.0 (git a68e739e6213dd02877258503f16df7ddaae6fc7)
- **rnx legacy**: rnx 0.0.0; rune 0.15.0 (git a68e739e6213dd02877258503f16df7ddaae6fc7)
- **Bun**: 1.4.2
- **Node official**: v22.22.1
- **Node distro**: v22.22.1
- **Deno**: deno 2.9.6 (stable, release, x86_64-unknown-linux-gnu); v8 15.0.245.2-rusty; typescript 6.0.3
- **Python**: Python 3.14.4
- **Perl JSON::PP**: v5.40.1 JSON::PP=4.16
- **Perl JSON::XS**: v5.40.1 JSON::XS=4.04
- **Ruby**: ruby 3.3.8 (2025-04-09 revision b200bad6cd) [x86_64-linux-gnu]
- **LuaJIT cjson**: LuaJIT 2.1.1788856981 -- Copyright (C) 2005-2026 Mike Pall. https://luajit.org/
- **LuaJIT json.lua**: LuaJIT 2.1.1788856981 -- Copyright (C) 2005-2026 Mike Pall. https://luajit.org/
- **Lua 5.4 cjson**: Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio
- **Lua 5.4 json.lua**: Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio
- **Kotlin jar**: openjdk version "25.0.4.1" 2026-08-18; OpenJDK Runtime Environment (build 25.0.4.1+1-1-26.04.4-Ubuntu); OpenJDK 64-Bit Server VM (build 25.0.4.1+1-1-26.04.4-Ubuntu, mixed mode, sharing)
- **Scala jar**: openjdk version "25.0.4.1" 2026-08-18; OpenJDK Runtime Environment (build 25.0.4.1+1-1-26.04.4-Ubuntu); OpenJDK 64-Bit Server VM (build 25.0.4.1+1-1-26.04.4-Ubuntu, mixed mode, sharing)
- **Julia**: julia version 1.13.0
- **R**: Rscript (R) version 4.5.2 (2025-10-31)

Kotlin/Scala are precompiled jars on the listed JVM, so source compilation is
excluded but JVM startup/JIT is included. Jar hashes, binary hash, versions,
round counts, sample summaries and thermal counters are retained in the
[machine-readable summary](cross-runtime-2026-11-02-c32a6ba7.json). The Kotlin/Scala source
and build instructions are in [scripts/jvm](../scripts/jvm/README.md).
These rows describe the identified artifacts, not arbitrary installations.

Rerun from the repository root after building the pinned production CLI with
the normal locked feature set and retaining its BUILD.json (commit, Rune pin,
clean source directories, executable hash/size):

```sh
python3 -I -B scripts/build_matrix_rnx.py target/readme-n6-build
export JULIAUP_NO_SELFUPDATE=1
JULIA_REAL="$(julia --startup-file=no -e 'print(joinpath(Sys.BINDIR,Base.julia_exename()))')"
JULIA_SYSIMAGE="$(julia --startup-file=no -e 'print(unsafe_string(Base.JLOptions().image_file))')"
python3 -I -B scripts/current_matrix.py --build target/readme-n6-build/BUILD.json --out target/readme-n6-new-run --julia "$JULIA_REAL" --julia-sysimage "$JULIA_SYSIMAGE"
python3 -I -B scripts/render_current_matrix.py target/readme-n6-new-run
```

The harness uses the exact Rune/rnx sources named by that receipt, installed
runtimes on PATH, the official Node binary at `~/opt/node-v22.22.1-linux-x64/bin/node`,
`~/opt/json.jar`, and the prebuilt JVM jars. The old shell runners remain
available for the dated suites. New raw hyperfine JSON, validation output,
commands, complete input hashes and logs live only in the ignored run directory;
the compact summary is committed. Rendering validates successful terminal
receipts and sample counts before replacing tables or README content.
