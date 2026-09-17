# Verified launch: where the time goes

Pre-draft measurements for 0059, against the closed 0058 tree at 48831ec. No product code or verification policy changed.

Two repeats, 20 samples per cell, one pinned CPU and one Polars thread. All 240 observations retained with checked outputs. Medians in milliseconds:

| Whole launch | Init | Tiny pipeline |
| --- | --- | --- |
| stock | 150.97 / 151.05 | 155.20 / 154.99 |
| profile | 150.94 / 150.87 | 155.26 / 155.55 |
| direct | 6.46 / 6.55 | 10.80 / 10.88 |

Pipeline phase medians; intervals are disjoint. The small unmeasured remainder includes tool startup/dispatch, comparisons and instrumentation output.

| Measured group | Repeat 1 | Repeat 2 |
| --- | ---: | ---: |
| project_open | 0.063 | 0.065 |
| lock_pair_read_decode | 0.469 | 0.467 |
| manifest_read | 0.022 | 0.022 |
| declaration_map | 0.020 | 0.020 |
| reconstruct_metadata | 0.007 | 0.007 |
| layout_map | 0.018 | 0.017 |
| source_inventory | 0.049 | 0.049 |
| native_inventory | 16.772 | 16.789 |
| wrapper_identity | 0.016 | 0.018 |
| receipt | 0.064 | 0.064 |
| map_publication | 2.828 | 2.840 |
| artifact_fingerprint | 123.198 | 123.204 |
| command_map_check | 0.016 | 0.016 |

## What this settles

The artifact fingerprint accounts for about 123 ms of the roughly 144 ms tool overhead. The hypothesis is now measured inside the actual tool, rather than inferred from coreutils hashing. Native inventory adds about 16.8 ms; map publication adds about 2.8 ms. The separate Rune source inventory is about 0.05 ms. The stock and instrumented whole-launch medians agree within about 0.6 ms on both repeats; the clocks do not explain the expensive row.

Removing artifact fingerprinting entirely would still leave roughly 21 ms of tool overhead in this scenario. That is arithmetic on observed costs, not a measured fast implementation or a latency promise. Keeping all other checks unchanged cannot plausibly meet the proposed few-millisecond-over-direct target here. Native input identity and map publication must be considered separately.

The native_inventory bucket includes Git, ancestor/config inventory and native working-tree hashing. It has not been subdivided, so it does not prove those 16.8 ms are all content hashing. This fixture has no mounted source dependencies; a larger Rune source tree can change that row.

## Candidates for the design, not implemented changes

The general hash_files helper updates both a content digest and a tree digest for every chunk. fingerprint::one calls that helper and retains only the file record. A specialised single-file fingerprint may avoid unused tree work while preserving content verification; compiler behaviour and the actual saving need their own measurement. No claim of a twofold improvement follows from source inspection alone.

Every run also republishes the same content-addressed map through fsync/rename/directory-fsync. Reusing an already validated identical map is another candidate that need not replace content checks with inode checks. Its concurrency and malformed-existing-file behaviour must still be specified.

A metadata-based artifact cache remains a distinct policy choice. Path/size/inode alone misses same-size in-place edits. Any such record needs explicit cache assumptions, a full-verification path, mutation and replacement tests, and separately measured input costs. Start with semantics-preserving work rather than assuming weakened verification is required.

## Reproduction and limits

See probes/project-run-cost/README.md. Full instrumented source, minimal diff, source revision, hashes, refreshed local project locks, build logs, launch commands, all samples and per-check timings are retained here. Compiler/dependency caches were warm. This is Linux evidence only and not a notebook measurement. No Cargo build, setup or cleanup is inside the launch clock. The previous Polars correctness/timing evidence is untouched.
