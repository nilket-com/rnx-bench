# 0059: everyday launch passes the gate

New default whole-pipeline medians: **28.84 / 28.86 ms** versus old
**154.58 / 154.73 ms**. Explicit --verify is **95.07 / 94.95 ms**;
generated-direct is **10.80 / 10.78 ms**. Both acceptance gates pass:
at least 70% improvement and at most 25 ms over direct, in each repeat.

Implementation: rnx b200a14. This is the intentional metadata-stamp default,
with source-content checks unchanged. All 400 ordinary product observations
and their journal are retained. Separate transition medians are about 98.24 ms
for v1 migration, 98.25 ms for metadata mismatch, 77.34 ms for first override
establishment (the override declares no native input tree). See transitions.json.

Inventory subdivision: Git 5.86 ms, native tree read/metadata/hash 10.09 ms,
ancestor/config audit 0.21 ms, inclusive parent 16.30 ms. Do not sum the parent
with its children. These instrumented/control launches are separate from the
ordinary product acceptance timing.

Both suites pass 37 tests, two old integrations ignored. Both clippy modes,
formatting, notices and Windows type-check pass. No Windows execution claim.
Seven new receipt/coverage groups, the existing sixteen-group workflow and real
PostgreSQL project pass. Refer to probes/project-run-default/README.md and the
root default evidence for reproduction, mutation coverage and qualifications.
