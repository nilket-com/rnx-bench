# 0064 gate 5: installation and matched launch costs

From the bench root, with this probe's ignored `target/` absent:

```sh
python3 probes/runtime-cost/setup.py
python3 probes/runtime-cost/build.py
python3 probes/runtime-cost/installation.py
python3 probes/runtime-cost/measure.py
python3 probes/runtime-cost/collect.py
```

Run in that order without other builds or benchmarks running. Setup copies the
clean published rnx snapshot, builds its ordinary project tool and installs that
snapshot. Build creates four fresh assemblies sequentially: checkout/installed,
one native (Polars) and two (Polars + PostgreSQL). Registry sources are already
cached and Cargo is offline; targets and assembly entries start absent. These
cold builds use the normal available CPUs and are separate from pinned launch
costs. The originals stay available here as explicit checkout controls; gate 4
proved operation after their removal.

Installation builds an isolated instrumented copy of the same tool. Its exact
changed files are archived, with the published source baseline. Named existing
installer boundaries produce monotonic timestamps, plus start/end points. Two
interleaved repeats each contain ten fresh-store ordinary installs and ten timed
installs. The ordinary-vs-instrumented wall totals show instrumentation cost rather
than assuming it away. Source and Git administration byte counts are separate.

Measure pins one allowed CPU and sets POLARS_MAX_THREADS=1 before spawn. Each
repeat randomizes all four project shapes, three modes (run/eval/first prompt),
and three routes (default/verify/direct), twenty samples per cell. Every exit,
stdout/stderr or first prompt is verified. Run and eval create one expression;
they measure startup, not the CSV/Parquet engine pipeline already proven by gate 4.
All 1,440 samples remain in the journal, with no outlier rejection. A per-sample
private cwd/history/config keeps input accumulation outside the result.

Forty ready attachments are separately measured with compiler traps and positive
controls; they include full artifact verification and receipt publication. The
160 describe samples measure spawn to the tool's validated notice, then decline
and reap the child. Checkout uses the explicit runtime override; installed uses
the selected default. File traces of ordinary installed eval assert that neither
installation.json nor current.json is consulted on launch. Native source content
inventory is still performed, as the everyday contract requires.

For a full rerun, remove only `target/` and the prior launch-samples.jsonl journal.
The other result files are overwritten. Do not reuse incomplete assemblies as
cold samples. The initial scaffolding run assumed a separate assembly key field
in the lock; the lock stores canonical identity bytes instead. It failed before
any assembly compiled, and its log is retained. The final build driver hashes
those bytes and checks the corresponding ready path is absent before building.
No product implementation changes belong to this cost gate.

The recorded first checkout build overlapped compilation of the isolated timing
tool during setup; its cold duration is a single observed cost, not a matched
speed comparison. The timing parent was paused before any samples and resumed
after all cold builds. The documented sequential rerun avoids that overlap.
The installed/checkout launch comparison and installation wall controls ran
without concurrent fixture builds. The retained-tree allocation totals include
directories; the source/Git subtotals count file bytes separately.
