# ADR 0214 follower: constant integer arithmetic report

Status: Accepted

Follow [rnx ADR 0214](https://github.com/nilket-com/rnx/blob/99790566bbf72e1b1431df95fd0a6e4e89ad7e0b/plans/adr/0214_constant_integer_simd.md).
No duplicate ADR or new acceptance policy is introduced.

Report paired first/warm whole-map instruction counts for constant addition and
both subtraction orders in generic masked chains. Include benign and adversarial
inputs, 10M/100M coverage, complete output checks and exact rescan witnesses.
Explain null-lane neutralization and checked valid overflow. Retain prior reports
as historical snapshots. Distinguish measured and published commits, preserve
binary/profile/receipt hashes in a compact public summary without private paths
or hostnames, and state the approved targets and protected-path non-regression.

Disclose old-path benchmarks not re-measured for 0214 (column-only source scope).
Do not infer elapsed-time gains or a new cross-runtime result. Validate numbers,
coverage and public content; sign the implementation and submit for review.
