# Record 0050 evidence

`conditions.json` contains complete output/status comparisons, exact fixture
source, commands, executable hashes and toolchain. `timings.json` and
`measurement.log` are the matched whole-process hyperfine exports. Reproduce
with `probes/file-modules/measure.py`; the before revision is rnx `e6c56cd`.

The suite logs are Linux runs with `TERM=xterm`. The final focused loader
run additionally checks queued declarations after early allowance exhaustion.
Root clippy returns nonzero on both revisions for two inherited denied
permission-literal lints; all 35 code-bearing diagnostics have identical
multiplicity. `clippy-comparison.json` records the comparison, with both raw
JSON streams preserved.

The Windows files distinguish a failed whole-root build (ring cannot find
MSVC `lib.exe`) from a successful compile-only check of the actual changed
sources and their unit tests with signature stubs for surrounding modules.
No Windows execution was performed. Root dependencies and notices are unchanged.
