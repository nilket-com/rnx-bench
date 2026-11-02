# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes, with
rerunnable harnesses, output checks and retained results.

rnx `83d94173` pins public [Rune N5](https://github.com/nilket-com/rune/commit/2565a2a4563a915d49de061931f2951fd5dede31).
`rnx run` enables its native tier by default. The same binary supports
`--native=off` and `--engine=legacy`. The pinned production binary passed native
entry/return witnesses, including fib with the default native setting and budget.

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
recursion. Sieve also has interpreted surrounding methods. `permute` and
`shared_rows` remain interpreted; the native tier does not handle their method
calls or string/table search.

<!-- current-matrix:start -->

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

† = thermally throttled batch; n/a = no matching port. All cells are milliseconds,
mean ± sample standard deviation. [Conditions, versions and provenance](results/cross-runtime-2026-11-02.md).

<!-- current-matrix:end -->

## Reproduction

Build the exact locked rnx production revision and retain its build receipt,
including clean source directories and the executable hash. The runtime
prerequisites and JVM jar build instructions are documented in
[scripts/jvm](scripts/jvm/README.md). Run from this repository's root:

```sh
python3 -I -B scripts/build_matrix_rnx.py target/readme-n5-build
export JULIAUP_NO_SELFUPDATE=1
JULIA_REAL="$(julia --startup-file=no -e 'print(joinpath(Sys.BINDIR,Base.julia_exename()))')"
JULIA_SYSIMAGE="$(julia --startup-file=no -e 'print(unsafe_string(Base.JLOptions().image_file))')"
python3 -I -B scripts/current_matrix.py --build target/readme-n5-build/BUILD.json --out target/readme-n5-new-run --julia "$JULIA_REAL" --julia-sysimage "$JULIA_SYSIMAGE"
python3 -I -B scripts/render_current_matrix.py target/readme-n5-new-run
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

- [Cross-runtime startup and JSON, 2026-09-13](results/cross-runtime-2026-09-13.md)
  used rnx `3af1ccb` and Rune 0.14.2.
- [Native-tier probe, 2026-10-12](probes/rune-native-0184/RESULTS.md) used an
  experimental fork and warmed per-invocation slopes. Its calls target passed;
  two controls were accepted by exception. That method differs from the
  whole-process matrix above. Its archived source/binary availability statements
  describe that checkpoint, while the current N5 engine is public.
- [Rune base 0168](probes/rune-base-0168/README.md),
  [interpreter profile 0170](probes/interp-profile-0170/README.md),
  [Rust-hosted Lua](probes/lua-rust-0001/README.md),
  [HTTP 0164](probes/web-0164/README.md),
  [context registration](probes/context-registration/README.md), and
  [standalone rustc](results/rustc-42/summary.md) retain their own conditions.

The full record-specific catalogue is in [probes/README.md](probes/README.md).
