# 0183 Stage A: official run, COMPLETE, disposition A-mixed; the record closes here

One official run under plan rnx 17d6d5a and grouping audit 2d3a11b. Registered outcome: **COMPLETE**, Stage A
disposition **A-mixed** (numeric `strong`; both range windows `intermediate`). Groups R and F1 each completed 140
samples and reproduced the 0179 anchors. F2 and F3 were excluded before any open (collection state "not collected
(unavailable)": TakenAlone safety beside other possibly active programmable counters cannot be established from primary sources on this host without changing system services (grouping audit rnx 2d3a11b)), so there is no locating event and, by the plan's frozen rules, **0183
closes at Stage A**; Stages B and C do not run. Nothing was repaired, replayed or added after the result. No engine,
profile or product change follows; 0179's STOP is unchanged.

## Identities

- Subjects: the two retained 0179 PRIMARY binaries (base `af06e8b3...0c87`, candidate `e4a5f207...a787`), staged at
  0179's path, E0, CPU 4, hash checked before and after every sample.
- Driver `probes/frontend-0183/events0183.py`, source 384c0fae (tree 46c1e72d), importing the 0180 driver, the 0181
  driver and 0179's helpers as libraries pinned by sha256 and verified before import.
- F1 = instructions, cycles and DSB2MITE_SWITCHES.PENALTY_CYCLES (event 0x61, umask 0x02; "fetch penalty cycles when a
  transition occurs from DSB to MITE" in the pinned Intel table), one strong pinned cpu_core user-only group,
  `--no-scale`.
- Discovery `discovery1` (driver a5f9914c): availability sha256 `c60910efcf21eb4ccacb92a54547cc005c0ffc296ec9cbdd473b845528b8383d`,
  identity sha256 `c281c11d5b0a0d3552415836e66635a9aed03c6fa3162c06f7f921848882f2aa` (byte-identical to 0180's and 0181's).
  Four opens, two per group. Rehearsal `rehearsal1` (384c0fae). Official raw rows sha256
  `02c2868fe77583ea7909b9e4e1c654deb0e518e3b00450227dbbaada342ad891`.

## Disclosures

- Retained control runs: controls1 15/15 (b41dce5d), controls2 15/15 (a5f9914c), controls3 16/16 (384c0fae), each
  replaying 0181's 23 and 0180's 26 controls. No failed dry run occurred for this record.
- Review found one decision-boundary gap before discovery: the verdict validated a difference but not the `resolved`
  and `direction` fields, so three malformed summaries were classified instead of refused. Repaired in a5f9914c with
  the reviewer's reproducers as controls; the real summarizer never emitted such fields.
- The driver never permits a Stage B proposal; general eligibility for a collected locating event is not implemented.
- Sentinel scope as inherited: the official run scans on success and failure; rehearsal on its success path;
  discovery sets none.
- The grouping audit's reasoning about the watchdog is conditional: the exclusion of F2 and F3 rests on unestablished
  safety, not on a demonstrated unsafe operation. No spelling of those events was ever opened.

## The official run

Command, from the repository root at a clean tree, controller environment PATH/HOME/LANG only:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/frontend-0183/events0183.py official results/frontend-0183/official1 results/frontend-0183/discovery1/availability.json

Exit status 0; report status `COMPLETE`; 39 s; 280 raw rows. Admission passed and the identity
was rechecked before each group. No group-local validity failure. Sentinel scan completed, 0 occurrences.

Reproduction anchors (candidate against base):

| Workload | 0179 cycles | R | F1 | 0179 instructions | R | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| run-numeric | +8.32% | +8.50% | +8.08% | -0.793% | -0.793% | -0.793% |
| run-range_signed | +16.11% | +16.10% | +16.09% | -0.831% | -0.831% | -0.831% |
| run-range_negative | +16.38% | +16.02% | +16.22% | -0.831% | -0.831% | -0.831% |
| run-fib | +2.94% | +2.45% | +2.43% | +2.283% | +2.283% | +2.283% |
| run-calls | +2.72% | +2.95% | +2.91% | +0.452% | +0.452% | +0.452% |
| run-while | +0.22% | -0.08% | +0.02% | -0.783% | -0.783% | -0.783% |
| run-empty | -4.53% | -5.92% | -4.75% | -6.854% | -6.854% | -6.854% |

Stage A quantities. `D` is candidate median minus base median over the ten samples per side in the F1 group; `r` is a
ratio of two such differences, formed only for signal windows. "Resolved" is the frozen descriptive rule (five paired
contrasts of one strict sign and a pooled difference beyond the base p10-p90 width).

| Workload | Class | Penalty cycles, base median | candidate median | D(F1) | F1 rule | D(cycles) in the F1 group | cycles rule | r = D(F1)/D(cycles) | Status |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | --- |
| run-numeric | signal | 2,618,970 | 30,990,413 | +28,371,443.0 | resolved up | +36,034,770.0 | resolved up | 0.7873 | strong |
| run-range_signed | signal | 2,626,285 | 15,162,743 | +12,536,458.0 | resolved up | +53,746,886.0 | resolved up | 0.2332 | intermediate |
| run-range_negative | signal | 2,299,269 | 15,271,408 | +12,972,139.5 | resolved up | +54,096,339.0 | resolved up | 0.2398 | intermediate |
| run-fib | reported | 1,470,556 | 1,352,052 | -118,504.5 | unresolved | +4,906,170.0 | unresolved |  |  |
| run-calls | reported | 2,083,108 | 16,931,284 | +14,848,176.5 | resolved up | +10,938,843.0 | resolved up |  |  |
| run-while | contrast | 1,348,474 | 1,308,108 | -40,366.5 | unresolved | +56,136.5 | unresolved |  |  |
| run-empty | contrast | 1,249,584 | 1,207,606 | -41,978.5 | resolved down | -595,777.5 | resolved down |  |  |

Contrast flag: not raised. Threshold is half the smallest signal-window difference, 6,268,229.0
penalty cycles; run-while's difference is -40,366.5 (unresolved) and run-empty's
-41,978.5 (resolved down).

## What the result says, and its limits

- Penalty cycles for switches from the decoded-uop cache to legacy decode rise, resolved, on all three windows whose
  cycle excess reproduces: about 12-fold on numeric and about 6-fold on the two ranges. They do not rise on while or
  run-empty, and are unresolved on fib.
- The size of that rise relative to the excess cycles differs by window: 0.79 on numeric,
  0.23 and 0.24 on the ranges. By the registered rule that is `strong` on one
  window and `intermediate` on two: A-mixed, not A-strengthened. On the ranges the penalty-cycle difference is about a
  quarter of the excess, so most of their excess is not accounted for by this event as it counts.
- On calls (reported only) the penalty-cycle difference, +14,848,176.5, is LARGER than the cycle
  difference in the same group, +10,938,843.0. That is direct evidence that these penalty cycles are
  not an additive component of the measured cycle difference: `r` compares magnitudes and is not an accounting.
- Together with 0181 (more legacy-decode uops and a lower decoded-cache share on the same windows) this strengthens
  the frontend-delivery category as a compatible explanation for the numeric window and leaves it partial for the
  ranges. It does not locate the switches in any function, does not show that code placement or the changed
  instruction stream causes them, and does not explain why the compiler emitted different interpreter code.
- These are whole-process counts on two binaries on one host. Nothing here is a statement about other builds.

Closure: Stage A complete with disposition A-mixed; no locating event; the record closes.
