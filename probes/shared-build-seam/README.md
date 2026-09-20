# 0069 gate 1: the wrapper name, the build kind and the identity

An isolated prototype of record 0069's gate 1 on the project tool only:
the `shared_build` declaration, the digest-named wrapper (generator 4),
the shared-build key, the build kind fixed at lock time (identity format 4),
and the retained format-3 reader. `candidate.patch` is the exact source
against rnx `339c6e3`; `prepare.py` archives the baseline and applies the
patch in its own repository, never in the product checkout. Git-source
projects address a bare origin made from the baseline tree by file URL.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/shared-build-seam/prepare.py        # ~2 min: both tools, the origin, a private Cargo home
python3 probes/shared-build-seam/vectors.py        # shared_build through the readers; the baseline refuses by name
python3 probes/shared-build-seam/identity.py       # locks: names, keys, the eligibility rule
python3 probes/shared-build-seam/compatibility.py  # ~2 min: a baseline entry launches and rebuilds under the candidate
python3 probes/shared-build-seam/control.py        # ~8 min: wrong-binary control, discriminated series on real wrappers
python3 probes/shared-build-seam/checks.py         # ~6 min: fmt, clippy, suites
python3 probes/shared-build-seam/collect.py
```

Run from the bench root with `probes/shared-build-seam/target` and
`results/shared-build-seam-0069` absent.
