# 0068 gate 4: costs, regression and the walkthrough

The product is rnx `80d40d2` (gate 3; the seam is unchanged since the gate 2
port `a8e0f4e`). The baseline is `73532b5`, the last product before the seam.
Everything builds from matched sources in private build/project/cache storage;
accepted result directories are not overwritten.

From rnx-bench, with `probes/frame-final/target` and `results/frame-final-0068`
absent:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/frame-final/build.py        # matched stock binaries; two Polars projects (present / plain); big.csv
python3 probes/frame-final/stock.py        # the 5% startup gate: version, eval, run, prompt, cells; interleaved, pinned
python3 probes/frame-final/polars.py       # worker cells (present/suppress/preview/collect) on 5 and 200,000 rows; spawn-to-prompt
python3 probes/frame-final/walkthrough.py  # examples/polars/SESSION.md line by line at the prompt
python3 probes/frame-final/regression.py   # fmt, three root configurations, tool, adapters, notices, clippy vs baseline
python3 probes/frame-final/features.py     # dependency and symbol audits, packaged manifest
python3 probes/frame-final/collect.py
```

Run the two timing steps with nothing else building or measuring; they pin
themselves to one core with one Polars thread. `build.py` adds a Git worktree
for the baseline that `collect.py` removes. Journals refuse overwrite.
