# 0070 gate 3: costs and regression

The product is rnx `8d33b85`, the record's impl commit; the baseline is `39beeaa`, the product before
this record. Matched stock binaries for the startup gate; a stock install of
the product from a private origin (0067's fixture pattern) for the
transition timings.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/quiet-dep-final/build.py       # matched binaries; the install
python3 probes/quiet-dep-final/stock.py       # the 5% startup gate
python3 probes/quiet-dep-final/transition.py  # ~10 min: :dep vs :depv, cold once each, warm interleaved
python3 probes/quiet-dep-final/regression.py  # fmt, three root configurations, tool, adapters, notices, clippy vs baseline
python3 probes/quiet-dep-final/features.py
python3 probes/quiet-dep-final/collect.py
```

Run the timing steps with nothing else building. Only `stock.py` pins itself
to one core; `transition.py` deliberately does not, because a pinned driver
hands its affinity to Cargo and serialises the first builds. `build.py` adds
a Git worktree that `collect.py` removes.
