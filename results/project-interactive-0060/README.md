# 0060 Linux evidence

All four new orchestration groups, five real journey groups, nine direct eval
comparisons, invalid-Unicode comparison and the copyable README example pass.
The old sixteen workflow groups and seven 0059 contract groups pass unchanged.
Root code and dependencies are untouched. Tool suites pass 37 tests each with
two explicitly ignored integrations; strict Clippy, formatting and notices pass.
Windows checks pass with the pre-existing test-only unused import warning and
no execution claim.

Median milliseconds, two repeats:

| Boundary | Project default | Full --verify | Direct artifact |
| --- | --- | --- | --- |
| eval completion | 24.56 / 24.62 | 90.57 / 90.58 | 6.50 / 6.51 |
| first session prompt | 23.38 / 23.44 | 89.47 / 89.25 | 5.18 / 5.23 |

Every default overhead is below 25 ms (about 18 ms). This is not a speedup
claim against another engine or a notebook timing. All 240 samples are retained
in samples.json and the incrementally written journal.jsonl. Conditions record
commands, hashes, CPU, terminal geometry, source baseline and clocks. Preparation
logs and lock snapshots identify the measured project, not a portable current lock.
source.patch applied to the recorded rnx plan commit reconstructs the measured
tool source and README before final evidence/status edits.

The first PTY attempt's matcher omitted rustyline's trailing carriage return and
timed out at a correctly opened prompt. The matcher was corrected before the
successful journeys and timing; no product change or timing sample was discarded.
The known 0059 metadata coverage limitations and source fingerprinting are unchanged.

Raw PTY logs include terminal controls by design; use the corresponding .txt for
reading. All test data, history, settings and outputs were private. Temporary
processes were reaped. Bench's older result directories were restored after reruns.
