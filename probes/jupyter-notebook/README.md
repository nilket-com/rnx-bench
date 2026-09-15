# Record 0047: installation and the real notebook frontend

From the bench root, with the adjacent rnx release worker built:

```sh
uv venv probes/jupyter-notebook/.venv --python python3.14
uv pip sync --python probes/jupyter-notebook/.venv/bin/python probes/jupyter-notebook/requirements.txt
probes/jupyter-notebook/.venv/bin/python -m playwright install chromium
bash probes/jupyter-notebook/run.sh
```

This is a separate environment from the accepted transport/supervision probes.
It retains JupyterLab 4.6.3, Jupyter Server 2.21.0 and Playwright 1.62.0, but pins
Tornado 6.5.8. The prior 6.5.9 static-file change expects an attribute that the
server's FileFindHandler does not initialize; the original failure is preserved.
The browser is Chromium 151.0.7922.34 in this run. No Python package is added to
rnx-jupyter's graph. This does not recommend these pins for public deployment.

Every installer/browser fixture gets temporary HOME, Jupyter data/config/runtime
directories and executable paths with spaces. No personal kernelspec is changed.
LSP server discovery is disabled in the browser fixture; the tested feature is
kernel execution, not language-server assistance. The Jupyter app is exposed to
the browser fixture for invoking the same notebook commands used by menus.
Screenshots are page captures with no compositing or drawn terminal substitutes.

- `install.py`: genuine CLI installation; exact argv; existing/invalid spec
  refusal; explicit replacement; non-Unicode paths; missing CLI guidance.
- `status.py`: shell kernel-info remains pending during execution, control info
  answers immediately, then normal execution recovers. A deliberately delayed
  SUB gets both kernel-info status messages after subscription is observed.
- `notebook.py`: nbclient uses the installed spec, executes, saves and reopens.
- `browser.py`: selects Rune in JupyterLab; runs values/errors; reloads during a
  pending cell without reporting idle; interrupts; restarts; proves old bindings
  are gone; runs again, validates nbformat, saves and reopens. Reloaded pages do
  not recreate the old client's cell future, so visible interrupt output is
  tested on a fresh request. Restart completion is followed by a real execution,
  not a requirement for an unsolicited idle before that execution.
- `timing.py`: twenty launches, each followed by one first and thirty warm cells.
  Times include the Python client's observation path. Ready includes client
  channel startup and wait_for_ready; it is not raw executable startup.
- `startup.py`: five byte-equivalence cases and pinned hyperfine on ordinary rnx.
  The accepted and current ordinary binaries are deliberately byte-identical;
  measured differences are variation, not a kernel-induced optimization.

The runner repeats the four acceptance fixtures, reruns the prior supervision and
wire fixtures into new directories, then measures on core 4. The prior fixture
now accepts RNX_JUPYTER_RESULTS to preserve old evidence. It records exit codes,
versions and source/binary hashes. Root suites run sequentially separately, and
their logs are copied into the results. Clean build timing is also separate,
after the latency run, against an empty temporary target directory with downloads
already cached. Timeouts are failure bounds, not evidence that messages arrived.

Windows checks cover the portable package and explicit unsupported supervisor;
no Windows notebook execution is claimed. Review notes remain outside git.

After record 0049, the notebook and status fixtures run against the new
namespaces. Set `RNX_NOTEBOOK_RESULTS` to a fresh directory to preserve
accepted captures. `startup.py` is deliberately the historical 0047
identical-binary assertion, pinned to its recorded worker hash and old API;
it is not a current-head startup gate. The full historical `run.sh` must
be reproduced at its original commit. Use `probes/namespaces/run.sh` for
the 0049 comparison and migrated notebook fixtures.
