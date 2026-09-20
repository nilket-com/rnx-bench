# 0068 gate 3: the interactive and notebook journey

The product at rnx `a8e0f4e` (the gate 2 port), archived with `git archive`
and built in `target/product`: the stock `rnx` and the `rnx-jupyter` kernel.
One Polars project is authored by `rnx project add polars` (which writes
`presentation = true`), locked and built into a private cache. Then a real
session at a pseudo-terminal (xterm-256color, 30 rows × 120 columns) and a
real kernel in a private Jupyter environment.

Run from the bench root with `probes/frame-journey/target` and
`results/frame-journey-0068` absent:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/frame-journey/prepare.py    # ~5 min: product, kernel, Polars project
python3 probes/frame-journey/journey.py    # the prompt journey
python3 probes/frame-journey/notebook.py   # the kernel journey (re-executes itself under the venv)
python3 probes/frame-journey/collect.py
```

Prerequisites: Rust/Cargo with the registry cache, Git, Python 3, the terminal
fixture at `probes/project-interactive/common.py`, and the
`probes/jupyter-notebook/.venv` virtual environment (jupyter_client and
nbformat) from record 0047. The kernel fixture uses a temporary HOME and
Jupyter data/config/runtime directories; the user's kernelspecs are checked
unchanged before and after. No user cache, store or project is touched.
