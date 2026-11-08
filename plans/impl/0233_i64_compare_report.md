# ADR 0233 follower: packed I64 comparison report

Status: Accepted

Follow rnx ADR 0233 at published implementation commit
`bc4a2065b04f9f023f1275de63b7e15deabc37db`. Publish a
compact, validated summary and README section with the all-six-operation
instruction matrix, I64 equality timing, and the original F64 timing together
with its separate investigation. Disclose the original fixed-order scheduling
flaw; the corrected investigation does not repeat I64 timing or establish
zero effect. Include first/warm distributions, per-process samples, counter
resolution, exact protected-driver and portable setup exceptions, source
identity and final receipt hashes. Cite Arrow/Polars only as data-derived,
cross-day ADR 0224 context. State that unchanged interpreter paths and 100M
unchanged-path system bands were not re-measured. Render only after runtime
publication and all required gates PASS; exclude private names and paths,
keep the artifact below 1 MB, and validate idempotent generation.
