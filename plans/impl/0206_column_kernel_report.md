# ADR 0206 follower: published column-kernel report

Status: Accepted

Follow the Rune decision at
https://github.com/nilket-com/rune/blob/fed878b5aea151a878462d71626c9a4d589a4273/plans/adr/0206_validity_aware_column_kernels.md
and the published rnx follower at
https://github.com/nilket-com/rnx/blob/002584a48d1f714e3856f5a3d6a99ac86c2204eb/plans/impl/0206_validity_aware_column_kernels.md.
No duplicate ADR or new measurement policy is introduced here.

Update the README and add a report for the published 0206 column kernels.
Archive compact summaries and SHA-256 provenance for both binaries, six kernels,
four layouts and 10M/100M rows, separating first and warm map calls. Preserve the
historical 0205 host/Polars comparison and its original numbers.

Disclose the reviewed old-path accounting and its pinned exceptions. Report the
separate single-sample whole-CLI user-cycle observations with their scope and
limitations: flat i64add +3.4% is unconfirmed timing variation, not proof of a
regression or its absence. Do not invent missing baseline wall times or repeat
successful samples. Make no new cross-runtime comparison claim.

Provide an offline renderer that validates archive hashes, coverage and cost
partitions. Verify both the new and historical report renderers, inspect the
diff, and scan public artifacts for private machine names and home paths.
Publish only summaries and hashes; retain raw machine-specific evidence in the
measurement archive. The implementation content was reviewed in rune-native
27084; this plan precedes its local restack and fast-forward publication.
