# 0065 gate 5 F2: floor repaired, first-adapter stop

Root checkpoint: `1a15f9d`; accepted previous stop: `2bf4871` / `fc30b5c`.
Narrative: rnx `plans/0065_a_launch_checks_each_native_file_once_directory_evidence.md`.
Reproduction: `probes/nested-directory/README.md`.

F2 observes each directory once and bypasses observation when no roots are nested.
The optional file-stamp Vec change is not included. No new format, dependency or
root runtime change is introduced. There is no post-measurement optimization.

All 36 oracle/mutation and 16 topology cases pass unchanged, including the same-
process case. Tool formatting, strict clippy, 46 default / 47 test-support tests
and notices pass (two ignored each).

The unchanged timing matrix retains all 4500 samples across 75 cells: two repeats,
30 observations per cell, fixed seed, one CPU/Polars thread, three ordinary tools
and per-product direct controls. Fallback adds 360 retained samples.

| Adapters | F2 eval overhead, repeats |
| --- | ---: |
| 0 | 12.16 / 12.23 ms |
| 1 | 14.60 / 14.57 ms |
| 2 | 15.06 / 15.15 ms |
| 3 | 15.65 / 15.64 ms |

The floor passes with over 5 ms improvement versus baseline. **Gate 5 still stops**:
the first adapter adds 2.30–2.44 ms in every mode/repeat, above the 1 ms bound.
Later increments are about 0.46–0.63 ms. gate.json contains the six failures.

Diagnostic one-native statx counts, traced after timing: format-only 2883,
previous port 7073, F2 3334. These are this fixture's counts, not traced latency
or an isolated attribution of every remaining millisecond. Raw traces are saved.

Three-adapter fallback overhead: clean 15.72 / 15.68 ms, exhausted 4096-entry
budget 19.96 / 19.99 ms, inherited GIT_PAGER 25.62 / 25.57 ms. Fixture inputs,
lock pair and receipt are restored/unchanged; no process remains. Shape blocks
are sequential with project/direct interleaved inside each.

conditions.json and implementation.patch preserve code identity alongside the
signed root source commit. Remaining topology/depth/attachment/installed journeys
and gate 6 are not claimed complete. The removal record remains immediately after
0065; the review's 15 GB cache observation grants no pruning authority here.
