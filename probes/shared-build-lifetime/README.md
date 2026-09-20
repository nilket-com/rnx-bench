# 0069 gate 3: lifetime, removal and the catalogue declarations

The product at rnx `e69d06b` (gate 2 plus the catalogue declarations),
built as the stock `rnx`; a bare Git origin of that tree with three
revisions: the tree, plus two 0061-style retained-output natives (an
embedding reader, and a runtime-configuration reader whose build script
re-runs on a declared environment input), plus a build-script change.
PostgreSQL queries run against the 0055 fixture cluster.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/shared-build-lifetime/prepare.py    # ~2 min
python3 probes/shared-build-lifetime/lifetime.py   # ~8 min: the sequences, every executable observed after each step
python3 probes/shared-build-lifetime/catalogue.py  # add writes the declaration; existing and path declarations left alone
python3 probes/shared-build-lifetime/checks.py     # ~5 min
python3 probes/shared-build-lifetime/collect.py
```

Run from the bench root with `probes/shared-build-lifetime/target` and
`results/shared-build-lifetime-0069` absent; needs `/usr/lib/postgresql/18`.
