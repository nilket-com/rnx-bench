# 0067 gate 2: integrated management and session protocol

This tests the product port, not another substitute implementation. Stock `rnx`
dispatches management into the internal crate; `rnx-project` is its independently
built compatibility entrypoint. Generated applications use defaults-off rnx.
The real Polars engine/Git acquisition journey is gate 3/4: these protocol matrices
use the accepted tiny catalogue-shaped Polars fixture, a tracked lifecycle adapter,
and (for commitment) the real PostgreSQL adapter and a private cluster.

Git-source describe/decline is live; consent deliberately refuses at the gate-3
boundary before fetch or scratch publication. Path overrides and path projects
perform the complete build, startup probe and handover. No Git acquisition is
claimed here.

## Reproduce

Use an isolated checkout at the reviewed product revision, with source files
tracked/staged and no concurrent edits. The project fingerprinter includes all
tracked working-tree bytes. Linux prerequisites are Rust/Cargo, Git, Python 3.14,
`nm`, and PostgreSQL's installed server tools (the accepted cluster helper finds
them). Registry sources are pre-populated and builds use offline resolution.

Move the **whole** `probes/stock-management/target` and
`results/stock-management-0067` aside before a rerun. Do not reuse a partial
preparation matrix: it may have published a cache entry, making a compiler trap
inapplicable. The replay now refuses an existing group target. All generated
scripts preserve their original driver pathname for imports, archive the effective
text under results/scripts, and record both original and effective SHA-256.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/stock-management/prepare.py
python3 probes/stock-management/clean.py
python3 probes/stock-management/dirty.py
python3 probes/stock-management/boundary.py
python3 probes/stock-management/replay.py stock preparation
python3 probes/stock-management/replay.py stock startup
python3 probes/stock-management/replay.py stock commit
python3 probes/stock-management/replay.py compat preparation
python3 probes/stock-management/replay.py compat startup
python3 probes/stock-management/replay.py compat commit
python3 probes/stock-management/discovery.py
python3 probes/stock-management/scratch.py
python3 probes/stock-management/checks.py
```

After every consumer is closed, remove the baseline through Git:

```sh
git -C ../rnx worktree remove ../rnx-bench/probes/stock-management/target/baseline
```

The developer's retained `refresh_clean.py` records the correction from the early
environment-carrier experiment; it is not part of a fresh replay.

## Coverage and retained evidence

- Both frontends pass 44 preparation, 17 startup and eight commitment groups.
  Fault and pause hooks come from product test-support builds. Production framing,
  process groups, cancellation, real VM ownership and startup execute unchanged.
- 29 boundary groups compare ordinary flags, diagnostics and files named project,
  runtime and cache against accepted `4e887b6`. Selfcheck's success is tested
  separately because its output includes its elapsed time. A settings-read
  positive control distinguishes management bypass from an unused counter.
- A real clean fixture build reaches the unverified Git notice; the dirty working
  build refuses. A started HTTP operation and binding survive refusal, decline,
  and the named gate-3 stop. Fetch traps stay untouched; no state/cache is created;
  an uninterpretable selected installation is not consulted.
- Ten discovery groups cover missing/relative/invalid tools, unsupported peers,
  bounded timeout/reaping, PATH discovery, and a real old-manager-issued capsule.
  Old manager `4e887b6` builds its own project and interoperates with the current
  runner through a consented, injected pre-author failure. It does not launch a
  new-generator project lock: that ordinary launch correctly refuses the changed
  wrapper. Gate 3 owns retained-envelope workflow compatibility.
- Recovery commands and the successful scratch reopen command are executed by
  `/bin/sh` exactly as printed, with apostrophes/spaces in paths and neither
  frontend on PATH. Scratch restart keeps PID/cwd, drops bindings, resets the
  prompt, and supports another `:dep` in the replacement.
- The generated artifact has no management symbols. The defaults-off graph has
  no management package; neither stock nor runner graphs include Polars or the
  PostgreSQL driver. The root's source manifest, notice selection, and intentional
  unpublished-package refusal are tested explicitly.

`product.patch` is the measured product source against `4e887b6`;
`clean.bundle` preserves the actual clean fixture revision with that prerequisite.
The final root commit adds evidence/status and corrects README's `repl` spelling;
these documentation changes were not inputs to the locked protocol fixtures.
Final test counts are 376 root default, 419 root support, 389 defaults-off runner
with project-sources; tool 51 passed and two explicitly ignored integration/audit
tests in each configuration. Tool clippy denies warnings in both configurations.

The `early/` directory retains the environment-marker experiment and partial
fixtures. The root env test found that the marker changed `env::vars()`; the
product uses a thread-local stock-entry flag in the internal crate instead.
A source edit during an early build correctly triggered before/after inventory
refusal. A partial compatibility rerun hit an already-published entry and could
not reach its compiler trap; the final matrix ran from an absent target. Other
harness corrections were selfcheck's dynamic time, using `repl` (the literal
`session` is already not a runner command), the HTTP response field, fixture event
environment, and exact old/new diagnostic spelling. No assertion was relaxed to
accept a product ownership or cancellation failure.
