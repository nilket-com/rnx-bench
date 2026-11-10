# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes, with
rerunnable harnesses, output checks and retained results.

The whole-process matrix uses rnx `c32a6ba7`, which pins public [Rune N6](https://github.com/nilket-com/rune/commit/a68e739e6213dd02877258503f16df7ddaae6fc7).
`rnx run` enables its native tier by default. The same binary supports
`--native=off` and `--engine=legacy`. The pinned production binary passed native
entry/return witnesses for permute and two additional method fixtures, including
a field loop with the default native setting and budget.

<!-- column-0233:start -->
## Packed I64 comparisons — ADR 0233

Published rnx **`bc4a2065`** uses runtime-dispatched AVX2 for I64
`==`, `!=`, `<`, `<=`, `>` and `>=`, including column/column and both constant
orientations. Signed extremes, nulls, slices, chunks and tails retain bitwise
parity; unsupported CPUs and forced-portable mode keep the scalar comparison.

All six operations reduced total instruction counts in every tested layout
at 64K and 10M rows, on first and warm calls. Live AVX2 symbols were checked.

| Operation | Total instruction reduction across measured cases |
|---|---:|
| eq | 62.45–78.14% |
| ne | 60.18–75.48% |
| lt | 60.42–78.14% |
| le | 57.74–75.48% |
| gt | 60.55–78.14% |
| ge | 58.27–75.48% |

**Timing caveat:** the original run accidentally kept the same binary order
within each case. The scheduling formula canceled the intended alternation.
These measurements are retained and disclosed, not described as counterbalanced.
At 100M rows, five fresh processes per binary each made one first call and
five warm calls, with a 120-second cooldown per round. Warm values below are
the median [minimum, maximum] of the five process medians, in milliseconds.
Input construction and full-output validation were outside the timed interval.

| I64 equality layout | Baseline warm ms | Candidate warm ms | Change |
|---|---:|---:|---:|
| flat | 84.59 [82.03, 86.46] | 67.50 [63.94, 75.36] | -20.2% |
| alternating | 83.83 [81.33, 86.57] | 64.00 [52.62, 70.20] | -23.7% |
| deterministic-random | 92.08 [81.77, 93.63] | 65.18 [57.95, 67.10] | -29.2% |
| sliced-chunked-null | 72.92 [70.62, 75.24] | 47.08 [43.71, 51.12] | -35.4% |

**Exact exceptions approved by the user:** shared F64 predicate dispatch
adds 4/5 instructions per 1,024-row block for greater-than/less-or-equal,
6/7 for arithmetic comparison, 9/10 for F64 AND, and 11/12 for mixed OR
(flat/nonflat). Function-level setup constants and these slopes are pinned
to the measured binary pair; +1 instruction, extra calls and extra slope fail.
The original scalar/F64 comparison kernels remain unchanged: 246 protected
routines passed resolved assembly identity. The shared driver is outside that set.

A separate portable host probe measured all six operators at 4K/64K rows.
Its total overhead is exactly **6 instructions per map**, with zero net slope:
the driver gains `6 + 2×blocks`, offset by a helper changing from `30×blocks`
to `28×blocks`. Its exact scorer also rejects redistribution hidden behind the
same total. This probe uses its own paired binaries; it is not the CLI binary.

**F64 timing investigation:** the original flat greater-than run reported a
17% warm slowdown. A separate disclosed investigation alternated order across
ten fresh processes per binary (five of each order), with the same cooldown.
It did not reproduce that result. First-call medians remained higher for the
candidate; overlapping ranges do not establish zero effect or statistical
significance. The I64 timing above was not repeated.

| F64 flat case | Call | Baseline ms | Candidate ms |
|---|---|---:|---:|
| f64gt | first | 64.51 [42.49, 70.81] | 67.37 [50.68, 78.24] |
| f64gt | warm | 61.68 [59.19, 70.19] | 60.61 [55.85, 69.18] |
| f64le | first | 61.29 [41.20, 71.39] | 64.93 [48.96, 71.18] |
| f64le | warm | 64.61 [56.91, 69.04] | 62.24 [52.38, 67.40] |

The investigation also records per-call process CPU ticks and faults.
CPU tick resolution is 10 ms; those counter intervals include snapshot overhead,
while the wall timer excludes snapshots. No claim rests on sub-tick CPU changes.

For **cross-day context only**, ADR 0224 measured flat 100M I64 equality at
about 33.08 ms for single-thread Polars and 54.27 ms for direct Arrow, versus
the 67.50 ms observed here for rnx. These are not matched same-day comparisons.
Core, hardware parity, Miri, exact-vector/identity, host, integration, generated
projects, cross and commit checks passed. Unchanged interpreter paths were not
re-measured. Unchanged-path system-library bands at 100M were not measured;
the accepted coverage is SMALL vectors and the changed-path 64K/10M matrix.
Failed exploratory captures and the original timing remain recorded.
[Samples, exact pins, receipt hashes and caveats](ARCHIVED-DATA.md?path=results/column-0233-summary.json#lookup).
[Renderer and validation](scripts/render_column_0233.py).
<!-- column-0233:end -->

<!-- column-0230:start -->
## Reuse for masked F64 outputs — ADR 0230

Published rnx **`e3d4365e`** admits masked single-operation F64
const/add/sub/mul outputs to `kernel.map_reusing(inputs, previous)`.
The existing rules remain: exclusive whole-buffer donors, nonzero output,
needed length ≤ capacity ≤ twice needed length, capacity charged once,
and fresh allocation on refusal. There is no hidden buffer cache or retention.

At 100M rows, warm reuse is **32–38% faster** for all six measured nullable
const/add cells. Plain map and reuse use the **same candidate binary**.
Plain-map instruction vectors match the published baseline `8d104dd1`
exactly in the 4K/64K comparison; no instruction exception was needed.

Milliseconds: median [minimum, maximum] across five fresh processes.
Each process makes one first call and five warm calls; warm statistics use
its median. First reuse calls allocate fresh; their observed ranges overlap
plain map, and no first-call speedup is claimed. Construction and full-output
validation are outside timing. Role order alternates; cooldown is 120 seconds
per round. No retries or statistical-confidence claim. Condition flags remain
in the summary.

| Expression | Layout | Call | Plain map ms | Reuse ms |
|---|---|---|---:|---:|
| f64const | alternating | first | 130.2 [116.7, 136.1] | 123.7 [117.4, 134.1] |
| f64const | alternating | warm | 125.0 [123.3, 137.8] | 78.1 [76.3, 78.4] |
| f64const | deterministic-random | first | 127.7 [121.6, 132.0] | 135.0 [126.4, 140.6] |
| f64const | deterministic-random | warm | 124.6 [124.4, 130.3] | 78.1 [77.6, 78.7] |
| f64const | sliced-chunked-null | first | 111.1 [104.4, 112.0] | 107.0 [104.4, 116.0] |
| f64const | sliced-chunked-null | warm | 113.2 [109.5, 115.2] | 72.4 [72.1, 72.7] |
| f64add | alternating | first | 157.6 [139.1, 164.0] | 160.5 [154.0, 163.7] |
| f64add | alternating | warm | 152.5 [150.6, 161.5] | 99.8 [99.4, 100.2] |
| f64add | deterministic-random | first | 157.7 [141.3, 167.8] | 154.9 [138.7, 169.7] |
| f64add | deterministic-random | warm | 151.2 [146.2, 158.0] | 99.8 [99.3, 100.0] |
| f64add | sliced-chunked-null | first | 123.7 [118.1, 130.7] | 123.9 [117.9, 135.9] |
| f64add | sliced-chunked-null | warm | 123.6 [122.7, 130.5] | 83.8 [82.6, 83.9] |

**Fault-scope correction approved by the user:** the original ≤1% total warm
fault rule passed for alternating/random columns (1,133 plain faults versus
zero with reuse), but failed for sliced-null: reuse retained **465–762 total
faults**, versus 1,087–1,830 plain. That original FAIL remains recorded.
A separate phase capture found a stable donated pointer and capacity, with
**zero faults in warm output execution and transfer**. Its residual faults
occurred before validity intersection, in bitmap/setup allocation; a single
add call also had one outer-setup fault. The bitmap is 12.5 MB at 100M rows.
The phase probe does not identify every allocation within that span.
The revised sliced-null criterion covers output faults, while total faults
remain reported. It does not claim zero faults for the complete call.

| Kind | Warm call | Total faults (phase probe) | Before validity | Outer setup | Output execution | Transfer |
|---|---:|---:|---:|---:|---:|---:|
| f64const | 1 | 697 | 697 | 0 | 0 | 0 |
| f64const | 2 | 465 | 465 | 0 | 0 | 0 |
| f64add | 1 | 698 | 697 | 1 | 0 | 0 |
| f64add | 2 | 465 | 465 | 0 | 0 | 0 |

Bitwise/Path parity, donor fallback, refusal, cancellation, retention, core,
Miri, instance/identity, host, integration, generated-project, cross and
commit checks passed. Unchanged interpreter paths were not re-measured.
[Samples, ranges, total faults, phase attribution and receipt hashes](ARCHIVED-DATA.md?path=results/column-0230-summary.json#lookup).
[Renderer and validation](scripts/render_column_0230.py).
<!-- column-0230:end -->

<!-- column-0229:start -->
## Write-only masked F64 output — ADR 0229

Published rnx **`8d104dd1`** removes the output zero-prefill pass
from masked single-operation F64 const/add/sub/mul. Each block writes its
complete result, including positive-zero null lanes, before publication.
Reuse admission is unchanged; nullable const/add still allocate fresh.

At 100M rows, the measured const/add cases improve **16–25% on first calls**
and **17–29% on warm calls** versus `c7d08d9b`.
Milliseconds below are median [minimum, maximum] across five fresh processes.
Each process makes one first and five warm calls; warm statistics use its
median. Construction and full-output validation are outside timing. Roles
alternate by round, with a fixed 120-second cooldown. There were no retries.
All twelve observed ranges are disjoint; this is not a confidence interval
or a guarantee for other machines. Raw condition flags are retained.

| Expression | Layout | Call | Baseline ms | Candidate ms | Reduction |
|---|---|---|---:|---:|---:|
| f64const | alternating | first | 170.0 [166.3, 179.0] | 128.0 [124.8, 136.4] | 24.7% |
| f64const | alternating | warm | 173.3 [167.1, 174.7] | 126.9 [120.7, 129.6] | 26.8% |
| f64const | deterministic-random | first | 174.6 [168.2, 182.7] | 132.2 [127.6, 135.6] | 24.3% |
| f64const | deterministic-random | warm | 175.8 [165.3, 181.8] | 124.4 [121.0, 132.9] | 29.2% |
| f64const | sliced-chunked-null | first | 144.3 [135.3, 146.0] | 115.0 [105.4, 121.9] | 20.3% |
| f64const | sliced-chunked-null | warm | 141.0 [132.5, 143.9] | 108.2 [106.3, 115.7] | 23.3% |
| f64add | alternating | first | 198.7 [190.0, 203.8] | 166.7 [159.0, 168.3] | 16.1% |
| f64add | alternating | warm | 191.7 [189.5, 201.8] | 153.4 [151.0, 172.2] | 20.0% |
| f64add | deterministic-random | first | 202.0 [198.8, 217.8] | 155.8 [152.3, 175.5] | 22.9% |
| f64add | deterministic-random | warm | 193.2 [190.8, 203.5] | 151.3 [148.3, 163.4] | 21.7% |
| f64add | sliced-chunked-null | first | 151.5 [148.8, 161.0] | 123.8 [113.4, 133.8] | 18.3% |
| f64add | sliced-chunked-null | warm | 151.1 [148.8, 158.8] | 125.2 [122.8, 134.3] | 17.1% |

**Two explicit user-approved exceptions:** the sliced-chunked-null route
is judged by measured wall time instead of total instructions. At 10M rows
its 4,883 small memset calls write 40,000,000 null bytes; Callgrind counts
40 million REP-store iterations. The baseline uses one 80MB memset with
a different libc implementation path. The higher instruction count remains
reported; it was not erased or called a passing original gate. Other changed
layouts retain the total-instruction criterion. Exact binary-pair, program,
accounting and profile seals prevent widening this exception.

The strict no-more-page-faults rule also failed. Cold differences were
−4 to +3; one warm const sliced-null call rose from 1,319 to 1,383 (+64).
Every other warm count matched. These observations were accepted explicitly;
**no fault reduction or exact fault equality is claimed**. Exact fault pins
and +1 negative controls preserve the approved scope.

Core, targeted Miri, instance/identity, host, integration, generated-project,
cross and commit checks passed. Unchanged interpreter paths were not re-measured.
[Samples, ranges, faults, identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0229-summary.json#lookup).
[Renderer and validation](scripts/render_column_0229.py).
<!-- column-0229:end -->

<!-- column-0228:start -->
## Explicit output reuse — ADR 0228

Published rnx **`c7d08d9b`** adds consuming
`kernel.map_reusing(inputs, previous)` for eligible F64 outputs.
At 100M rows, warm calls save **38%** for flat const/add, **8%** for a flat
chain, and **21%** for a chain on nullable columns versus the same binary's
plain map. Nullable const/add still allocate fresh, as planned.

The caller supplies the previous output; there is no hidden buffer cache.
Reuse requires exclusive whole-buffer ownership and capacity between the
needed size and twice that size. Shared, sliced, non-F64 and unsuitable-size
donors fall back to fresh allocation. Rejected buffers are dropped before
fresh allocation; memory is not retained beyond caller-owned outputs.

Milliseconds: median [minimum, maximum] across five fresh processes.
Each process makes one first call and five warm calls; warm statistics use
each process's median. The first reuse call allocates fresh. Input creation,
preparation and full-output validation are outside timing. Role order
alternates by round with a fixed 120-second cooldown. No retries or
statistical-confidence claim. Baseline plain map is rnx `7802ce4a`.

| Expression | Layout | Call | Baseline plain ms | New plain ms | Reuse ms |
|---|---|---|---:|---:|---:|
| f64const | flat | first | 120.3 [117.0, 123.8] | 122.7 [115.0, 124.1] | 120.9 [119.1, 126.1] |
| f64const | flat | warm | 118.7 [117.6, 120.8] | 120.7 [116.7, 124.7] | 75.1 [74.4, 75.4] |
| f64const | alternating | first | 172.7 [170.2, 177.4] | 176.2 [173.0, 181.2] | 179.0 [176.0, 180.5] |
| f64const | alternating | warm | 175.1 [168.5, 180.4] | 168.1 [167.3, 173.0] | 168.7 [167.6, 168.8] |
| f64add | flat | first | 143.4 [132.4, 161.0] | 152.2 [144.7, 164.7] | 162.7 [149.4, 165.3] |
| f64add | flat | warm | 153.5 [153.1, 155.0] | 153.7 [141.4, 157.7] | 95.4 [94.9, 96.1] |
| f64add | alternating | first | 202.3 [199.4, 204.6] | 198.7 [193.7, 203.9] | 193.0 [186.3, 204.8] |
| f64add | alternating | warm | 189.8 [188.7, 196.9] | 192.4 [188.8, 200.4] | 189.7 [186.5, 191.1] |
| f64chain | flat | first | 214.5 [184.5, 220.4] | 219.8 [179.8, 225.7] | 222.0 [184.1, 228.7] |
| f64chain | flat | warm | 215.0 [214.0, 216.1] | 217.9 [187.3, 221.4] | 200.3 [161.2, 207.3] |
| f64chain | alternating | first | 247.7 [204.8, 254.1] | 236.1 [220.1, 251.4] | 254.7 [221.8, 255.9] |
| f64chain | alternating | warm | 239.9 [210.0, 243.8] | 241.1 [230.5, 242.4] | 191.3 [158.8, 192.5] |

Warm page faults fall from **622–1,133 to 0–3** on the four eligible cells.
Nullable const/add remain at 1,133 in the separate diagnostic.

The user approved an exact instruction-count exception for plain map:
flat F64 const adds **1 instruction per 1,024-row block**; flat axpy and
I64 add add **2**. At 10M and 100M the total program deltas are exactly
`ceil(n/1024)+96`, `2*ceil(n/1024)+88`, and `2*ceil(n/1024)+98` respectively.
Fixed setup vectors for other paths are pinned too. Binary-pair checks
reject an extra instruction per call or block and changed call counts.
The affected instruction totals rise about **0.06–0.13%**. Plain-map warm
medians range from **0.96–1.02×** baseline; this does not prove zero timing cost.
Raw failures remain recorded alongside approved rescores.

ADR 0224 warm medians: Arrow flat const 69.0 ms, add
89.9 ms and chain 200.4 ms; single-thread Polars
70.7, 93.5 and 147.9 ms respectively.
Polars leads the flat-chain context result (about 148 ms
versus 200 ms for reuse).
These came from a **different run/day**, not this paired experiment.
The previously quoted 70/92/203/210 ms Arrow figures were from the instrumented
0228 diagnostic, not ADR 0224. This corrects that attribution; context does not
establish parity or a win over either engine.

Core, targeted Miri, ownership/retention, host, integration, generated-project,
cross and commit checks passed. Unchanged interpreter paths were not re-measured.
[Raw sample times, ranges, binary identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0228-summary.json#lookup).
[Renderer and validation](scripts/render_column_0228.py).
<!-- column-0228:end -->

<!-- column-0227:start -->
## Huge-page advice for large outputs — ADR 0227

Published rnx **`7802ce4a`** gives the operating system a
best-effort huge-page hint for large column buffers before first touch.
The matched baseline is **`94c30cee`**. At 100M rows, these
F64 workloads take **34–51% less elapsed time** on the measurement host.

Milliseconds: median [minimum, maximum] across five fresh processes.
Each process makes one first call after preparation and five warm calls.
Warm statistics summarize each process's median of those five calls.
Construction, preparation and full-output validation are outside timing.
Binary order alternates by round, with a fixed 120-second round cooldown.
No retries and no statistical confidence claim.

| Expression | Layout | Call | Baseline ms | Candidate ms | Reduction |
|---|---|---|---:|---:|---:|
| f64const | flat | first | 241.2 [231.6, 242.4] | 118.6 [116.3, 134.8] | 50.8% |
| f64const | flat | warm | 230.9 [228.6, 234.4] | 120.0 [116.0, 125.1] | 48.0% |
| f64const | alternating | first | 356.9 [348.8, 361.8] | 176.2 [172.0, 180.4] | 50.6% |
| f64const | alternating | warm | 345.9 [342.2, 348.0] | 168.1 [166.3, 182.4] | 51.4% |
| f64add | flat | first | 257.9 [254.5, 261.7] | 152.9 [149.3, 165.1] | 40.7% |
| f64add | flat | warm | 251.9 [247.1, 261.9] | 155.1 [146.3, 156.5] | 38.4% |
| f64add | alternating | first | 372.3 [366.0, 387.8] | 195.1 [182.3, 196.7] | 47.6% |
| f64add | alternating | warm | 364.5 [362.7, 378.3] | 193.4 [187.0, 197.9] | 46.9% |
| f64chain | flat | first | 328.0 [321.4, 343.1] | 216.8 [187.0, 222.8] | 33.9% |
| f64chain | flat | warm | 327.9 [309.4, 339.0] | 214.8 [194.8, 218.2] | 34.5% |
| f64chain | alternating | first | 393.6 [375.7, 399.7] | 210.6 [206.7, 253.7] | 46.5% |
| f64chain | alternating | warm | 386.4 [358.6, 387.2] | 239.7 [230.0, 241.8] | 38.0% |

The instruction gate includes an explicit user-approved exception: unchanged
integer `x*3+y` executes one extra jump per all-valid executor call (about
+0.001 Ir/row flat and +0.008 for the sliced fixture). Exact binary-pair pins
check the formula and absolute calls at 10M and 100M, including partial blocks.
Mixed-valid calls save two instructions; flat F64 pair calls save four.
Advice and page-size initialization add exact first/warm constants, selected
separately when data and validity allocations reach 4 MiB. Every pin rejects
an extra instruction or changed call count. Raw failed captures are retained;
reviewed rescores pass without repeating measurements.

The separate page-fault diagnostic improved by a median **172×**, which is
not a 172× speedup. One cold call improved only **7.317×**, with partial
huge-page backing: 675,840 KiB versus 780,288 KiB warm. The hint was present;
the kernel fallback cause is unproven. No call was worse than baseline.
Huge-page availability and elapsed-time gains can vary by host and call.

For context only, flat F64 `x+1.0` warm is now about **120 ms**; ADR 0224
reported Arrow about **69 ms** and Polars about **71 ms** on a different day.
These are **not directly comparable measurements**. This report covers
column buffers; unchanged interpreter paths were not re-measured.

Core, Miri, host, integration, generated-project and cross checks passed.
[Raw sample times, ranges, binary identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0227-summary.json#lookup).
[Renderer and validation](scripts/render_column_0227.py).
<!-- column-0227:end -->

<!-- column-0226:start -->
## Packed Boolean XOR and equality — ADR 0226

Published rnx **`94c30cee`** adds `^`, `==` and `!=` to the
pure-Boolean packed driver, including chains with `&`, `|` and `!`.
Equality uses word-wise XNOR; XOR and inequality use XOR. Strict input-null
intersection, zero invalid payload and tail masking are preserved. Numeric
comparison plans remain in the separate predicate driver.

Whole-map executed instructions per row, including system-library work.
First/warm are two map calls per capture. Construction, initial compilation
and output validation are outside the measured interval. Baseline is
**`b177e963`**, runtime-identical to measured `45823dda`.
No adjustments are subtracted. This is **Ir only, column-only scope**:
no new wall-time or unchanged interpreter performance claim.

| Shape | Layout | Baseline first | Candidate first | Baseline warm | Candidate warm |
|---|---|---:|---:|---:|---:|
| booland | flat | 0.740441 | 0.746300 | 0.740434 | 0.746294 |
| booland | sliced-chunked-null | 1.696524 | 1.702383 | 1.696512 | 1.702370 |
| booland | alternating | 2.513973 | 2.519831 | 2.513958 | 2.519825 |
| booland | deterministic-random | 2.513971 | 2.519833 | 2.513963 | 2.519823 |
| boolor | flat | 0.743365 | 0.746301 | 0.743365 | 0.746294 |
| boolor | sliced-chunked-null | 1.699443 | 1.702380 | 1.699443 | 1.702366 |
| boolor | alternating | 2.516914 | 2.519830 | 2.516901 | 2.519821 |
| boolor | deterministic-random | 2.516902 | 2.519831 | 2.516894 | 2.519823 |
| boolchain | flat | 1.107665 | 1.120363 | 1.107661 | 1.120355 |
| boolchain | sliced-chunked-null | 2.232694 | 2.245390 | 2.232687 | 2.245382 |
| boolchain | alternating | 3.344160 | 3.356850 | 3.344143 | 3.356841 |
| boolchain | deterministic-random | 3.344153 | 3.356852 | 3.344144 | 3.356845 |
| booleq | flat | 94.387899 | 0.755088 | 94.387892 | 0.755084 |
| booleq | sliced-chunked-null | 51.343002 | 1.711173 | 51.342990 | 1.711164 |
| booleq | alternating | 109.802364 | 2.528622 | 109.802363 | 2.528610 |
| booleq | deterministic-random | 109.802363 | 2.528617 | 109.802352 | 2.528613 |
| boolne | flat | 94.387902 | 0.746295 | 94.387895 | 0.746292 |
| boolne | sliced-chunked-null | 51.342992 | 1.702371 | 51.342988 | 1.702370 |
| boolne | alternating | 109.802370 | 2.519834 | 109.802358 | 2.519827 |
| boolne | deterministic-random | 109.802363 | 2.519834 | 109.802349 | 2.519824 |
| boolxor | flat | 93.387904 | 0.746300 | 93.387895 | 0.746294 |
| boolxor | sliced-chunked-null | 50.843003 | 1.702384 | 50.842992 | 1.702375 |
| boolxor | alternating | 108.802373 | 2.519828 | 108.802361 | 2.519831 |
| boolxor | deterministic-random | 108.802362 | 2.519830 | 108.802346 | 2.519824 |

The table shows 100M rows. All new shapes pass at 10M and 100M, first and
warm, across all four layouts: at most 2 Ir/row flat, 4 nullable, and 10% of
baseline instructions. Deterministic-random validity repeats a 256-bit mask.

The edited driver increases existing AND/OR/chain work by **6/3/13 instructions
per 1,024-row block** in the small diagnostic. Those paths retain their raw
ceilings: 2/4 Ir per row for AND/OR and 2.5/5 for chains, flat/nullable.
Unchanged paths retain exact function vectors plus reviewed fixed setup pins.

This record also repairs two stale cross-check fixtures left by ADR 0224,
whose gate set omitted cross: the live `src/time.rs` fingerprint and the
registry count after adding `time::monotonic_ns`. The checked refresh verifies
exact old/new witnesses, allowing only that addition and the source-proven
`monotonic_ms` documentation change. Historical provenance is unchanged.
Failed receipts are retained; cross passed after repair. Other passed stages
were reused with tooling-only diff proofs.

[Exact totals, reviewed table, binary identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0226-summary.json#lookup).
[Renderer and validation](scripts/render_column_0226.py).
<!-- column-0226:end -->

<!-- column-0224:start -->
## Cross-engine column comparison — ADR 0224

rnx **`45823dda`**, Polars **2.1.0**, direct Arrow kernels (PyArrow
**26.0.1**) and DuckDB **2.0.0**, measured at 10M and 100M rows.
This is a wall-time comparison, not a new instruction-count result or an
aggregate ranking. [All 640 cells with ranges](results/column-0224-tables.md)
place equivalent and native semantics side by side;
[compact samples and settings](ARCHIVED-DATA.md?path=results/column-0224-summary.json#lookup) retain all 2,976
process samples. [Renderer/validator](scripts/render_column_0224.py).

The first three expressions produce F64 columns; the others produce Boolean
masks, **not filtered tables**. Primary results enforce rnx's strict input-null
intersection and unordered NaN comparisons. Polars and DuckDB use explicit
semantic adaptations where needed. Their secondary native panel omits those
adaptations and is **not generally semantically equivalent**, even when these
finite flat inputs happen to produce the same answers. Arrow uses direct
strict Boolean kernels; it is not an Arrow-backed dataframe benchmark.

100M **flat**, equivalent semantics, median **first / warm milliseconds**.
Ranges for every entry are in the complete table.

| Key / expression | rnx serial | Arrow serial | Polars 1 | Polars 28 | DuckDB 1 | DuckDB 28 |
|---|---:|---:|---:|---:|---:|---:|
| f64const: `x + 1.0` | 247.88 / 243.66 | 120.53 / 69.03 | 248.54 / 70.69 | 253.59 / 70.67 | 627.41 / 300.88 | 360.25 / 171.24 |
| f64add: `x + y` | 273.85 / 265.14 | 145.75 / 89.90 | 269.10 / 93.54 | 274.96 / 94.39 | 668.87 / 433.58 | 396.52 / 205.91 |
| f64chain: `x * 2.0 + y` | 340.42 / 336.14 | 252.58 / 200.40 | 328.39 / 147.92 | 326.92 / 145.18 | 699.77 / 476.42 | 423.70 / 237.66 |
| booland: `a & b` | 12.92 / 8.43 | 5.13 / 3.99 | 17.12 / 14.67 | 18.33 / 14.41 | 303.26 / 269.24 | 170.73 / 138.31 |
| boolor: `a &#124; b` | 14.94 / 11.58 | 5.28 / 4.06 | 17.04 / 11.40 | 17.79 / 11.77 | 283.38 / 251.07 | 166.36 / 139.47 |
| boolchain: `(a & b) &#124; c` | 17.02 / 14.12 | 9.92 / 10.01 | 22.50 / 15.86 | 29.79 / 16.53 | 311.16 / 281.07 | 194.31 / 162.33 |
| f64gt: `x > 1.0` | 57.82 / 61.55 | 70.08 / 53.82 | 87.45 / 83.04 | 106.07 / 82.93 | 337.62 / 293.34 | 222.52 / 180.28 |
| i64eq: `i == 2` | 89.23 / 86.40 | 55.31 / 54.27 | 48.58 / 33.08 | 50.19 / 33.13 | 253.23 / 219.50 | 134.03 / 103.93 |
| f64and: `(x > 1.0) & (y < 2.0)` | 105.98 / 111.50 | 118.55 / 118.22 | 182.14 / 178.35 | 206.44 / 184.96 | 523.64 / 487.25 | 409.95 / 373.30 |
| mixedor: `((x > 1.0) & (y < 2.0)) &#124; c` | 122.60 / 125.84 | 121.58 / 121.05 | 188.96 / 183.02 | 184.75 / 228.68 | 555.75 / 520.93 | 439.75 / 403.54 |
| arithcmp: `x * 2.0 + y > 3.0` | 133.46 / 128.64 | 303.90 / 305.39 | 563.75 / 560.18 | 563.57 / 558.32 | 435.16 / 397.50 | 316.19 / 282.00 |

On these flat F64 arithmetic examples, rnx warm calls take approximately
1.7–3.5× Arrow/Polars time. Some nullable layouts have larger gaps; this range
does not summarize the entire matrix. Arrow leads these flat Boolean examples,
and Polars/Arrow lead I64 equality. rnx is competitive on F64 predicates and
leads the arithmetic-plus-comparison example under equivalent semantics, but
is not universally fastest: Arrow's flat `f64gt` warm result is 53.82 ms versus
rnx's 61.55 ms, and its alternating `f64and` is 126.47 versus 131.81 ms.

The native panel changes the picture substantially. At 100M flat rows,
Polars single-thread native Boolean AND is **0.194 ms**, versus **14.67 ms**
with strict semantics; native `f64gt` is **34.15 ms**, versus **83.04 ms**.
DuckDB default native `arithcmp` is **93.63 ms**, versus **282.00 ms**.
Fixtures use uniform finite values and can enable engine-specific shortcuts:
these native numbers must not be described as general kernel throughput.

**Unexplained observation:** rnx first and warm times are close for large F64
outputs, while Arrow and Polars become sharply faster warm. The cause was not
measured. These results do not establish an allocation, page-fault or ownership
explanation.

Measurement details and limits:

- Each primary cell has five fresh processes, each with one first call and five
  warm calls. The reported warm value is the median of the five within-process
  medians; its range is across processes, not 25 independent samples. The native
  panel has three processes per cell and only 100M rows. No confidence intervals
  or statistical-significance claims are made.
- First means first **after preparation**, not cold startup. Input construction,
  expression preparation and full-output validation are outside the clock.
  Output materialization is inside. DuckDB preloads a physical table, normalizes
  input offsets/chunks, and times SQL execution plus Arrow export. Polars' Arrow
  conversion for validation is outside the clock. These API boundaries differ.
- Polars and DuckDB use 1 or 28 threads. rnx is single-threaded and Arrow uses
  serial direct kernels; each is measured once and reused for both thread
  comparisons, without pretending these are independent measurements.
- Layouts are flat, sliced/chunked/null, alternating validity and deterministic
  random validity. The random validity mask repeats every 256 bits; values are
  uniform, not representative random data. Semantic probes separately test
  heterogeneous values, nulls, NaNs and signed zero. NaN payload identity is not
  promised. Every timed output is validated after the clock stops.
- Runs were serial, with a fixed 120-second cooldown before each round. No
  slow/hot samples were replaced. The sample span was 4.83 hours, excluding the
  initial cooldown. **1,743 samples flagged load average >1**; this lagging metric
  does not establish concurrent competing work or an idle host. The x86 package
  sensor observed **48–68°C**. Invalid ACPI readings (−268.4 to −266°C) are retained
  in raw local evidence but excluded as physical temperature measurements.
- Nanosecond units are not nanosecond accuracy. Python reports 1 ns clock
  resolution; Rust `Instant` resolution is unknown. Process peak RSS includes
  construction and validation and is not a kernel-only memory measurement.
- Existing interpreter paths were not re-measured for this report. The runtime
  change is the nanosecond clock; column implementation is unchanged from
  `6d253fad`. No next optimization is implied by these observations.

Published [implementation and harness](https://github.com/nilket-com/rnx/tree/45823ddaf2a5890afcafd9e06e45bd71a56a9a5c/tools/column/compare).
The compact summary retains each process’s first-call and warm-median nanoseconds,
cell statistics, settings and condition-flag counts; individual warm calls and
per-call metadata remain in local raw evidence. The full original summary SHA-256 is
`dedb0654888f9ef9472d350e2ea31b02f47452081662e2c86f272eba482f93a9`;
the terminal matrix receipt SHA-256 is
`83b3bb1f179040a3ad9cf4d99d1995cd47a9604ea16611398adc913841f2ed4d`.
Production binary SHA-256:
`e787bf81f86f88120a2444c539686a103774bfc9e9d269d662abfad067c9f8bf`.
The matrix passed all 2,976 samples; the preceding full oracle validation
passed 752 cases. Failed development receipts were retained; no failed final
timing sample was retried. Re-render with `python3 scripts/render_column_0224.py`.
<!-- column-0224:end -->

<!-- column-0223:start -->
## Numeric predicate masks — ADR 0223

Published rnx **`6d253fad`** adds a separate driver for Bool-output
plans containing I64/F64 comparisons, optionally F64 Add/Sub/Mul and Boolean
combinations. I64 arithmetic is excluded. The result is a Boolean mask column,
**not a row-filter operator**. Validity is the intersection of all input validity;
invalid output payload bits are zero.

| Fixture | Expression |
|---|---|
| f64gt | `x > 1.0` |
| f64le | `x <= 1.0` |
| i64eq | `x == 2` |
| f64and | `(x > 1.0) & (y < 2.0)` |
| mixedor | `((x > 1.0) & (y < 2.0)) &#124; z` |
| arithcmp | `x * 2.0 + y > 3.0` |

Whole-map executed instructions per row, including setup and system-library work.
Construction, initial compilation and output validation are outside the interval.
First/warm are two map calls in each capture. Baseline is published **`e4e6f465`**.
No adjustments are subtracted. The table shows 100M rows; exact totals for both
10M and 100M are in the linked summary. Deterministic-random validity repeats a
256-bit mask; it is not an independent random draw per row.

| Predicate | Layout | Baseline first | 0223 first | Baseline warm | 0223 warm |
|---|---|---:|---:|---:|---:|
| f64gt | alternating | 79.002191 | 4.680913 | 79.002181 | 4.680901 |
| f64gt | deterministic-random | 79.002177 | 4.680901 | 79.002173 | 4.680899 |
| f64gt | flat | 64.330264 | 3.775577 | 64.330263 | 3.775578 |
| f64gt | sliced-chunked-null | 36.123253 | 4.495333 | 36.123247 | 4.495325 |
| f64le | alternating | 80.002177 | 4.135006 | 80.002176 | 4.134994 |
| f64le | deterministic-random | 80.002182 | 4.135005 | 80.002172 | 4.135000 |
| f64le | flat | 65.330268 | 3.229677 | 65.330261 | 3.229673 |
| f64le | sliced-chunked-null | 36.623253 | 3.949429 | 36.623253 | 3.949433 |
| i64eq | alternating | 74.111554 | 7.974847 | 74.111542 | 7.974840 |
| i64eq | deterministic-random | 74.111559 | 7.974848 | 74.111549 | 7.974841 |
| i64eq | flat | 59.336123 | 7.069523 | 59.336123 | 7.069516 |
| i64eq | sliced-chunked-null | 33.670130 | 7.789275 | 33.670122 | 7.789271 |
| f64and | alternating | 202.482240 | 8.557142 | 202.482234 | 8.557137 |
| f64and | deterministic-random | 202.482240 | 8.557143 | 202.482231 | 8.557136 |
| f64and | flat | 168.819727 | 7.047261 | 168.819729 | 7.047265 |
| f64and | sliced-chunked-null | 91.819731 | 7.804123 | 91.819724 | 7.804110 |
| mixedor | alternating | 279.478524 | 9.417691 | 279.478511 | 9.417678 |
| mixedor | deterministic-random | 279.478477 | 9.417691 | 279.478461 | 9.417677 |
| mixedor | flat | 236.092305 | 7.444842 | 236.092300 | 7.444839 |
| mixedor | sliced-chunked-null | 127.279809 | 8.370647 | 127.279803 | 8.370644 |
| arithcmp | alternating | 201.482251 | 10.755377 | 201.482234 | 10.755373 |
| arithcmp | deterministic-random | 201.482237 | 10.755375 | 201.482226 | 10.755377 |
| arithcmp | flat | 167.819726 | 9.245510 | 167.819724 | 9.245503 |
| arithcmp | sliced-chunked-null | 91.319732 | 10.002364 | 91.319731 | 10.002364 |

All six predicates meet their absolute instruction ceilings and use at most
25% of baseline instructions across both sizes, all layouts and both calls.
Comparison forms were selected by measurement: F64 uses packed comparisons
over 64-lane words; I64 retains bounded eight-lane scalar comparisons because
the tested packed SSE2 form cost more. F64 arithmetic uses packed four-lane loops.

The original small and large FAIL receipts are retained with hashes. The small
rescore applies reviewed, binary-pair-pinned per-function setup constants and
exact call counts, with no per-row allowance. Untouched `dismantle_repr` source
showed a fixed instruction decrease attributed to code-generation redistribution.
The large rescore classifies the unchanged `f64chain` path under the ELF-object
rule: program instructions decreased by seven, unknown-object totals matched,
and system-library variation stayed within the existing band (0.001 Ir/row plus
4,096 fixed instructions). Its absolute whole-map ceiling remains enforced.
Neither rescore reran measurements or changed raw totals.

Core tests, targeted Miri, executed assembly snapshots, protected column checks,
host integration, generated projects and cross verification passed.
NaN behavior and bit equality were checked on x86-64; this is not a portable
NaN-payload guarantee. These are instruction counts only: no new timing result
or proportional elapsed-time claim is made.

**Column-only scope: old interpreter paths were not re-measured. These gains do
not describe arbitrary scripts or the cost of materializing filtered rows.**

[Exact totals, measured/published commits and retained receipt hashes](ARCHIVED-DATA.md?path=results/column-0223-summary.json#lookup).
<!-- column-0223:end -->

<!-- column-0222:start -->
## F64 write-only output — ADR 0222

Published rnx **`e4e6f465`** runs qualifying pure-F64 plans
with at least two Add/Sub/Mul operations using write-only output storage.
The measured expression is `x*2.0+y`; single-operation plans keep existing paths.

Whole-map executed instructions per row, including setup and system-library work.
Input construction, initial compilation and output validation are outside the
measured interval. First and warm are two map calls in each capture.
Baseline is published **`7c51bf60`**. No adjustments are subtracted.

| Operation | Layout | Rows | Baseline first | 0222 first | Baseline warm | 0222 warm |
|---|---|---:|---:|---:|---:|---:|
| f64chain | flat | 10000000 | 11.190267 | 9.793781 | 11.190266 | 9.793780 |
| f64chain | flat | 100000000 | 11.186902 | 9.790417 | 11.186901 | 9.790417 |
| f64chain | sliced-chunked-null | 10000000 | 11.576147 | 11.023412 | 11.576102 | 11.023367 |
| f64chain | sliced-chunked-null | 100000000 | 11.572670 | 11.019936 | 11.572666 | 11.019931 |
| f64chain | alternating | 10000000 | 19.499117 | 17.641700 | 19.499029 | 17.641612 |
| f64chain | deterministic-random | 10000000 | 18.874080 | 17.661197 | 18.874058 | 17.661106 |
| f64chain | alternating | 100000000 | 19.494936 | 17.637514 | 19.494922 | 17.637501 |
| f64chain | deterministic-random | 100000000 | 18.869934 | 17.657045 | 18.869924 | 17.657031 |

Descriptive quiet 100M-row map wall time in milliseconds. One sample per
role/layout, containing first and warm calls; no statistical claim or timing
acceptance threshold. The lease and readiness policy used a fixed 120-second
cooldown before each sample. Construction and validation are outside map time.

| Layout | Version | First ms | Warm ms |
|---|---|---:|---:|
| flat | 0221 | 335 | 333 |
| flat | 0222 | 251 | 256 |
| sliced-chunked-null | 0221 | 366 | 330 |
| sliced-chunked-null | 0222 | 307 | 270 |
| alternating | 0221 | 352 | 351 |
| alternating | 0222 | 290 | 290 |
| deterministic-random | 0221 | 349 | 349 |
| deterministic-random | 0222 | 299 | 300 |

Timing recovery: v1 lacked clocks in mixed-null fixtures; v2 used an invalid
small fixture size; v3 put preflight artifacts in the recorder directory.
All three FAIL receipts were retained. Four completed, validated flat/sliced
samples were reused with receipt and binary identity checks; only missing
mixed-layout samples were measured after correcting the harness.

The removed fill measured 8 Ir/row at small sizes (Callgrind counts repeated
byte stores) and 0.4375 Ir/row at large sizes (glibc non-temporal stores).
Both paths write 8 bytes per row: removing the fill avoids a redundant 800 MB
pass at 100M rows. Ir savings do not express memory traffic or predict timing.

Protected column vectors passed with reviewed fixed setup pins, exact unknown
object totals and unchanged system-library bands. Every candidate F64 profile
lacked the output-fill edge; baseline profiles supplied the positive control.
NaN bit equality was verified on x86-64 only. Boolean output is unchanged.

**Column-only scope: old interpreter paths were not re-measured. Gains apply
only to qualifying pure-F64 plans, not arbitrary scripts.**

[Exact totals, timing samples, commits and receipt hashes](ARCHIVED-DATA.md?path=results/column-0222-summary.json#lookup).
<!-- column-0222:end -->

<!-- column-0221:start -->
## Pure-F64 multi-operation plans — ADR 0221

Published rnx **`7c51bf60`** runs qualifying pure-F64 plans
with at least two Add/Sub/Mul operations in a separate whole-plan driver.
The measured expression is `x*2.0+y`; single-operation plans keep existing paths.

Whole-map executed instructions per row, including setup and system-library work.
Input construction, initial compilation and output validation are outside the
measured interval. First and warm are two map calls in each capture.
Baseline is published **`662a8214`**. No adjustments are subtracted.

| Operation | Layout | Rows | Baseline first | 0221 first | Baseline warm | 0221 warm |
|---|---|---:|---:|---:|---:|---:|
| f64chain | flat | 10000000 | 104.034203 | 11.190270 | 104.034169 | 11.190268 |
| f64chain | sliced-chunked-null | 10000000 | 58.003076 | 11.576147 | 58.002999 | 11.576102 |
| f64chain | alternating | 10000000 | 126.556895 | 19.499139 | 126.556764 | 19.499077 |
| f64chain | deterministic-random | 10000000 | 126.556917 | 18.874135 | 126.556811 | 18.874060 |
| f64chain | sliced-chunked-null | 100000000 | 58.000314 | 11.572670 | 58.000306 | 11.572666 |
| f64chain | flat | 100000000 | 104.031548 | 11.186901 | 104.031544 | 11.186901 |
| f64chain | alternating | 100000000 | 126.553442 | 19.494934 | 126.553430 | 19.494926 |
| f64chain | deterministic-random | 100000000 | 126.553436 | 18.869936 | 126.553422 | 18.869922 |

Protected column paths passed exact function-vector checks with reviewed setup
constants and pinned run_flat-to-map inlining redistribution (net nonpositive
per block). Unknown-object totals stayed exact; system-library bands passed.
NaN bit equality was verified on x86-64 only, not asserted across platforms.

Output zero-initialization remains. Its measured 8 versus 0.44 Ir/row size
dependence is backlogged for attribution and a separate ownership change.

**Column-only scope: old interpreter paths were not re-measured. These are
instruction counts only, with no elapsed-time or cycle measurements. The gains
apply to qualifying pure-F64 plans, not arbitrary scripts.**

[Exact totals, measured/published commits and source receipt hash](ARCHIVED-DATA.md?path=results/column-0221-summary.json#lookup).
<!-- column-0221:end -->

<!-- column-0220:start -->
## Packed Boolean plans — ADR 0220

Published rnx **`662a8214`** evaluates pure-Boolean AND/OR plans
and their NOT intermediates as packed words in a separate whole-plan driver.
Null semantics remain strict: all inputs must be valid for an output row to be valid.
NOT-only plans, comparisons, XOR and numeric plans keep their existing paths.

Whole-map executed instructions per row, including setup and system-library work.
Input construction, initial kernel compilation and output validation are outside
the measured interval. First and warm are the two map calls in each capture.
Baseline is published **`e05ce43c`**. No adjustments are subtracted.

| Operation | Layout | Rows | Baseline first | 0220 first | Baseline warm | 0220 warm |
|---|---|---:|---:|---:|---:|---:|
| booland | flat | 10000000 | 93.390744 | 0.742272 | 93.390646 | 0.742219 |
| booland | flat | 100000000 | 93.388881 | 0.740435 | 93.388871 | 0.740433 |
| booland | sliced-chunked-null | 10000000 | 50.844916 | 1.698383 | 50.844817 | 1.698396 |
| booland | sliced-chunked-null | 100000000 | 50.842996 | 1.696518 | 50.842985 | 1.696510 |
| booland | alternating | 10000000 | 108.804893 | 2.516614 | 108.804807 | 2.516516 |
| booland | alternating | 100000000 | 108.802365 | 2.513971 | 108.802353 | 2.513955 |
| booland | deterministic-random | 10000000 | 108.804916 | 2.516692 | 108.804710 | 2.516570 |
| booland | deterministic-random | 100000000 | 108.802361 | 2.513971 | 108.802347 | 2.513961 |
| boolor | flat | 10000000 | 93.390734 | 0.745202 | 93.390643 | 0.745149 |
| boolor | flat | 100000000 | 93.388878 | 0.743369 | 93.388870 | 0.743365 |
| boolor | sliced-chunked-null | 10000000 | 50.844924 | 1.701396 | 50.844874 | 1.701304 |
| boolor | sliced-chunked-null | 100000000 | 50.842989 | 1.699449 | 50.842985 | 1.699436 |
| boolor | alternating | 10000000 | 108.804890 | 2.519585 | 108.804737 | 2.519467 |
| boolor | alternating | 100000000 | 108.802370 | 2.516906 | 108.802356 | 2.516895 |
| boolor | deterministic-random | 10000000 | 108.804868 | 2.519603 | 108.804791 | 2.519516 |
| boolor | deterministic-random | 100000000 | 108.802362 | 2.516906 | 108.802358 | 2.516901 |
| boolchain | flat | 10000000 | 160.665364 | 1.109819 | 160.665255 | 1.109780 |
| boolchain | flat | 100000000 | 160.662437 | 1.107665 | 160.662427 | 1.107661 |
| boolchain | sliced-chunked-null | 10000000 | 86.306088 | 2.234993 | 86.306010 | 2.234832 |
| boolchain | sliced-chunked-null | 100000000 | 86.303079 | 2.232693 | 86.303061 | 2.232692 |
| boolchain | alternating | 10000000 | 185.802863 | 3.347865 | 185.802766 | 3.347784 |
| boolchain | alternating | 100000000 | 185.798635 | 3.344153 | 185.798626 | 3.344150 |
| boolchain | deterministic-random | 10000000 | 185.802418 | 3.347706 | 185.802324 | 3.347638 |
| boolchain | deterministic-random | 100000000 | 185.798609 | 3.344157 | 185.798598 | 3.344148 |

Protected column paths passed exact function-vector checks with reviewed fixed
setup differences and the pinned beneficial invoke formula; unknown-object totals
matched and unchanged-path system-library bands passed. This is not a claim of
byte-identical binaries or identical setup cost.

**Column-only scope: old interpreter paths were not re-measured. These are instruction
counts only; no wall-clock or cycle measurements were taken for this record. Gains
apply to qualifying pure-Boolean plans, not arbitrary scripts.**

[Exact totals, measured/published commits and source receipt hash](ARCHIVED-DATA.md?path=results/column-0220-summary.json#lookup).
<!-- column-0220:end -->

<!-- column-0215:start -->
## Flat numeric output initialization — ADR 0215

Published rnx **`956ed4d5`** removes the initial zero fill for specialized flat
numeric outputs. Each primitive writes its whole block before the output becomes
visible. Generic, masked and Boolean outputs keep initialized storage. The record
also makes bounded null clearing explicit and separates masked-float entry signatures.

Whole-map instructions per row at **100 million rows**, including adaptation,
per-map preparation, allocation and worker join; input construction, initial
kernel compilation and output validation are outside the measured interval.

| Kernel | 0214 first / warm | 0216 first / warm | 0215 first / warm | Warm reduction vs 0216 |
|---|---:|---:|---:|---:|
| I64 x+1 | 2.208 / 2.208 | 2.204 / 2.204 | 1.726 / 1.726 | 21.7% |
| I64 x*2+y | 3.768 / 3.768 | 3.764 / 3.764 | 3.237 / 3.237 | 14.0% |
| F64 x+1.0 | 1.267 / 1.267 | 1.267 / 1.267 | 0.782 / 0.782 | 38.2% |
| F64 x+y | 1.607 / 1.607 | 1.607 / 1.607 | 1.085 / 1.085 | 32.5% |

Quiet single-process-sample wall times for the same 100M-row map, in milliseconds
(first / warm). These are descriptive observations, not statistical estimates.

| Kernel | 0214 | 0216 | 0215 |
|---|---:|---:|---:|
| I64 x+1 | 280 / 276 | 279 / 275 | 199 / 195 |
| I64 x*2+y | 286 / 305 | 327 / 291 | 210 / 207 |
| F64 x+1.0 | 280 / 276 | 279 / 274 | 199 / 194 |
| F64 x+y | 287 / 284 | 287 / 285 | 202 / 198 |

The complete 10M/100M matrix passed reviewed program checks against both baselines,
whole-map ceilings and applicable system-library checks. Unchanged paths retain
reviewed, exactly attributed setup costs of 17–82 instructions per call; no per-row
or per-block allowance was needed. Correctness, targeted Miri and host checks passed.

[Complete matrix, first/warm timings and evidence hashes](ARCHIVED-DATA.md?path=results/column-0215-summary.json#lookup).

Limitations from the approved publication packet:

- Timing single serial sample per binary/kernel with first/warm map milliseconds; descriptive, not statistical or a general workload claim.
- Old VM benchmarks not remeasured: production scope column primitives and output allocation/execution.
- Fixed reviewed setup costs17..82 Ir/call pinned to measured candidate and exact function vectors; no per-block allowance.
- Baseline shape mismatch retained under explicit review; two-composition and exact loop gates pass.
- Safety uses portable Miri plus native/portable controls; Miri does not execute AVX2.
- 0216 prerequisite only measured4096/65536;0215 measured10M/100M against both published0216 and original0214.

Measured candidate: `89182b3b3235cdbf66b3312f844792608d6f1e12`. The published commit adds only the reviewed
scorer, policy and tests. This is not a new cross-runtime comparison.

<!-- column-0215:end -->

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
[Full first/warm matrices, rescan witnesses and provenance hashes](ARCHIVED-DATA.md?path=results/column-0214-summary.json#lookup).

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
[Full first/warm matrix, adversarial results and provenance hashes](ARCHIVED-DATA.md?path=results/column-0213-summary.json#lookup).

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
[All six kernels, four layouts, both sizes/calls and provenance hashes](ARCHIVED-DATA.md?path=results/column-0212-summary.json#lookup).

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

Historical data is stored outside git. See [Archived benchmark evidence](ARCHIVED-DATA.md)
for original-path lookup and checksum-verified report rendering.
