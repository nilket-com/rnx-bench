# 0068 gate 1: the presentation seam

An isolated prototype of record 0068's registration seam, driven end to end:
`Extensions::present(name, registrar)`, a context-owned `Presenters` registry
keyed by Rune type hash, the REPL and worker consulting it only for a
top-level result, the Polars presenter and `DISPLAY_FMT`, the optional
`presentation = true` declaration field, and the generated wrapper's separate
`.present(...)` call. `candidate.patch` is the exact source against rnx
`b5664ff`; `prepare.py` archives that baseline and applies it in its own
repository (never in the product checkout).

Run from the bench root with `probes/frame-seam/target` and
`results/frame-seam-0068` absent (or preserved elsewhere):

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/frame-seam/prepare.py     # ~3 min: both trees, both tools, the probe
python3 probes/frame-seam/vectors.py     # declaration vectors, old-tool refusal
python3 probes/frame-seam/identity.py    # locks with both tools; wrapper bytes
python3 probes/frame-seam/consumers.py   # failure/panic-only builders; runner-only consumer
python3 probes/frame-seam/ownership.py   # registry ownership: reset, quit, worker, settings
python3 probes/frame-seam/journey.py     # ~2 min: real Polars application, bare frames
python3 probes/frame-seam/handover.py    # ~3 min: presenter-bearing :dep handover, worker restart (reuses journey's cache)
python3 probes/frame-seam/checks.py      # ~7 min: fmt, clippy vs baseline, all suites
python3 probes/frame-seam/collect.py
```

Prerequisites: Rust/Cargo with the registry cache, Git, `nm`, Python 3, and the
terminal fixture at `probes/project-interactive/common.py`. `journey.py` builds
Polars cold (about 110 s here) into a private cache under `target/`. Fixture
repositories commit with signing disabled. No user cache, store or project is
touched.
