# 0070: quiet and verbose dependency preparation

Stock installs of the product (`8d33b85`, the record's impl commit) and of 0069's product (`39beeaa`,
capability version 1) from a bare origin by `cargo install --git`, plus a
runner-only session build of each for the cross-version directions.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/quiet-dep/prepare.py        # ~4 min
python3 probes/quiet-dep/journey.py        # ~5 min: :dep quiet (build, attach, postgres), :depv, a failure, Ctrl-C, same key
python3 probes/quiet-dep/verbose.py        # :depv held to 0067's journey
python3 probes/quiet-dep/exec_failure.py   # a named exec failure under :dep (test-support pause)
python3 probes/quiet-dep/compatibility.py  # the two peer directions
python3 probes/quiet-dep/checks.py         # ~7 min
python3 probes/quiet-dep/collect.py
```

Run from the bench root with `probes/quiet-dep/target` and
`results/quiet-dep-0070` absent. Every session runs in a private HOME.
