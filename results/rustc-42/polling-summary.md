# Bare rustc and the 42 test

Quoted claim: “if you just use bare rustc you often don't even have compile times above your terminals refresh rate”. No tweet URL or author was supplied; this tests that quoted timing claim on this machine.

The columns below use the requested rounded frame budgets: 16.7 ms (60 Hz), 8.3 ms (120 Hz), 6.9 ms (144 Hz). “Often” has no defined frequency; the observed fraction is reported instead of silently defining it. Every row has 90 fresh invocations. These are compile **and link** timings, excluding execution.

| Configuration | Mean ms | Min | Median | p95 | <16.7 ms | <8.3 ms | <6.9 ms |
|---|---|---|---|---|---|---|---|
| build-empty-default | 37.859 | 35.273 | 37.925 | 39.213 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O | 41.050 | 38.401 | 40.810 | 42.225 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-dynamic | 25.745 | 23.537 | 25.817 | 27.305 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-cgu1 | 37.919 | 35.015 | 37.853 | 39.406 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-dynamic | 28.645 | 26.462 | 28.549 | 30.323 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-cgu1 | 40.620 | 37.602 | 40.106 | 42.290 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-dynamic-cgu1 | 25.454 | 23.573 | 25.171 | 27.185 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-empty-O-dynamic-cgu1 | 28.147 | 25.775 | 27.991 | 29.639 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-default | 39.352 | 36.895 | 39.062 | 40.732 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O | 42.009 | 39.091 | 41.838 | 44.139 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-dynamic | 26.793 | 25.053 | 26.899 | 28.508 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-cgu1 | 39.255 | 37.087 | 39.166 | 40.493 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-dynamic | 29.958 | 27.272 | 30.169 | 31.286 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-cgu1 | 41.241 | 38.002 | 41.108 | 42.806 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-dynamic-cgu1 | 26.857 | 25.133 | 26.892 | 28.478 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-print-O-dynamic-cgu1 | 29.250 | 26.632 | 29.062 | 31.026 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-default | 38.420 | 35.359 | 38.285 | 39.762 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O | 41.482 | 38.187 | 41.272 | 42.691 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-dynamic | 26.081 | 24.179 | 26.006 | 27.948 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-cgu1 | 38.402 | 35.711 | 38.310 | 39.658 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-dynamic | 29.220 | 26.835 | 29.259 | 30.918 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-cgu1 | 40.682 | 37.976 | 40.453 | 42.047 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-dynamic-cgu1 | 26.132 | 23.865 | 26.042 | 27.983 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| build-exit-O-dynamic-cgu1 | 28.214 | 26.139 | 28.496 | 30.089 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| human-unpinned | 58.263 | 42.055 | 59.241 | 65.508 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |
| four-cores | 23.287 | 22.271 | 23.091 | 24.428 | 0/90 (0%) | 0/90 (0%) | 0/90 (0%) |

The last two rows repeat the fastest pinned full-build configuration, `build-empty-dynamic-cgu1`, without affinity restriction and on four cores. They are later controls, not interleaved comparisons with the initial run. The fastest row was selected on the measured data; it is descriptive, not an independent performance test.

## Source to answer

Every program here prints exactly `42\n`. Rust compiles and links on every sample, then starts the new executable. The runtimes parse/compile their input during startup. Source writing and output deletion are outside the clock. No binary reuse is credited to Rust in this table.

| Configuration | Mean ms | Min | Median | p95 | p10–p90 |
|---|---|---|---|---|---|
| answer-print-default | 41.400 | 37.795 | 41.151 | 42.951 | 40.340–42.523 |
| answer-print-O | 43.881 | 42.147 | 43.782 | 45.319 | 42.889–44.957 |
| answer-print-dynamic | 29.052 | 26.765 | 29.174 | 30.438 | 27.591–30.069 |
| answer-print-cgu1 | 41.189 | 39.534 | 40.849 | 42.713 | 40.179–42.331 |
| answer-print-O-dynamic | 31.989 | 29.834 | 31.981 | 33.612 | 30.371–33.296 |
| answer-print-O-cgu1 | 43.185 | 40.493 | 43.103 | 44.604 | 42.137–44.403 |
| answer-print-dynamic-cgu1 | 29.160 | 26.963 | 29.220 | 30.928 | 27.593–30.556 |
| answer-print-O-dynamic-cgu1 | 31.337 | 28.742 | 31.384 | 33.161 | 29.701–32.882 |
| rnx-eval | 6.443 | 5.451 | 6.139 | 7.918 | 5.894–7.851 |
| rnx-run | 5.846 | 5.078 | 5.702 | 7.273 | 5.421–6.721 |
| python | 10.918 | 9.893 | 10.565 | 12.518 | 10.129–12.332 |
| perl | 2.461 | 2.051 | 2.373 | 2.604 | 2.226–2.499 |
| lua | 1.817 | 1.675 | 1.812 | 1.922 | 1.722–1.906 |
| luajit | 1.921 | 1.685 | 1.857 | 2.042 | 1.771–1.999 |
| bun | 4.043 | 3.283 | 3.924 | 5.531 | 3.652–4.330 |
| node-official | 17.524 | 15.965 | 17.142 | 18.941 | 16.686–18.856 |
| ruby | 38.060 | 36.082 | 37.665 | 39.868 | 37.009–39.728 |
| deno | 26.969 | 12.932 | 25.759 | 59.703 | 15.789–28.065 |

## Stages and existing binaries

Metadata emission does not produce an executable; object emission skips linking. These are diagnostic paths, not source-to-answer alternatives. Existing-executable rows include process startup and printing but **exclude compilation**. `/bin/true` and compiler-version rows are overhead observations; no subtraction is applied.

| Configuration | Mean ms | Min | Median | p95 | <16.7 ms | <8.3 ms | <6.9 ms |
|---|---|---|---|---|---|---|---|
| empty-metadata | 11.411 | 10.348 | 11.266 | 12.664 | 90/90 (100%) | 0/90 (0%) | 0/90 (0%) |
| empty-obj | 14.962 | 13.509 | 14.618 | 16.611 | 85/90 (94%) | 0/90 (0%) | 0/90 (0%) |
| print-metadata | 12.482 | 11.218 | 12.283 | 13.849 | 89/90 (99%) | 0/90 (0%) | 0/90 (0%) |
| print-obj | 15.916 | 14.480 | 15.733 | 17.270 | 69/90 (77%) | 0/90 (0%) | 0/90 (0%) |
| exit-metadata | 11.736 | 10.609 | 11.491 | 12.957 | 89/90 (99%) | 0/90 (0%) | 0/90 (0%) |
| exit-obj | 15.159 | 13.933 | 15.051 | 16.335 | 89/90 (99%) | 0/90 (0%) | 0/90 (0%) |
| cached-print-default | 1.921 | 1.611 | 1.803 | 3.262 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| cached-print-O | 1.797 | 1.601 | 1.774 | 1.901 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| cached-print-dynamic | 2.029 | 1.842 | 1.988 | 2.138 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| true | 1.696 | 1.527 | 1.671 | 1.806 | 90/90 (100%) | 90/90 (100%) | 90/90 (100%) |
| rustc-version | 6.564 | 5.779 | 6.356 | 7.956 | 90/90 (100%) | 90/90 (100%) | 72/90 (80%) |

## What was measured

- Standalone stable rustc 1.98.1, invoked at its real toolchain path; no Cargo or rustup launcher in timed commands, no dependencies, LTO, or incremental compilation. Output is deleted before each fresh compile; the filesystem and compiler/standard-library pages are warm, not cold disk.
- Intel i7-14700, Linux; affinity core 4. Governor `powersave`, driver `intel_pstate`, min/max kHz 800000/5300000, intel no_turbo=0. Governor names alone do not state actual clock frequency.
- Five warmups, three seeded shuffled rounds of 30 samples per row. Synchronous spawn/capture/wait, no shell, identical driver for each tool. Intermediate compiler status validation is included between compile and execution. Means, min, median, p95 and p10/p90 are retained; raw samples and per-round summaries are in JSON.
- Full builds cross three inputs and eight configurations. `empty` is `fn main(){}`; `print` uses println; `exit` exits with 42 and avoids printing. Default has no explicit optimization flag; `O` means `-O`, dynamic means `-C prefer-dynamic`, cgu1 means `-C codegen-units=1`. Exact commands are retained.
- Dynamic-standard-library executable checks run with its toolchain library directory in LD_LIBRARY_PATH (same environment for all rows); this is an explicit configuration, not the default bare command. Every executable was checked before timing. Linker identification per executable is retained in conditions.json. Stable output reports bundled LLD 22.1.8; no separate mold/ld.lld was found on PATH and nothing was installed.
- Stable exec/thread attribution is untimed under strace. Installed nightly time-passes is supplemental attribution from a different compiler, not a decomposition of the stable wall-time samples. Those diagnostics cannot be subtracted from the primary results.
- This tiny startup/compile workload says nothing about application throughput or large builds. Empty Rust and unused literals can be optimized away; this is not an arithmetic benchmark. Results on other hardware, toolchains, operating systems or linkers are unmeasured. The follow-up about LTO while building an interpreter concerns a different workload and is outside this probe.
