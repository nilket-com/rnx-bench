# ADR 0220 follower: packed Boolean plan report

Status: Accepted

Follow [rnx ADR 0220](https://github.com/nilket-com/rnx/blob/662a82143fa27699a746fe1ee35dbde7f98e70d3/plans/adr/0220_boolean_plan_driver.md).
No duplicate ADR or acceptance policy is introduced.

Use the publication packet's Boolean table as the single source for AND, OR
and chain, all four layouts, 10M/100M rows and first/warm calls beside the
published baseline. Preserve exact instruction totals and receipt provenance.
Disclose pure-Boolean scope, column-only validation, old interpreter paths not
re-measured, and instruction counts without wall-clock measurements. Keep prior
reports as historical snapshots. Validate coverage and arithmetic; export no
machine-specific paths or host names. Send the report for review before publishing.
