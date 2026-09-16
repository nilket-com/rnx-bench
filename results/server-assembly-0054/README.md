# 0054 assembly evidence: HTTP cleanup stop

Two complete runs against rnx c28cf22, using the actual battery and extension
installers in an isolated private-test build. Source and reproduction are in
`../../probes/server-assembly/`. conditions.json in each run records provenance,
source and binary hashes; run.log records execution. summary.json derives from
the two results.jsonl files. Each run contains one schema event, eighteen
scheduling cases and four ownership/isolation events.

The fixture passes by **asserting the stop**, not by closing gate 2. Neither
shape is selected and no HTTP library decision follows yet.

- Serial: sixteen sleeping requests then a quick request take about 330 ms for
  the quick request; two serving contexts/builders. Four-way multiplexing per
  worker reduces that to 125–131 ms, with seventeen contexts/builders.
- Finite awaiting-batch rate: 51.5 versus 108.5–115.9 requests/s. These are
  dispatch measurements, not HTTP throughput.
- Awaiting-batch peak tracked allocation increase: ~4.57 MB versus ~7.64 MB,
  including the fixture. Context build wall-time sums: ~15 ms versus ~93–104 ms.
  Context creation is on the multiplexed request path; serial initialization
  precedes dispatch. See the probe README for memory and timing definitions.
- Both shapes still delay healthy work when both workers are CPU-bound.
- Tracked-operation revocation isolates failures across workers and between
  same-worker handlers. The failed inner future remains strongly retained,
  proving actual revocation; the healthy operation survives and completes.
- Cross-worker HTTP cleanup between block_on calls preserves the healthy peer.
- Same-worker HTTP cleanup inside block_on panics at nested block_on. Calling it
  outside block_on as a diagnostic control times out after ~103 ms because the
  whole-runtime zero-task condition includes a healthy peer's request. The
  failed socket closes cleanly and the healthy response subsequently succeeds.
  Four tasks are observed before that control, zero after final fixture cleanup.

The injected module and test-only Runtime accessor do not change production
code, public API, manifests or lockfiles. Root suites were not rerun for this
probe-only change. The complete narrative is in rnx's companion 0054 assembly
evidence. Gate 3 waits on an await-compatible, owner-scoped cleanup decision.
