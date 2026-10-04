# Rune route-table dispatch probe

This compares the same stock rnx binary on main-mode and routes-mode versions of
the retained web skeleton. The content and helpers before `main(request)` are
byte-identical. The 26 response fixtures and three consecutive responses on one
HTTP/1 connection must pass before load starts. Application development remains
in its own repository.

Build stock rnx at the implementation revision in `results/web-0165/provenance.json`
with `CARGO_INCREMENTAL=0 cargo build --locked --release --bin rnx`, and copy it to
`target/stock`. Build baseline 2a06a81 the same way in an isolated checkout and copy
it to `target/baseline`. Those binaries are ignored; their hashes and sizes are
retained. The sources, lockfile and tool provenance are retained too.

From the bench repository root:

```
python3 probes/web-0164/host_controls.py probes/web-0165/target/stock
python3 probes/web-0165/host_controls.py probes/web-0165/target/stock
python3 probes/web-0165/run.py NEW_OUTPUT_DIRECTORY
python3 probes/web-0165/validate_saved.py NEW_OUTPUT_DIRECTORY
python3 probes/web-0165/saved_controls.py NEW_OUTPUT_DIRECTORY
python3 probes/web-0165/overhead.py NEW_OUTPUT_DIRECTORY
python3 probes/web-0165/count.py
```

Two workers use CPUs 2,4 and oha uses 8,10,12,14. Logs are off in both paths.
Five conditions × two paths × three interleaved repetitions give 30 measured
samples and 60 complete warmup/measurement artifacts. Warmups are 3 seconds,
measurements 10 seconds. Saved validation checks every exit, duration, status,
error, latency, throughput, connection count, command and row binding. Corruption
controls exercise refusal. The gate requires routes/main median throughput at
least 0.95 in every condition. This dispatch comparison makes no axum or Flask
performance claim. Logger overhead is measured separately in 0164.

The line census includes full sources, the unchanged helper/content prefix and
dispatch/declaration tails separately. Flask's module docstring is excluded only
from noncomment code lines, reproducing 0162's 62-line reference. It is not a
claim that the two full source totals have identical presentation content.

For the inherited 0068 startup gate, populate `startup/binaries.json` with hashes
and sizes and set `RNX_STARTUP_OUT` to that directory before `startup.py`. It uses
two interleaved repeats and stops on a >5% increase reproducing in both. Do not
build or run other tests during timed measurements. Matcher-only and returned
table allocation measurements are ignored rnx unit tests, run alone; their logs
are retained separately and do not count as HTTP performance.
