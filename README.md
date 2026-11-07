# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes, with
rerunnable harnesses, output checks and retained results.

The whole-process matrix uses rnx `c32a6ba7`, which pins public [Rune N6](https://github.com/nilket-com/rune/commit/a68e739e6213dd02877258503f16df7ddaae6fc7).
`rnx run` enables its native tier by default. The same binary supports
`--native=off` and `--engine=legacy`. The pinned production binary passed native
entry/return witnesses for permute and two additional method fixtures, including
a field loop with the default native setting and budget.

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

[Exact totals, measured/published commits and retained receipt hashes](results/column-0223-summary.json).
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

[Exact totals, timing samples, commits and receipt hashes](results/column-0222-summary.json).
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

[Exact totals, measured/published commits and source receipt hash](results/column-0221-summary.json).
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

[Exact totals, measured/published commits and source receipt hash](results/column-0220-summary.json).
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

[Complete matrix, first/warm timings and evidence hashes](results/column-0215-summary.json).

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
