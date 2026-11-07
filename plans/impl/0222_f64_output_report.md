# ADR 0222 follower: F64 write-only output report

Status: Accepted

Follow [rnx ADR 0222](https://github.com/nilket-com/rnx/blob/e4e6f465f14740476bf57f1425e48df7e796ef10/plans/adr/0222_f64_output_ownership.md).
No duplicate ADR or acceptance policy is introduced.

Report exact whole-map instruction totals at 10M/100M and descriptive
100M first/warm timings for four layouts against ADR 0221. Preserve source
receipt hashes and measured/published commit identities. Disclose single
samples without statistical claims, retained failed timing receipts and
reuse of four validated samples. Explain the size-dependent memset Ir and
unchanged bytes per row. Keep the column-only scope and historical reports.
Validate coverage, rendering and privacy; send for review before publishing.
