# Bare rustc and the 42 test

Quoted claim: “if you just use bare rustc you often don't even have compile times above your terminals refresh rate”. No tweet URL or author was supplied; this tests that quoted timing claim on this machine.

The columns below use the requested rounded frame budgets: 16.7 ms (60 Hz), 8.3 ms (120 Hz), 6.9 ms (144 Hz). “Often” has no defined frequency; the observed fraction is reported instead of silently defining it. Every row has 90 fresh invocations. These are compile **and link** timings, excluding execution.

| Configuration | Mean ms | Min | Median | p95 | <16.7 ms | <8.3 ms | <6.9 ms |
|---|---|---|---|---|---|---|---|
| build-empty-default | 36.492 | 33.572 | 36.561 | 38.076 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O | 39.161 | 36.545 | 39.238 | 40.841 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-dynamic | 24.197 | 22.430 | 24.005 | 26.155 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-cgu1 | 37.078 | 34.156 | 36.653 | 37.801 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-dynamic | 27.160 | 25.113 | 27.202 | 28.685 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-cgu1 | 38.837 | 36.378 | 38.669 | 40.479 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-dynamic-cgu1 | 24.174 | 22.713 | 24.041 | 25.845 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-dynamic-cgu1 | 26.431 | 24.558 | 26.358 | 27.911 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-default | 37.427 | 34.850 | 37.572 | 39.049 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O | 40.479 | 37.676 | 40.403 | 42.145 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-dynamic | 25.645 | 23.078 | 25.519 | 27.416 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-cgu1 | 38.284 | 35.340 | 37.710 | 39.360 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-dynamic | 28.285 | 26.031 | 28.367 | 30.073 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-cgu1 | 39.795 | 36.967 | 39.781 | 41.200 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-dynamic-cgu1 | 25.422 | 23.671 | 25.510 | 27.077 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-dynamic-cgu1 | 27.863 | 25.289 | 27.562 | 29.719 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-default | 36.701 | 34.059 | 36.733 | 38.609 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O | 39.780 | 37.309 | 39.719 | 41.085 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-dynamic | 24.397 | 22.482 | 24.512 | 25.706 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-cgu1 | 36.909 | 34.352 | 36.771 | 38.337 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-dynamic | 27.744 | 25.521 | 27.546 | 29.308 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-cgu1 | 39.617 | 36.341 | 38.988 | 40.752 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-dynamic-cgu1 | 24.486 | 22.647 | 24.429 | 26.147 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-dynamic-cgu1 | 26.871 | 25.047 | 26.825 | 28.377 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| human-unpinned | 57.607 | 38.712 | 57.165 | 66.159 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| four-cores | 23.078 | 22.289 | 22.917 | 23.991 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |

The last two rows repeat the fastest pinned full-build configuration, `build-empty-dynamic`, without affinity restriction and on four cores. They are later controls, not interleaved comparisons with the initial run. The fastest row was selected on the measured data; it is descriptive, not an independent performance test.

For complete executable builds on this machine, **0/2340** samples finished within the rounded 60 Hz frame budget. The quoted below-refresh claim was not observed for any tested full-build configuration. Stage-only emission does often meet that budget here; it skips some required work and cannot run. This does not establish how frequently the claim holds on other machines or for other programs.

The unpinned median (57 ms) is 2.4× the same configuration pinned to one core (24 ms), and slower than four cores (23 ms); on this hybrid i7-14700, scheduling onto E-cores or migration is a plausible but unmeasured explanation, and the unpinned case represents ordinary unrestricted invocation.

## Source to answer

Every program here prints exactly `42\n`. Rust compiles and links on every sample, then starts the new executable. The runtimes parse/compile their input during startup. Source writing and output deletion are outside the clock. No binary reuse is credited to Rust in this table.

| Configuration | Mean ms | Min | Median | p95 | p10–p90 |
|---|---|---|---|---|---|
| answer-print-default | 38.226 | 34.950 | 38.275 | 39.724 | 36.586–39.367 |
| answer-print-O | 41.031 | 38.672 | 40.937 | 42.403 | 39.806–42.237 |
| answer-print-dynamic | 26.017 | 24.395 | 26.004 | 27.733 | 24.780–27.139 |
| answer-print-cgu1 | 38.248 | 35.466 | 38.162 | 39.673 | 36.726–39.440 |
| answer-print-O-dynamic | 28.992 | 27.218 | 29.067 | 30.527 | 27.560–29.993 |
| answer-print-O-cgu1 | 40.285 | 37.405 | 40.238 | 41.817 | 38.701–41.633 |
| answer-print-dynamic-cgu1 | 26.250 | 23.788 | 26.291 | 27.787 | 24.762–27.404 |
| answer-print-O-dynamic-cgu1 | 28.258 | 26.034 | 28.185 | 30.612 | 26.828–29.708 |
| rnx-eval | 5.015 | 4.281 | 4.741 | 6.507 | 4.513–6.421 |
| rnx-run | 4.469 | 3.759 | 4.310 | 5.986 | 4.087–4.977 |
| python | 9.623 | 8.378 | 9.180 | 11.441 | 8.824–11.116 |
| perl | 1.111 | 0.864 | 1.038 | 1.138 | 0.958–1.107 |
| lua | 0.518 | 0.435 | 0.493 | 0.539 | 0.460–0.534 |
| luajit | 0.553 | 0.449 | 0.543 | 0.576 | 0.506–0.567 |
| bun | 2.625 | 2.070 | 2.546 | 3.187 | 2.410–2.695 |
| node-official | 16.122 | 14.121 | 15.778 | 17.624 | 15.364–17.524 |
| ruby | 36.783 | 34.956 | 36.335 | 38.542 | 35.775–38.437 |
| deno | 25.309 | 11.680 | 24.437 | 58.550 | 15.947–26.203 |

## Stages and existing binaries

Metadata emission does not produce an executable; object emission skips linking. These are diagnostic paths, not source-to-answer alternatives. Existing-executable rows include process startup and printing but **exclude compilation**. `/bin/true` and compiler-version rows are overhead observations; no subtraction is applied.

| Configuration | Mean ms | Min | Median | p95 | <16.7 ms | <8.3 ms | <6.9 ms |
|---|---|---|---|---|---|---|---|
| empty-metadata | 10.295 | 8.982 | 9.920 | 11.675 | 90/90 (100%) | 0/90 (0%) | 0/90 (0%) |
| empty-obj | 13.425 | 12.338 | 13.233 | 14.699 | 89/90 (99%) | 0/90 (0%) | 0/90 (0%) |
| print-metadata | 11.134 | 9.745 | 10.985 | 12.576 | 90/90 (100%) | 0/90 (0%) | 0/90 (0%) |
| print-obj | 14.570 | 13.165 | 14.350 | 15.831 | 88/90 (98%) | 0/90 (0%) | 0/90 (0%) |
| exit-metadata | 10.420 | 9.211 | 10.120 | 11.748 | 89/90 (99%) | 0/90 (0%) | 0/90 (0%) |
| exit-obj | 13.924 | 12.724 | 13.731 | 15.164 | 88/90 (98%) | 0/90 (0%) | 0/90 (0%) |
| cached-print-default | 0.447 | 0.386 | 0.440 | 0.478 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| cached-print-O | 0.460 | 0.389 | 0.438 | 0.481 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| cached-print-dynamic | 0.677 | 0.594 | 0.666 | 0.730 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| true | 0.348 | 0.296 | 0.349 | 0.392 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| rustc-version | 5.338 | 4.568 | 5.020 | 6.775 | 90/90 (100%) | 90/90 (100%) | 86/90 (96%) |

## Clock audit

The deciding dataset is `native-final/`: a dependency-free Rust clock helper measures all compiler and interpreter commands inside the same native spawn/capture/blocking-wait interval. Preflight median `/bin/true` was 0.317 ms versus hyperfine 0.240, and cached Rust 0.381 versus 0.353; both passed the pre-agreed ±0.15 ms sanity bound. The original polling-Python dataset is retained at this directory’s parent, and the blocking-Python replay in `blocking-final/`. The latter failed the sanity bound (true 0.499 ms); neither is used for the deciding fast-runtime rankings. The independent 50-sample `hyperfine.json` is also retained. No overhead subtraction or sample removal is applied.

## What was measured

- Standalone stable rustc 1.98.1, invoked at its real toolchain path; no Cargo or rustup launcher in timed commands, no dependencies, LTO, or incremental compilation. Output is deleted before each fresh compile; the filesystem and compiler/standard-library pages are warm, not cold disk.
- Intel i7-14700, Linux; affinity core 4. Governor `powersave`, driver `intel_pstate`, min/max kHz 800000/5300000, intel no_turbo=0. Governor names alone do not state actual clock frequency.
- Five warmups, three seeded shuffled rounds of 30 samples per row. Synchronous spawn/capture/wait, no shell, identical driver for each tool. In the deciding native-clock run, argument preparation, helper startup, output/status validation and serialization are outside the timer; child process spawn, pipe capture and blocking waits are inside it. Means, min, median, p95 and p10/p90 are retained; raw samples and per-round summaries are in JSON.
- Full builds cross three inputs and eight configurations. `empty` is `fn main(){}`; `print` uses println; `exit` exits with 42 and avoids printing. Default has no explicit optimization flag; `O` means `-O`, dynamic means `-C prefer-dynamic`, cgu1 means `-C codegen-units=1`. Exact commands are retained.
- Dynamic-standard-library executable checks run with its toolchain library directory in LD_LIBRARY_PATH (same environment for all rows); this is an explicit configuration, not the default bare command. Every executable was checked before timing. Linker identification per executable is retained in conditions.json. Stable output reports bundled LLD 22.1.8; no separate mold/ld.lld was found on PATH and nothing was installed.
- Stable exec/thread attribution is untimed under strace. Installed nightly time-passes is supplemental attribution from a different compiler, not a decomposition of the stable wall-time samples. Those diagnostics cannot be subtracted from the primary results.
- This tiny startup/compile workload says nothing about application throughput or large builds. Empty Rust and unused literals can be optimized away; this is not an arithmetic benchmark. Results on other hardware, toolchains, operating systems or linkers are unmeasured. The follow-up about LTO while building an interpreter concerns a different workload and is outside this probe.
