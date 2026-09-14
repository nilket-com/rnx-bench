# Record 0041 measurements

Measured by Codex on nano, Linux x86_64, 2026-09-14. Rust 1.98.1,
Rune 0.14.2, hyperfine 1.20.0, CPU 4, 10 warmups, 100 samples per command.
Before is the existing accepted 0040 release, saved before changing code;
after implements plan 7d06f93. Exact hashes identify both binaries.

| Command | Before mean ± σ (ms) | After mean ± σ (ms) |
| --- | --- | --- |
| version | 0.558 ± 0.020 | 0.540 ± 0.016 |
| help | 0.558 ± 0.020 | 0.544 ± 0.018 |
| eval | 4.081 ± 0.045 | 4.003 ± 0.022 |
| run | 3.719 ± 0.013 | 3.665 ± 0.029 |
| json | 11.645 ± 0.141 | 11.597 ± 0.161 |

No startup regression detected in this run. Outliers were reported; small
improvements are observations, not attributed speedups. These are whole-process
times. Binary size: 14,878,600 → 14,879,080 bytes (+480). Session startup
allocation reference: 1,823,087 → 1,823,086 bytes. Later allocation sample:
1,831,716 → 1,831,714 bytes. These samples include presentation and harness
conditions; they are allocator requests, not RSS or an attributed saving.

conditions.json preserves successful exact stdout/stderr comparison of all five
commands, their invocation, versions, hashes and memory samples. startup.json
holds raw samples. diagnostics.json preserves six before/after comparisons:
only the intended fault sentence changes; excerpts and placement are identical.
Both final suites ran sequentially under TERM=xterm-256color: 309 default,
347 test-support, zero failures. Commands and counts are in tests.json.
Linux execution only; Windows remains unverified. Reproduction:
../../probes/method-naming/README.md.
