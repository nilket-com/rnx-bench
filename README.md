# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes, with
rerunnable harnesses, output checks and retained results.

rnx `c32a6ba7` pins public [Rune N6](https://github.com/nilket-com/rune/commit/a68e739e6213dd02877258503f16df7ddaae6fc7).
`rnx run` enables its native tier by default. The same binary supports
`--native=off` and `--engine=legacy`. The pinned production binary passed native
entry/return witnesses for permute and two additional method fixtures, including
a field loop with the default native setting and budget.

## Current cross-runtime matrix

Measured on an **Intel i7-14700** measurement host, pinned to CPU 4, with
hyperfine `-N` (no shell). Every cell includes startup, compilation and native
preparation; first recursive calls can fall back to the interpreter and are
included. Compute cells run 16 kernel calls, except the million-element list
cases, which run once. Fast compute cells therefore include a substantial
startup component. rnx compute commands use `--budget 1099511627775` rather than
the CLI default of 2,000,000; other runtimes have no equivalent work limit.
Startup and JSON use the default budget. Every included cell must pass its
exit-status and output-equivalence checks before any timing begins.

Single-CPU affinity penalizes runtimes with parallel JIT/GC work, including JVM,
Julia, Deno and Bun. Throttled batches are marked inline. Each kernel stands
alone: there is no aggregate score. Encoder choice, allocation and API behavior
differ across JSON implementations; the JSON table does not isolate language
implementation. The ± values show sample spread, not confidence intervals.

The list columns include construction and eight reads. Native regions handle
admitted scalar loops, integer/Boolean list loops and scalar direct self
recursion. Permute uses a guarded named receiver with scalar fields, one integer
list, closed helpers and self recursion; its setup and verification stay
interpreted. Sieve also has interpreted surrounding methods. `shared_rows` keeps
its string/table search in the interpreter.

<!-- current-matrix:start -->

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

† = thermally throttled batch; n/a = no matching port. All cells are milliseconds,
mean ± sample standard deviation. [Conditions, versions and provenance](results/cross-runtime-2026-11-02-c32a6ba7.md).

<!-- current-matrix:end -->

## Reproduction

Build the exact locked rnx production revision and retain its build receipt,
including clean source directories and the executable hash. The runtime
prerequisites and JVM jar build instructions are documented in
[scripts/jvm](scripts/jvm/README.md). Run from this repository's root:

```sh
python3 -I -B scripts/build_matrix_rnx.py target/readme-n6-build
export JULIAUP_NO_SELFUPDATE=1
JULIA_REAL="$(julia --startup-file=no -e 'print(joinpath(Sys.BINDIR,Base.julia_exename()))')"
JULIA_SYSIMAGE="$(julia --startup-file=no -e 'print(unsafe_string(Base.JLOptions().image_file))')"
python3 -I -B scripts/current_matrix.py --build target/readme-n6-build/BUILD.json --out target/readme-n6-new-run --julia "$JULIA_REAL" --julia-sysimage "$JULIA_SYSIMAGE"
python3 -I -B scripts/render_current_matrix.py target/readme-n6-new-run
```

The harness validates every output before invoking hyperfine, records versions,
source/binary/jar hashes and thermal counters, and excludes cooperating jobs
using the measurement lease. It reports only a terminal result. Raw samples and
logs stay in the ignored run directory; the compact result summaries and tables
are committed. The renderer requires a passing receipt and all expected sample
counts. See the current results for exact source pins, runtime locations and
command semantics.

The older `./run_bare.sh` and `./run_json_loop.sh` remain available; they overwrite
their historical working exports. They do not refresh the current matrix.

## Dated results and probes

Historical measurements describe their named binaries and method. They are not
relabelled as measurements of today's engine:

- [2026-11-02 N5 matrix](results/cross-runtime-2026-11-02.md) preserves the previous
  rnx `83d94173` / Rune `2565a2a4` snapshot.
- [Cross-runtime startup and JSON, 2026-09-13](results/cross-runtime-2026-09-13.md)
  used rnx `3af1ccb` and Rune 0.14.2.
- [Native-tier probe, 2026-10-12](probes/rune-native-0184/RESULTS.md) used an
  experimental fork and warmed per-invocation slopes. Its calls target passed;
  two controls were accepted by exception. That method differs from the
  whole-process matrix above. Its archived source/binary availability statements
  describe that checkpoint, while the current N6 engine is public.
- [Rune base 0168](probes/rune-base-0168/README.md),
  [interpreter profile 0170](probes/interp-profile-0170/README.md),
  [Rust-hosted Lua](probes/lua-rust-0001/README.md),
  [HTTP 0164](probes/web-0164/README.md),
  [context registration](probes/context-registration/README.md), and
  [standalone rustc](results/rustc-42/summary.md) retain their own conditions.

The full record-specific catalogue is in [probes/README.md](probes/README.md).
