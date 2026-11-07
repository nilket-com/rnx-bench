# ADR 0221 follower: pure-F64 plan report

Status: Accepted

Follow [rnx ADR 0221](https://github.com/nilket-com/rnx/blob/7c51bf600f9f0655b6d98034dfc2b0d4caafa2ce/plans/adr/0221_f64_plan_driver.md).
No duplicate ADR or acceptance policy is introduced.

Report the large capture's F64 chain at 10M/100M rows, four layouts and
first/warm calls, preserving exact totals and receipt provenance. Keep older
reports as historical snapshots. Disclose pure-F64 multi-operation scope,
x86-64 NaN bit equality, retained output initialization, pinned nonpositive
inlining redistribution, and that old interpreter paths and timing were not
re-measured. Validate coverage and rendering; export no private paths or host
names. Send the report for review before publishing.
