# 0180 native-event study: official attempt, STOP with valid partial evidence

One official run was made under plan rnx ee3a5de section 7 (wording correction fac2b00). It **stopped on a registered
measurement-validity gate** in group B after groups R and A had completed. This is not a completed study. Groups R and
A are valid partial evidence; group B is invalid and incomplete; groups C, D and E were never collected. Nothing was
repaired, replayed or added after the result. 0179's STOP is unchanged; no engine, profile or product change follows.

## Identities

- Subjects: the two retained 0179 PRIMARY binaries only, staged at 0179's stage path with 0179's E0 environment and
  argv: base `af06e8b3...0c87`, candidate `e4a5f207...a787`; hash checked before and after every sample.
- Driver `probes/execution-cost-0180/events.py`, controls `controls_events.py`. Source at the official run: b92ee986
  (tree e89da845). History: 063c44b3 (first driver), 902b5635 (review repairs R1-R4), b92ee986 (rehearsal probe gate).
- Discovery `discovery1` (driver 063c44b3): availability.json sha256 `29b03834d480690511f760cfe2e4f01372e953c59271c3b1d94c55ed4504de0b`,
  identity.json sha256 `c281c11d5b0a0d3552415836e66635a9aed03c6fa3162c06f7f921848882f2aa`. Host gate: GenuineIntel family 6
  model 0xB7 stepping 1, CPU 4 in the cpu_core mask 0-15, kernel 7.0.0-31-generic, perf 7.0.14. All six frozen groups
  passed both open checks on the affinity probe; no event magnitude selected anything. `cpu_core/ref-cycles` resolves to
  event 0x3c umask 0x01, accepted in review as CPU_CLK_UNHALTED.REF_TSC_P.
- Accepted rehearsal: `rehearsal2` (driver b92ee986). `official1` raw rows sha256 `edfa125ad3ae2aeedc464f313f071d2d8c28d76a9884395402857c99723e83e0`.

## Disclosures

- `rehearsal1` ran before the discovery/availability receipts had been reviewed, against the agreed order. It executed
  no experiment subject or workload (one probe on the grep affinity command and one deliberately failing command). It
  is retained unchanged with a note beside it and was not accepted as the rehearsal.
- Review of the first driver found four defects, all repaired before any workload ran. Identity/parser defects were
  reproduced by the reviewer without perf; deadline and scan-status defects were identified by source inspection: admission ignored the identity receipt and allowed an eligible group to be dropped (R1); the parser
  accepted missing, non-finite or negative running times and arbitrary units (R2); outer deadlines were checked only
  before a sample (R3); a sentinel hit after a "complete" status left the report complete (R4). A further gap, the
  rehearsal probe's status and output being unchecked, was closed in b92ee986. The 12 retained discovery rows pass the
  repaired parser; discovery was not repeated.
- Control runs retained: event-controls1 (19/19, first driver), event-controls2 (26/26), event-controls3 (26/26, final).
  One intermediate run of the extended controls, 25/26, was made in a scratch directory and NOT retained: its `.xz`
  control asserted a count of exactly 1 where the scanner, which searches stored and decompressed bytes, counted 2. The
  assertion became "this file, count >= 1"; the scanner did not change. No receipt exists for that run.
- Before any measurement, two control expectations were corrected for binary floating-point rounding at inclusive
  tolerance boundaries (EPS 1e-12 in `anchor_check`).
- perf 7.0.14's JSON rows carry no PMU field and no enabled-time field. "cpu_core only" rests on the frozen
  `cpu_core/.../u` spellings bound in the availability manifest; non-multiplexing rests on one strong pinned group,
  `--no-scale`, and `pcnt-running` equal to 100 with a finite positive running time on every row.

## The official attempt

Command, from the repository root at a clean tree, controller environment PATH/HOME/LANG only:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/execution-cost-0180/events.py official results/execution-cost-0180/official1 results/execution-cost-0180/discovery1/availability.json

Exit status 1; report status `STOPPED (infrastructure, safety or measurement failure)`; 59 s. Admission passed at launch (reviewed
receipt bytes, content validation, current host equal to the recorded identity, `perf --version` status 0). 405 raw rows
were retained: R 140, A 140, B 125, C/D/E 0. Sentinel scan completed with 0 occurrences in 2 files.

**Stop:** the 125th sample of group B (repetition 4, run-fib, base). Its four top-level slot counts divided by `slots`
were retiring 0.5963, bad speculation 0.1216, frontend bound 0.2044, backend bound 0.0981: a sum of 1.020378, outside
the registered `|sum - 1| <= 0.02`. The protocol makes that a measurement STOP, never clamped or repaired. The other 124
group-B samples had sums from 0.9961 to 1.0078. The tolerance was frozen before this distribution had been observed on
this host; why this sample's categories exceeded it has not been analysed and is not explained here. Group B therefore
has no summary and its 124 earlier samples are not a group result. C, D and E were never started: their mechanisms are
untested, not refuted.

## Valid partial evidence: groups R and A

Both groups' reproduction anchors passed (each side's instruction median within 2% of 0179, instruction change within
0.5 percentage points, each side's cycle median within 10%, cycle change within 3 percentage points; run-empty cycles
descriptive).

| Workload | 0179 cycles change | R cycles change | A cycles change | 0179 instructions change | R | A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| run-numeric | +8.32% | +8.30% | +8.16% | -0.793% | -0.793% | -0.793% |
| run-range_signed | +16.11% | +16.06% | +16.20% | -0.831% | -0.831% | -0.831% |
| run-range_negative | +16.38% | +16.23% | +15.98% | -0.831% | -0.831% | -0.831% |
| run-fib | +2.94% | +2.64% | +2.65% | +2.283% | +2.283% | +2.283% |
| run-calls | +2.72% | +2.86% | +2.90% | +0.452% | +0.452% | +0.452% |
| run-while | +0.22% | +0.18% | +0.05% | -0.783% | -0.783% | -0.783% |
| run-empty | -4.53% | -4.47% | -5.45% | -6.854% | -6.854% | -6.855% |

Group A, same-sample quantities. `task_clock` is in milliseconds; context switches are counts. "Resolved" is the frozen descriptive rule: all five ABBA paired contrasts with one
strict sign AND the pooled median difference beyond the base p10-p90 width. It is not a confidence interval.

| Workload | Quantity | Base median | Candidate median | Relative | Five paired contrasts | Base p10-p90 width | Frozen rule |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| run-numeric | cycles_per_ref_cycle | 1.87973 | 1.87974 | +0.00% | +0.002544, +0.0004805, -0.0008851, +0.0004991, -0.001611 | 0.002993 | unresolved |
| run-numeric | ref_cycles_per_instruction | 0.134783 | 0.146924 | +9.01% | +0.01192, +0.0113, +0.01169, +0.0123, +0.01242 | 0.001605 | resolved up |
| run-numeric | task_clock | 113.623 | 122.775 | +8.05% | +8.923, +8.507, +8.786, +9.283, +9.415 | 1.322 | resolved up |
| run-numeric | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-range_signed | cycles_per_ref_cycle | 1.8751 | 1.87798 | +0.15% | +0.001477, +0.0005394, +0.003, +0.004577, +0.003324 | 0.006715 | unresolved |
| run-range_signed | ref_cycles_per_instruction | 0.12386 | 0.14489 | +16.98% | +0.02107, +0.01986, +0.02097, +0.02074, +0.02105 | 0.002795 | resolved up |
| run-range_signed | task_clock | 85.6048 | 99.1019 | +15.77% | +13.52, +12.67, +13.45, +13.26, +13.52 | 1.998 | resolved up |
| run-range_signed | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-range_negative | cycles_per_ref_cycle | 1.87689 | 1.87851 | +0.09% | +0.00286, +0.001553, +0.001163, +0.002274, -0.0003577 | 0.0089 | unresolved |
| run-range_negative | ref_cycles_per_instruction | 0.123807 | 0.144586 | +16.78% | +0.02077, +0.0201, +0.02089, +0.025, +0.02124 | 0.005427 | resolved up |
| run-range_negative | task_clock | 85.5789 | 98.8797 | +15.54% | +13.35, +12.89, +13.44, +16.11, +13.68 | 3.795 | resolved up |
| run-range_negative | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-fib | cycles_per_ref_cycle | 1.86559 | 1.86424 | -0.07% | -0.004118, -0.004415, +0.003184, -0.001127, -0.0007536 | 0.008718 | unresolved |
| run-fib | ref_cycles_per_instruction | 0.129742 | 0.130522 | +0.60% | +0.00104, +0.0006894, +0.0003763, +0.001035, +0.003449 | 0.001299 | unresolved |
| run-fib | task_clock | 52.4859 | 53.9598 | +2.81% | +1.582, +1.386, +1.298, +1.545, +2.575 | 0.6806 | resolved up |
| run-fib | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-calls | cycles_per_ref_cycle | 1.87689 | 1.87649 | -0.02% | -0.001112, +0.001726, +0.0007822, -0.002874, +0.002839 | 0.005778 | unresolved |
| run-calls | ref_cycles_per_instruction | 0.112606 | 0.115301 | +2.39% | +0.003158, +0.002431, -0.009428, +0.002744, +0.00122 | 0.02434 | unresolved |
| run-calls | task_clock | 96.2345 | 98.9606 | +2.83% | +3.109, +2.472, -7.506, +2.792, +1.418 | 20.61 | unresolved |
| run-calls | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-while | cycles_per_ref_cycle | 1.86423 | 1.87143 | +0.39% | +0.007826, +0.003122, +0.008819, +0.008541, +0.00725 | 0.01019 | unresolved |
| run-while | ref_cycles_per_instruction | 0.127543 | 0.128239 | +0.55% | +0.0001063, +0.001072, +0.0003441, +0.0008956, +0.0009461 | 0.001512 | unresolved |
| run-while | task_clock | 70.3228 | 70.1448 | -0.25% | -0.4709, +0.06149, -0.3932, -0.1176, -0.0481 | 0.8504 | unresolved |
| run-while | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |
| run-empty | cycles_per_ref_cycle | 1.76968 | 1.76132 | -0.47% | +0.02046, -0.003337, -0.02875, +0.01134, -0.0312 | 0.108 | unresolved |
| run-empty | ref_cycles_per_instruction | 0.248838 | 0.2547 | +2.36% | +0.0006463, +0.003393, +0.008172, +0.004291, +0.006377 | 0.01633 | unresolved |
| run-empty | task_clock | 4.38477 | 4.20954 | -4.00% | -0.2484, -0.2046, -0.1316, -0.1863, -0.1602 | 0.3164 | unresolved |
| run-empty | context_switches | 0 | 0 | n/a | +0, +0, +0, +0, +0 | 0 | unresolved |

No sample reported a cpu migration (one would have stopped the run).

## What this supports, and its limits

- The 0179 cycle excess on the numeric and for-range windows reproduces on the same two binaries, in two further
  groups, with different counter groupings.
- In group A the actual-to-reference cycle ratio shows no resolved difference between base and candidate for any
  nonempty workload, while reference cycles per instruction resolve upward for numeric and both range workloads. Under
  section 7d this **weakens a frequency-only explanation** of Q1 on these windows.
- It does **not** establish that the excess is free of host or scheduling effects, nor any causal mechanism. Zero
  context switches and migrations are observations of these user-filtered per-task counters, not proof that host
  effects were absent. Hardware reference cycles exclude descheduled time.
- Frontend, speculation and backend explanations are **untested** in this record: B failed its validity gate and
  C, D, E were not collected. Q2 (fib's instruction growth) has no dynamic attribution beyond R and A.
- Nothing here explains why the compiler emitted different interpreter code for a context.rs-only source change.

Together with Step 0: the two binaries contain different generated interpreter code; the candidate retires fewer
instructions per loop iteration on the range windows and spends reproducibly more cycles and reference cycles doing
so; the mechanism category is unresolved.
