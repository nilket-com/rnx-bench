# 0179 independent reconstruction

`probes/startup-0179/audit.py` reads the committed official1 raw rows and
summaries. It imports no measurement or decision code. It checks explicit
runtime environments, controller/representative child affinity, process
cleanup and artifact hashes; parses raw PMU counters; reconstructs ABBA sample
orders, medians, wall receipt values and deciles; verifies all decision rows
and gate lists; rebuilds allocation counts, calibration differences and
historical reproduction medians from the pinned references. Both cold
first-use outputs are checked explicitly. Cycles are descriptive.

Commands (read-only, under /tmp/rnx-runtime-bench.lock; command timeout120s,
five-second kill grace), exit0 each:

```sh
python3 probes/startup-0179/audit.py results/startup-0179/official1/p0-cand
python3 probes/startup-0179/audit_controls.py results/startup-0179/official1/p0-cand
```

`audit.json` is the independent report, bound to the official raw-file SHA-256.
`controls.json` accepts the original and refuses11 altered copies. Missing
PMU/wall samples or first-use workloads, changed medians/allocation counts,
forged first-use output/hash/decision/gate list and NaN cycle median fail.
Controls create temporary copied cells and remove only those copies; neither
original samples nor binaries are modified, and no subject is executed.
