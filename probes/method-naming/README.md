# Record 0041 method naming

Run from the bench root: `python3 probes/method-naming/measure.py BEFORE AFTER`.
Before is the existing accepted 0040 release, copied before changing code;
the saved hash identifies that binary. After implements plan 7d06f93. The runner preserves
binary hashes, toolchain, exact command outputs, session allocation observations,
and 100 whole-process samples per command on CPU 4 after 10 warmups.

The regular Rust gates cover diagnostic naming, retained sources across renumber,
redefinition, unavailable origin, fallback and budget-clause ordering. Tests.json
preserves final suite commands and totals. No Windows execution is claimed.

Run `python3 probes/method-naming/diagnostics.py BEFORE AFTER` for six release
comparisons asserting unchanged placement/excerpts and only the intended sentence
replacement. Raw results are in diagnostics.json.
