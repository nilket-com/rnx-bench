# ADR 0212 follower: borrowed column operands report

Status: Accepted

Follow [rnx ADR 0212](https://github.com/nilket-com/rnx/blob/0f95d955081fd21d43b04bba6b5fac6f1b6bc084/plans/adr/0212_borrowed_column_operands.md).
This report introduces no new measurement policy or duplicate ADR.

Add a short README update using the accepted paired 10M/100M map instruction
capture. Archive compact first/warm results and provenance hashes; retain raw
machine-specific profiles privately. Identify the baseline, measured candidate,
and published candidate, explaining the tools-only difference. Preserve older
report sections and their original measurements.

State explicitly: old-path benchmarks not re-measured for 0212 (column-only
source scope). Do not imply binary identity, wall-time gains, new cross-runtime
measurements, removal of output initialization, or generic mixed-mask SIMD.
Validate table numbers against the capture and scan added public content for
private hostnames and home paths. Send the completed report for review.
