# 0069 gate 4: costs, regression and documentation

The product is rnx `6acde0b` (gate 3 plus the documentation pass); the
baseline is `c6d8a1c`, the product before this record. Both stock binaries
build from matched sources; every Git-source project addresses a bare origin
of the baseline tree, so both binaries compile the same runtime and adapters
and only the tool differs. Private build/project/cache storage throughout.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/shared-build-final/build.py       # matched binaries, the origin, a private Cargo home
python3 probes/shared-build-final/stock.py       # the 5% startup gate: version, eval, run, prompt, cells
python3 probes/shared-build-final/matrix.py      # ~25 min: first Polars, second wrapper, + PostgreSQL, attach; three interleaved repeats
python3 probes/shared-build-final/regression.py  # fmt, three root configurations, tool, adapters, notices, clippy vs baseline
python3 probes/shared-build-final/features.py    # dependency and symbol audits, packaged manifest
python3 probes/shared-build-final/collect.py
```

Run the two timing steps with nothing else building; `stock.py` pins itself
to one core. `build.py` adds a Git worktree for the baseline that
`collect.py` removes. Journals refuse overwrite.
