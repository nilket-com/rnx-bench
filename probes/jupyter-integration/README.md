# Record 0047 integration checks

`transport.sh` builds `rnx/jupyter`'s transport-probe example and runs 0048's
unchanged scenarios against that owned component and its message codec. Outputs
are in `results/jupyter-0047-integration`. The old prototype remains available
for reproducing its own evidence; binary and result overrides select the new one.

`browser.py` smoke-tests the pinned Playwright Chromium prerequisite. It does
not open JupyterLab and does not claim the notebook gate.

Both use `probes/jupyter-transport/.venv`, pinned by that probe's requirements.
These scripts install no kernelspec and touch no personal notebook configuration.
