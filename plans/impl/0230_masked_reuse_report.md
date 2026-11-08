# ADR 0230 follower: masked F64 output reuse report

Status: Accepted

Follow rnx ADR 0230 after publication. Report all six nullable const/add
100M cells, first/warm process medians and ranges, raw samples, total faults,
and phase-attributed output faults. Explain the unchanged 0228 donation
rules, no hidden retention, and the user-approved sliced-null fault-scope
correction. Preserve the original failed total-fault criterion; do not claim
zero total faults on sliced-null or a first-call speedup. Validate a compact
summary and renderer; exclude private paths and keep artifacts below 1 MB.
