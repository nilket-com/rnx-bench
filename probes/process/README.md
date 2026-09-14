# Record 0044 process facade

Codex, nano, 2026-09-14. Run from any directory with two preserved release
binaries built from the plan's parent and implementation tree:

```
python3 probes/process/measure.py /absolute/before/rnx /absolute/after/rnx
```

Linux fixture (`/bin/true`); whole-process elapsed times include startup.
The harness checks exit status, full stdout and stderr equivalence before
measuring, records binary hashes, versions and session memory, and uses
core 4, ten warmups and 100 runs. The child comparison includes both the
old facade on both binaries and the new facade on the new binary.

Results are under `results/process_0044`. `preliminary-*` preserves the
first measurement, which overlapped test execution and is superseded by
the idle rerun; it must not be used to attribute the noisy differences.
The Windows type-check extension is in `../fs-portability`; it does not
execute the process fixtures.
