# ADR 0213 follower: mixed-mask integer SIMD report

Status: Accepted

Follow [rnx ADR 0213](https://github.com/nilket-com/rnx/blob/49eb4453cf333e926357ecd71448175449d5a07c/plans/adr/0213_mixed_mask_integer_simd.md).
No duplicate ADR or new acceptance policy is introduced.

Add a short README report with paired first/warm whole-map instruction counts,
10M/100M matrix provenance, and the corrected benign/adversarial comparison.
Distinguish measured and published commits and their tooling-only equivalence.
Archive compact summaries and hashes, retaining raw machine-specific profiles
privately. Explain the exact fixed preparation allowances, not a per-row waiver.

Include the exact rescan witness, scalar constant Add/Sub limitation, initialized
output contract and instruction-count scope. Disclose old-path benchmarks not
re-measured for 0213 (column-only source scope), without implying unchanged LTO.
Keep prior reports intact. Validate numbers, partitions, coverage and added public
content; sign implementation and send for review before publication.
