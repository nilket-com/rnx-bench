# ADR 0240 follower: archived benchmark evidence

Status: Accepted

Follow rnx ADR 0240 at plan commit
`66624931b7f96929738354d40e7ac96fe16d09de` and the reviewed conservative
inventory. Archive restore is verified before changes. Remove only the
reviewed measured-evidence files; retained executable harnesses under
results/ move to probes/retained-results/ with their relative internal
structure. Do not claim archived historical replayers are supported with
missing inputs: execute them from the complete archived snapshot. Supported
README renderers get explicit archive-input resolution while continuing to
write reports into this checkout. Preserve all reported measurements and
caveats; replace broken artifact links with the archive catalog. Never rerun
measurements to fabricate equivalent evidence. Unresolved files, active
configuration and licensing stay. Introduce the same reviewed data-only
hygiene policy with exact duplicate exemptions and explicit retention.

Validate archive restoration/checksums, per-file removal and relocation
lists, retained harness byte equality, archive-aware renderer validation,
unchanged report numbers, hygiene controls, and the follower commit pair.
No history rewrite or force push in this implementation. Publish only after
review, with rnx publication first. Phase 2 remains a separate reviewed dry
run and user-operated force push.

Render from a fresh clone plus the archive root only; regenerated README
measurement numbers must remain byte-identical.
