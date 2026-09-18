# 0065 gate 5: nested reuse port, floor stop

Root checkpoint: `2bf4871`; previous accepted checkpoint: `e6844b6`.
Full narrative: rnx `plans/0065_a_launch_checks_each_native_file_once_product_evidence.md`.
Reproduction: `probes/nested-product/README.md`.

**Gate 5 is stopped, not passed.** All 4500 matched headline samples and 360
fallback samples are retained. The adapter increments are below 1 ms, but the
zero-adapter improvement is only 0.60–0.80 ms rather than the required 3 ms, in
all six mode/repeat combinations. See gate.json, summary.json and the raw journals.

The accepted product oracle replay passes 36 primary cases and 16 topology/roster
cases. Tool formatting, strict clippy and tests pass: 46 default, 47 test-support,
two ignored each. Counters and pause hooks are absent from the ordinary release.
The inherited-GIT_PAGER unit fixture correction and original failure are retained.

Eval overheads in milliseconds, two repeats:

| Adapters | SHA-256 baseline | BLAKE3 format-only | Reuse port |
| --- | ---: | ---: | ---: |
| 0 | 17.63 / 17.52 | 12.28 / 12.16 | 16.87 / 16.92 |
| 1 | 22.41 / 22.53 | 16.27 / 16.21 | 17.72 / 17.66 |
| 2 | 26.57 / 26.56 | 20.09 / 19.95 | 18.15 / 18.16 |
| 3 | 30.58 / 30.69 | 23.72 / 23.75 | 18.74 / 18.72 |

The 4097-file ignored-target control exhausts the 4096-entry descendant budget:
23.20 / 23.21 ms overhead, against clean 18.87 / 18.81 ms. GIT_PAGER forces full
independent inventory: 29.28 / 29.11 ms. These shape blocks are sequential;
project/direct observations are interleaved within each. Inputs are restored and
the lock pair/receipt are unchanged. No compiler ran during measurement.

conditions.json pins the product source and binaries; implementation.patch and
the signed root commit preserve the measured code. No post-measurement optimization
is substituted. Full topology/depth/attachment/installed-adapter journeys and gate 6
remain outstanding after the stop. No pruning or format migration is introduced.
