# Cross-runtime matrix, 2026-11-02 (UTC)

Intel i7-14700, Linux 7.0.0-31-generic; CPU 4 affinity inherited by
all child threads. rnx `83d94173`, public Rune N5 `2565a2a4`. Default native
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
| rnx default | 3.065 ± 0.026 | 13.880 ± 0.257 |
| rnx native off | 3.065 ± 0.046 | 14.689 ± 0.503 |
| rnx legacy | 3.075 ± 0.029 | 13.745 ± 0.132 |
| Bun | 1.395 ± 0.023 | 2.817 ± 0.130 |
| Node official | 10.074 ± 0.227 | 13.201 ± 0.352 |
| Node distro | 51.712 ± 0.313 | 54.801 ± 0.632 |
| Deno | 9.346 ± 0.536 | 9.294 ± 0.509 |
| Python | 6.156 ± 0.122 | 22.931 ± 0.429 |
| Perl JSON::PP | 0.553 ± 0.017 | 52.436 ± 0.661 |
| Perl JSON::XS | 0.551 ± 0.016 | 6.319 ± 0.059 |
| Ruby | 26.559 ± 0.223 | 36.275 ± 0.232 |
| LuaJIT cjson | 0.316 ± 0.012 | 6.389 ± 0.155 |
| LuaJIT json.lua | 0.319 ± 0.012 | 13.883 ± 0.522 |
| Lua 5.4 cjson | 0.295 ± 0.010 | 7.167 ± 0.064 |
| Lua 5.4 json.lua | 0.287 ± 0.010 | 30.506 ± 0.431 |
| Kotlin jar | 25.375 ± 1.268 | 82.896 ± 3.477 |
| Scala jar | 88.670 ± 1.254 | 196.034 ± 4.051 |
| Julia | 96.019 ± 0.734 | 347.280 ± 8.160 |
| R | 71.407 ± 2.371 | 783.510 ± 14.114 |

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
native. That first-call behavior is included here. `permute` and `shared_rows`
remain interpreted; N5 adds neither method dispatch nor string/table search.

| Runtime | fib | loops | numeric calls | sieve | permute † | shared rows | list i64 † | list bool † | 1M i64 † | 1M bool † |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rnx default | 12.935 ± 0.141 | 4.331 ± 0.058 | 4.491 ± 0.068 | 6.074 ± 0.063 | 48.002 ± 0.907 | 3.435 ± 0.116 | 7.102 ± 0.093 | 6.999 ± 0.105 | 32.256 ± 0.481 | 32.937 ± 0.445 |
| rnx native off | 22.090 ± 0.404 | 8.062 ± 0.162 | 11.096 ± 0.072 | 13.905 ± 0.096 | 47.683 ± 0.568 | 3.544 ± 0.053 | 32.651 ± 0.306 | 42.449 ± 0.529 | 199.552 ± 4.489 | 251.044 ± 11.568 |
| rnx legacy | 35.444 ± 0.777 | 20.361 ± 0.417 | 26.982 ± 0.330 | 37.091 ± 0.511 | 82.357 ± 1.486 | 3.543 ± 0.040 | 117.093 ± 1.562 | 137.125 ± 6.253 | 718.710 ± 15.721 | 837.530 ± 28.864 |
| Bun | 5.510 ± 1.567 | 3.524 ± 1.103 | 6.335 ± 1.859 | n/a | n/a | n/a | 8.696 ± 1.596 | 9.055 ± 1.612 | 32.372 ± 1.889 | 34.433 ± 0.728 |
| Node official | 11.635 ± 0.422 | 12.294 ± 0.207 | 12.326 ± 0.426 | n/a | n/a | n/a | 19.819 ± 0.657 | 20.267 ± 0.789 | 55.583 ± 0.715 | 58.562 ± 0.849 |
| Node distro | 54.831 ± 0.865 | 54.355 ± 0.495 | 54.738 ± 0.884 | n/a | n/a | n/a | 61.421 ± 1.323 | 60.178 ± 0.470 | 97.415 ± 4.892 | 100.947 ± 2.396 |
| Deno | 8.882 ± 0.240 | 8.722 ± 0.267 | 8.665 ± 0.527 | n/a | n/a | n/a | 15.686 ± 2.021 | 15.449 ± 1.893 | 49.109 ± 0.874 | 51.972 ± 0.640 |
| Python | 14.560 ± 0.186 | 10.579 ± 0.136 | 12.227 ± 0.143 | n/a | n/a | n/a | 23.427 ± 0.334 | 22.240 ± 0.230 | 112.846 ± 0.385 | 112.435 ± 1.745 |
| LuaJIT | 1.082 ± 0.062 | 1.581 ± 0.094 | 1.486 ± 0.020 | 0.979 ± 0.028 | 5.107 ± 10.093 ‡ | 0.406 ± 0.009 | 1.826 ± 0.030 | 8.798 ± 0.117 | 7.590 ± 0.127 | 42.836 ± 0.428 |
| Lua 5.4 | 5.498 ± 0.080 | 1.390 ± 0.036 | 3.257 ± 0.038 | 2.970 ± 0.150 | 11.582 ± 0.432 | 0.353 ± 0.009 | 17.459 ± 0.333 | 18.965 ± 0.328 | 108.402 ± 4.482 | 110.209 ± 2.422 |

Perl, Ruby, Kotlin, Scala, Julia and R have startup/JSON cells only. Compute uses one fixed cjson-labelled capture for each Lua runtime, without averaging the encoder-labelled duplicates.

‡ LuaJIT permute: median 1.935 ms, maximum 52.664 ms. Its standard deviation exceeds its mean; extreme samples dominate the mean. This batch also showed thermal throttling (†).

### Reading the tables

From the rendered sample means, rnx default is 1.71× faster than native off on fib, rnx default is 4.60× faster than native off on the integer list, and rnx default is 6.07× faster than native off on the Boolean list. Against LuaJIT, LuaJIT is 11.95× faster than rnx default on fib and LuaJIT is 3.89× faster than rnx default on the integer list, while rnx default is 1.26× faster than LuaJIT on the Boolean list. On numeric calls, rnx default is 1.41× faster than Bun, rnx default is 2.74× faster than official Node, and rnx default is 2.72× faster than Python. At startup, LuaJIT is 9.70× faster than rnx default and Bun is 2.20× faster than rnx default. These are ratios of whole-process sample means, not confidence-bound rankings; permute and shared_rows remain interpreted.

## Versions and provenance

- **rnx default**: rnx 0.0.0; rune 0.15.0 (git 2565a2a4563a915d49de061931f2951fd5dede31)
- **rnx native off**: rnx 0.0.0; rune 0.15.0 (git 2565a2a4563a915d49de061931f2951fd5dede31)
- **rnx legacy**: rnx 0.0.0; rune 0.15.0 (git 2565a2a4563a915d49de061931f2951fd5dede31)
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
[machine-readable summary](cross-runtime-2026-11-02.json). The Kotlin/Scala source
and build instructions are in [scripts/jvm](../scripts/jvm/README.md).
These rows describe the identified artifacts, not arbitrary installations.

Rerun from the repository root after building the pinned production CLI with
the normal locked feature set and retaining its BUILD.json (commit, Rune pin,
clean source directories, executable hash/size):

```sh
python3 -I -B scripts/build_matrix_rnx.py target/readme-n5-build
export JULIAUP_NO_SELFUPDATE=1
JULIA_REAL="$(julia --startup-file=no -e 'print(joinpath(Sys.BINDIR,Base.julia_exename()))')"
JULIA_SYSIMAGE="$(julia --startup-file=no -e 'print(unsafe_string(Base.JLOptions().image_file))')"
python3 -I -B scripts/current_matrix.py --build target/readme-n5-build/BUILD.json --out target/readme-n5-new-run --julia "$JULIA_REAL" --julia-sysimage "$JULIA_SYSIMAGE"
python3 -I -B scripts/render_current_matrix.py target/readme-n5-new-run
```

The harness uses the exact Rune/rnx sources named by that receipt, installed
runtimes on PATH, the official Node binary at `~/opt/node-v22.22.1-linux-x64/bin/node`,
`~/opt/json.jar`, and the prebuilt JVM jars. The old shell runners remain
available for the dated suites. New raw hyperfine JSON, validation output,
commands, complete input hashes and logs live only in the ignored run directory;
the compact summary is committed. Rendering validates successful terminal
receipts and sample counts before replacing tables or README content.
