# HTTP lifecycle migration, record 0055

Measured by Codex on nano/Linux, 2026-09-16. These fixtures exercise the actual
root battery and lifecycle, not a replacement HTTP implementation. Historical
0054 fixtures/results remain under `server-assembly` unchanged.

- `assembly.py --output results/http-lifecycle-0055/assembly` archives rnx HEAD
  plus its tracked working diff, records that patch, and injects `assembly.rs`
  as a private test module. It uses the existing server-assembly target cache.
  The second run is under `assembly-confirmation`. No manifest or public API
  changes are injected. An empty working diff is valid after the root commit.
- `assembly.rs` derives from the accepted 0054 fixture. Only the HTTP installer,
  cleanup/teardown expectations and healthy-future priming are changed. Inline
  requests must be polled until their headers are sent; the old one-poll prime
  relied on the removed detached task. Same held peers, failure, clean EOF,
  healthy response, admission shapes, ownership and count assertions remain.
- `worker.py` exercises stock-worker HTTP cancellation, unrelated interrupts,
  caught errors, reset and final shutdown. Proxy/config environment is isolated.
- `regressions.py` rebuilds the external assembly/lifecycle and PostgreSQL
  ownership executables, reruns their existing fixtures, and reruns the real
  Jupyter supervision/recovery fixtures. It redirects all result directories
  here, keeping historical exports unchanged. Requires the existing pinned
  Jupyter probe venv and kernel binary, plus PostgreSQL 18 tools. It creates its
  own temporary database cluster; it never uses the system database.
- `measure.py` compares stock binaries on CPU 4, eight warmups and 80 samples per
  label/workload in ABBA blocks. Times include Python subprocess spawn/wait and
  capture, with no shell per sample. `RNX_HTTP_BEFORE` selects a baseline binary;
  the default is the saved prechange `/tmp/rnx-0055-baseline/rnx` built at the
  plan commit `2c76d38` (same production code as `20f8310`). To reproduce elsewhere,
  build that revision separately and set the variable. After is the current
  root release binary. Complete outputs must agree.
- `http-cost.py` uses a private HTTP/1.1 fixture with TCP_NODELAY, two ABBA worker
  rounds, one pooled connection per 21 requests, and signal-to-settlement times.
  It also records allocator transcripts before/after reset and runtime progress.
  It uses the same baseline override. Cancellation settlement timings do not
  imply equivalent cleanup: the old path drained, the new one only revokes.

Root suites carry the durable drop-observer, snapshot, lazy-client, retained
expiry, pool, editing Ctrl-C and shutdown-failure gates. The test-support-only
`rnx_test::test_shutdown_task` deliberately injects a never-ending async task;
worker shutdown must settle a runtime failure with state loss, then exit 1 after
ack. It does not exist in the shipped binary.

`results/http-lifecycle-0055/` contains raw results and check logs; root record
0055's companion evidence interprets them. No Windows execution is claimed.
