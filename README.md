# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes, with
rerunnable harnesses, output checks and retained results.

The whole-process matrix uses rnx `c32a6ba7`, which pins public [Rune N6](https://github.com/nilket-com/rune/commit/a68e739e6213dd02877258503f16df7ddaae6fc7).
`rnx run` enables its native tier by default. The same binary supports
`--native=off` and `--engine=legacy`. The pinned production binary passed native
entry/return witnesses for permute and two additional method fixtures, including
a field loop with the default native setting and budget.

## Constant integer arithmetic in masked chains — ADR 0214

Published rnx **`99790566`** vectorizes constant integer addition and subtraction
in generic masked chains, including constants on either side. Invalid input
lanes are replaced with zero for addition and the constant for subtraction, so
null payloads cannot trigger arithmetic overflow. Valid overflow still triggers
a bounded scalar rescan and the existing first-fault replay. Final null output
values remain zero; standalone specialized `x+c` is unchanged.

Whole-map **instructions per row at 100 million rows**, including Arrow adaptation,
per-map plan preparation, output allocation and worker join. Input construction,
initial kernel compilation and result validation are outside this interval.

| Expression | Input | 0213 first | 0214 first | 0213 warm | 0214 warm |
|---|---|---:|---:|---:|---:|
| `(x+y)+1` | benign | 33.282 | 22.375 | 33.282 | 22.375 |
| `(x+y)+1` | adversarial | 33.282 | 22.375 | 33.282 | 22.375 |
| `1+(x+y)` | benign | 33.266 | 22.438 | 33.266 | 22.438 |
| `1+(x+y)` | adversarial | 33.266 | 22.438 | 33.266 | 22.438 |
| `(x+y)-1` | benign | 33.266 | 22.344 | 33.266 | 22.344 |
| `(x+y)-1` | adversarial | 33.266 | 22.344 | 33.266 | 22.344 |
| `1-(x+y)` | benign | 33.250 | 22.407 | 33.250 | 22.407 |
| `1-(x+y)` | adversarial | 33.250 | 22.407 | 33.250 | 22.407 |

Across 10M and 100M rows, first/warm calls and both input patterns, these four
expressions use **32.5–32.8% fewer instructions** (22.34–22.44 Ir/row). All meet
both approved targets: at most 32 Ir/row and at most 80% of the same-expression
baseline. These are instruction counts, not elapsed-time or cross-runtime claims.

The benign fixture alternates valid `x=1` with nulls and uses `y=2`. The adversarial
twin places MAX (addition) or MIN (subtraction) in `y` where `x` is null: the
preceding pair add stays representable, but constant arithmetic would overflow
without neutralization. Both compare the complete output and valid-row counts.
Profiles at 4,096 and 65,536 rows prove zero scalar rescans for benign and null-only
overflow inputs. Separate valid-overflow fixtures prove exactly one rescan per
call and arithmetic replay, in all four shapes and first/warm calls.

The protected six-kernel 10M/100M matrix has no program-plus-unknown instruction
growth; existing numeric ceilings and system-library bounds remain enforced.
No new preparation exceptions apply. The archived raw strict-improvement failure
is retained alongside the approved non-regression verdict.

Baseline: `49eb4453cf333e926357ecd71448175449d5a07c`.
Measured candidate: `019d729e2944b0baf4fd573274ab49bad6d7bf63`.
Published candidate: `99790566bbf72e1b1431df95fd0a6e4e89ad7e0b` differs only in
two scoring/control files; measured production source is unchanged.
[Full first/warm matrices, rescan witnesses and provenance hashes](results/column-0214-summary.json).

Output zero-initialization remains; generic F64/Bool expansion is outside this
record. **Old-path benchmarks not re-measured for 0214 (column-only source scope).**
The reports below describe their original revisions.

## Mixed-mask integer SIMD — ADR 0213

Published rnx **`49eb4453`** runs supported generic integer nodes with checked
AVX2 across a block. An overflow flag triggers one validity-aware scalar rescan
of that node; overflow in a null lane does not become a script error. Final null
output values remain zero.

Whole-map **instructions per row at 100 million rows**, including Arrow adaptation,
per-map plan preparation, output allocation and worker join. Input construction,
initial kernel compilation and result validation are outside this interval.

| Checked `x*3+y` layout | 0212 first | 0213 first | 0212 warm | 0213 warm |
|---|---:|---:|---:|---:|
| flat | 7.950 | 7.948 | 7.950 | 7.948 |
| sliced-chunked-null | 10.274 | 10.258 | 10.274 | 10.258 |
| alternating | 47.507 | 22.585 | 47.507 | 22.585 |
| deterministic-random | 47.507 | 22.585 | 47.507 | 22.585 |

Mixed-mask `x*3+y` uses about **52% fewer instructions**; flat and sliced inputs
are slightly cheaper. These counts do not establish elapsed-time savings or a
new cross-runtime comparison.

The adversarial control uses alternating nulls in `x` and `y=MAX` on those rows,
forcing overflow only in the final add's invalid lanes. Valid rows produce 7.
The benign twin uses `y=2` throughout. Both check complete output and valid-row
counts, with first and warm calls measured separately:

| `(x*3+y)+y`, 65,536 rows | 0212 first | 0213 first | 0212 warm | 0213 warm |
|---|---:|---:|---:|---:|
| benign | 76.388 | 36.544 | 76.347 | 36.512 |
| adversarial | 76.382 | 53.259 | 76.345 | 53.218 |

Profiles prove exactly one scalar rescan per mixed block: 64 at 4,096 rows and
1,024 at 65,536 rows, in each adversarial call; zero in the benign calls.
The adversarial case remains cheaper than the same-expression 0212 baseline.

Acceptance includes reviewed, commit-pair-pinned preparation constants:
`i64add +10`, `axpy +56`, `f64const +10`, `f64add +11` instructions per map;
`multiply3` has the same +56 preparation component but cheaper execution.
Four attributed preparation-function deltas must match exactly across all sizes
and calls. There is no per-row allowance. Unchanged kernels retain program
non-regression after that constant and the approved system-library band; existing
ceilings and the 25 Ir/row mixed-mask target remain enforced. The original raw
failure and reviewed rescore are both identified in the archive.

Baseline: `0f95d955081fd21d43b04bba6b5fac6f1b6bc084`.
Measured candidate: `1263b1e449d7470e947701874f075841b9843739`.
Published candidate: `49eb4453cf333e926357ecd71448175449d5a07c` differs only in
backlog documentation and four scoring/control files; product source is unchanged.
[Full first/warm matrix, adversarial results and provenance hashes](results/column-0213-summary.json).

Constant Add/Sub still uses scalar execution in generic masked chains. Output
zero-initialization remains; generic F64/Bool expansion is outside this record.
**Old-path benchmarks not re-measured for 0213 (column-only source scope).**
Source isolation does not establish unchanged LTO code generation elsewhere.
Earlier reports below retain their original commits and measurements.

## Borrowed column operands — ADR 0212

Published rnx **`0f95d955`** removes generic numeric input staging and writes
final column results directly to owned output. It also reuses the core's valid-row
count. Output allocation/zero-initialization remains; generic mixed-mask SIMD is
still deferred.

Whole-map instructions per row at **100 million rows**, including Arrow adaptation,
output allocation and worker join, excluding preparation/input construction and
validation. First and warm calls are shown separately:

| Checked `x*3+y` layout | Baseline first | 0212 first | Baseline warm | 0212 warm |
|---|---:|---:|---:|---:|
| flat | 10.732 | 7.950 | 10.732 | 7.950 |
| sliced-chunked-null | 13.976 | 10.274 | 13.976 | 10.274 |
| alternating | 49.027 | 47.507 | 49.027 | 47.507 |
| deterministic-random | 49.026 | 47.507 | 49.026 | 47.507 |

Flat and sliced `x*3+y` use about 26% fewer instructions; mixed-mask cases improve
about 3%. These are instruction counts, not elapsed-time or new cross-runtime
comparisons. The paired 10M/100M capture passed the accepted column gates.

Baseline: `9b161210578a53d010e6c4ea8ab61d6bb01f9c8a`.
Measured candidate: `1d2bc05e79b7a75cb6b11dddc6b0a5a4e0025cdd`.
Published candidate: `0f95d955081fd21d43b04bba6b5fac6f1b6bc084` differs only in the
acceptance launcher's cross-verifier output path; product source is unchanged.
[All six kernels, four layouts, both sizes/calls and provenance hashes](results/column-0212-summary.json).

**Old-path benchmarks not re-measured for 0212 (column-only source scope).**
Source isolation does not establish unchanged LTO code generation elsewhere.
Earlier results below retain their original commits and measurements.

## Column kernels — 2026-11-05

<!-- column-0206:start -->

Published **rnx 0206 `002584a` / Rune `fed878b5`** improves nullable
column kernels, adds typed two-input F64 arithmetic and checked constant
multiplication, and counts output validity in words. The explicit
`polars::column_kernel(...).map(...)` API is unchanged.

The table below reports **instructions per row at 100 million rows**, including
Arrow adaptation, output allocation and worker join. Input construction,
preparation and validation are outside the map interval. First and warm calls
are separate; these are individual calls, not repeated-sample means.

| Kernel / layout | 0205 first | 0206 first | 0205 warm | 0206 warm |
|---|---:|---:|---:|---:|
| checked x+1 / flat | 2.228 | 2.219 | 2.228 | 2.219 |
| checked x*2+y / flat | 3.788 | 3.778 | 3.788 | 3.778 |
| checked x*3+y / flat | 91.062 | 10.732 | 91.062 | 10.732 |
| F64 x+1.0 / flat | 1.284 | 1.278 | 1.284 | 1.278 |
| F64 x+y / flat | 66.559 | 1.618 | 66.559 | 1.618 |
| packed !x / flat | 0.065 | 0.065 | 0.065 | 0.065 |

[Full nullable-layout matrix, timing caveats and evidence hashes](results/column-0206-2026-11-05.md).
The historical 0205 host/Polars comparison below has not been remeasured.

<!-- column-0206:end -->

## Historical column comparison — 2026-11-04

<!-- column-summary:start -->

Published **rnx 0205 `bc0fada` / Rune `1b4b66bd`** adds the explicit
`polars::column_kernel(...).map(...)` path for borrowed numeric/Boolean columns.
The following warm `x + 1` measurements process **100 million non-null i64 rows**
and include output allocation. Input construction and validation are outside
the interval. These are individual calls, not repeated-sample means.

| Path | Warm ms | Instructions/row |
|---|---:|---:|
| Actual Rune CLI map | 268 | 2.228 |
| Rune host AVX2 | 265.869 | 2.226 |
| Rune per-row | 6601.214 | 1134.250 |
| Polars py-2.1.0 | 186.579 | 0.688 |

On these warm measurements, Rune host AVX2 is 24.83× faster than per-row Rune; Polars is 1.42× faster than Rune host AVX2. These are ratios of individual measured calls, not statistical rankings.

The matched host/Polars comparison uses varied inputs; the CLI uses constant
inputs and includes Arrow adaptation and the worker join. Host timing excludes
Arrow wrapping/output destruction; Polars eager assignment includes dropping
the prior output. Polars wraps integers, while Rune checks overflow; these inputs
do not overflow. Build recipes differ. No one-instruction-per-row claim is made.

The full report includes 10M/100M first and warm calls, preparation, all twenty
CLI cases, selected paths, null/slice/chunk costs, allocation proofs and thermal
exclusions. Large CLI cases set `--budget 1000000000`; the default remains
2,000,000. User-cycle counts exclude kernel page-fault time. Existing-path
publication includes three explicitly attributed performance exceptions.

[Results, limits and archived evidence](results/column-0205-2026-11-04.md).
The older whole-process N6 matrix below retains its original binary and numbers.

<!-- column-summary:end -->

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
