# 0058 gate 6: final regression

From rnx-bench, run `python3 probes/polars-regression/check.py /tmp/rnx-polars-final-check`.
The output directory must not exist. Commands come from the recorded root/adapter
check lists and run serially, with root feature configurations sharing one target.
The original run checked the root and independent adapter targets concurrently;
no two root feature configurations ran together. Keep test logs for packaged
README validation as well as unit/integration results.

Linux requires the existing compiler, cached dependencies and Python worker
fixture prerequisites. The adapter uses the release test profile as earlier
gates did. No new workload or timing comparison is part of this gate: root
source and dependency inputs are unchanged from before 0058.

Strict root clippy fails; the non-strict comparison must match all nineteen
source-located baseline diagnostics from 0057. This is not a clean clippy result.
Adapter clippy passes in both configurations. The Windows cross-check fails in
psm/ring native build tooling without lib.exe on this Linux host; inspect that
log independently, and do not label it type-checked or executed.

`licence-audit.json` records exact upstream trees searched. alloc-stdlib's text
is recovered with its URL/revision/hash in the adapter SOURCES.tsv. syntree has
no licence file at the published revision. polars-parquet-format has a nested
varint-specific text, not a package-wide text; it is not substituted for one.
The two unavailable package-wide texts remain explicit in generated notices.
No generic licence text or a later revision is substituted.
