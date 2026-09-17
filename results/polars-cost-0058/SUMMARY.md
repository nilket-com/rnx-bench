# 0058 gate 5 observations

Warm launches, normal Python bytecode caching. Two interleaved repeats; 30 samples per product/workload/repeat. No samples discarded. Different engine revisions: no boundary-only attribution.

| Product | Init medians (ms) | Pipeline medians (ms) | Pipeline p95 (ms), pooled | Pipeline peak RSS median (MiB) |
| --- | --- | --- | --- | --- |
| python | 96.71 / 96.80 | 99.87 / 99.99 | 101.06 | 86.5 |
| ordinary | 6.76 / 6.73 | 11.44 / 11.47 | 11.70 | 45.9 |
| project | 150.76 / 150.11 | 155.10 / 154.81 | 155.71 | 48.7 |
| generated-direct | 6.61 / 6.69 | 10.88 / 10.85 | 11.09 | 48.6 |
| aligned-direct | 6.77 / 6.80 | 11.49 / 11.45 | 11.68 | 46.4 |

Empty-target Rust build, cached downloads, two jobs: 505.48 s. Warm build: 0.19 s.
Private Python venv: 0.613 s; install exact cached wheels: 0.479 s. No download timing.
Fingerprint tree bytes per launch: 6,977,812; executable hashes and byte sizes are in conditions.json. Ancestor/config inventory is additional.

GNU time peak RSS is a separate launch observation including native threads, not a sum of concurrent process-tree RSS. Timing includes no-shell process spawn/capture/wait overhead. CSV creation, both reads, collect, write and close/flush are inside pipeline time; directory setup/removal and fsync durability are not.

The rejected preliminary no-bytecode-cache block is retained separately and contributes no samples to this table.
