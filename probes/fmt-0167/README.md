# 0167 formatter controls and startup cost

The product uses Rune 0.14.2's public formatter, bounded in a lean re-exec worker.
No adapter, dependency build, network or source evaluation is needed to format.
The fixtures exercise the command, not a substitute formatter.

`checks/builds.json` under `results/fmt-0167` binds the measured binaries to the
clean implementation commit and SHA-256s. The baseline executable was retained
from 0166 at 89c9ce5; its relevant source is byte-identical to ffa2d4e (the
zero-length diff is checked). Build a stock release binary and a release binary
with `--features test-support` from the recorded product commit, copying them
into this probe's ignored `target/stock` and `target/test-support`. Copy the
baseline into `target/baseline`. Do not run Cargo builds during timing: different
feature configurations share the executable path.

From rnx-bench, using new output directories:

```
python3 probes/fmt-0167/probe.py probes/fmt-0167/target/stock probes/fmt-0167/target/test-support results/fmt-0167/new-probe
RNX_STARTUP_OUT=$PWD/results/fmt-0167/new-startup python3 probes/fmt-0167/startup.py
```

`probe.py` checks a dense valid 1,048,575-byte source, typical-source latency,
seven worker controls, six known upstream corruption/refusal cases, all six
committed demos' formatting/idempotence, and the three offline demos' execution
outputs. Resource samples come from `/proc` and include the worker's virtual
peak and RSS high-water mark. CPU accounting includes the entire CLI plus its
reaped worker, an upper bound on worker CPU. One sample is reported per workload,
not a latency distribution. `startup.py` retains 7,200 interleaved samples in
six rounds on one allowed CPU. The pre-stated aggregate-median 5% slowdown gate
is unchanged; round medians and spreads are retained.

`framed-final/` and `startup-final/` are the final product measurements.
Earlier root-level, `final/` and `startup/` artifacts are preliminary, before
framed worker transport and later controls. They are retained, not pooled with
the final samples. In particular the preliminary startup run briefly overlapped
an unrelated baseline build; the final run had no Cargo builds by this team.

The application formatting-only diff and before/after HTTP checks are retained
separately. They test the same local source layout; no deployment happened.
The final formatter checks that source without rewriting it. The application
name/content appears here, not in rnx's generic plan or implementation.

## Upstream-main comparison

`upstream-main.rs` is Claude's scratch program, replayed read-only by Codex.
Build a scratch crate with that source and:

```
[dependencies]
rune = { path = "/home/me/work/rune/crates/rune", default-features = false, features = ["std", "fmt"] }
```

Pin the Rune checkout to bb8e69372353c50e271c9f115bc771c77aa6b83e, then run:

```
python3 probes/fmt-0167/upstream.py /path/to/target/release/runefmt-main results/fmt-0167/new-upstream
```

The replay bounds virtual memory to 1 GB, CPU to two seconds and wall time to
five seconds. It confirms unfinished-macro refusal, continuing silent call
completion even with recovery false, the fixed template case, and real tabs
with `fmt.indent=tab`. It does not identify which commit fixed allocation.
The rnx implementation stays on 0.14.2. A future Rune upgrade should replay all
0167 controls before removing any workaround.
