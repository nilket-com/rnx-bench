# 0056 gate 4 extraction results

Implementation: rnx `3f8f6af`. Exact binary/source hashes and build commands:
`../../probes/server-extraction/build.json`. The test-support binary's SHA-256 is
`3bddd776c7508ce3d67fe0128e72312eb79a5ac3202b0d98140ab51c09aecaf2`.
The ordinary binary is `259e8b0b0f4de7a5570bb5d467c8c22875f5d5d44865b1d3c896e0beb4874076`.

- `wire`: 57 cases, original assertions unchanged.
- `transactions`: eight original cases, independent observer and fault proxy.
- `shutdown-int`, `shutdown-term`: thirteen cases each; driver/overall deadline
  cases exit 1 without a clean-close event. Other rows certify owner disposal.
- `classification`: four injected SQLSTATE integration cases, one COMMIT each,
  fresh replacement backend, independent zero victim-row observation. Actual
  serialization and deadlock mechanisms remain gate 3's separate evidence.
- `blocked-stderr`: full 65,536-byte pipe unread until exit 1 at 5,027 ms; the
  original bytes remain intact. Remaining ownership is in the event log.
- `normal`: default build, echo/commit/rollback, test-only compile refusal,
  ignored driver injection and preserved inherited stdin socket identity.
- `scheduling`: final coherent three-sample run of every unchanged scenario.
  Healthy median ms: alone 4.33, awaiting-spare 5.75, CPU-spare 8.73,
  CPU-saturated 68.51, mixed 4.96, awaiting-batch 104.24. No matched speedup claim.
- `scheduling-overlap-miss`: the preceding repeat failed the saturation overlap
  precondition, retained without changing that assertion. The cause of its
  68.77 ms preparation delay is not isolated. The initial successful aggregate
  is kept as `initial-scheduling-results.json`; some raw files from that first
  attempt were overwritten by the repeat, so it is not the final evidence set.

Each server launch records the actual extracted binary and program hash;
archived prototype metadata is labelled as reference. Private PostgreSQL
clusters are created and reaped by the existing cluster helper. Successful
rows independently observe backend disappearance. No system server is touched.
Only Linux execution is claimed. Gate 4 is ready for review; gates 5–6 remain
open.
