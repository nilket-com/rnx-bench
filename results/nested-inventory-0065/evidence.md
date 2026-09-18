# 0065 gate 4: nested-root equivalence

Root checkpoint: `e6844b6`. Isolated candidate/oracle base: `7b0bb65`.
Full narrative: rnx `plans/0065_a_launch_checks_each_native_file_once_nested_evidence.md`.
Reproduction: `probes/nested-inventory/README.md`.

- 36 primary matrix cases compare exact quiescent results and allowance, then
  record timed metadata/index/boundary changes and restored-mtime divergence.
- 16 additional cases cover topology, bounded discovery fallback, the actual
  zero-to-three roster, and a second inventory call in the same process.
- Runtime floor: 443 files / 6,988,177 bytes. Independent physical reads at zero
  through three adapters: 443 / 466 / 487 / 508. Candidate: 443 at every count.
  Tool-issued Git calls fall from 3 / 6 / 9 / 12 to 3 in every eligible shape.
- Isolated real workflow: default/verify accept unchanged sources, both refuse a
  pre-launch restored-mtime content edit, and restoration succeeds. Lock pair and
  receipt stay unchanged.
- F1: absolute quoted runtime recovery executes under /bin/sh with no rnx-project
  on PATH. A 30-case adapted migration replay passes as well.
- Product fmt, strict clippy, both 46-test configurations and notices pass. The
  isolated candidate passes strict all-target clippy and 46 library tests with
  test-support. Two pre-existing tests remain ignored in each suite.

The candidate/trace/workflow modifications are archived in source/ and
candidate.patch, with source/binary hashes in provenance.json. Counter instrumentation
is confined to the copy. Product native inventory remains unchanged; the only
production edit is F1. No latency claim or automatic pruning is introduced.

Ignored descendants are searched for repository boundaries under a 4096-entry
eligibility budget. Exhaustion falls back without changing logical allowances.
The discovery cost and fallback topology slopes are gate 5's measurements.
The documented same-size restored-metadata mutation after the read is deliberately
shown as missed by reuse until the next inventory; it is not called equivalent
concurrent-edit detection. Fixture and candidate corrections are named in the
root evidence; all final cases were rerun after correction.
