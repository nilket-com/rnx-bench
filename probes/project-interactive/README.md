# 0060: a project prompt and expression

Run from rnx-bench with rnx as a sibling. Python 3, Linux PTYs, Cargo's existing
Polars compilation cache and the accepted 0059 fixture are required. No Python
Polars or Jupyter installation is needed. The project commands run offline.

```sh
cargo build --locked --release --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
cargo build --locked --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
PYTHONDONTWRITEBYTECODE=1 python3 probes/project-interactive/contracts.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/project-interactive/prepare.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/project-interactive/journey.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/project-interactive/measure.py
```

Stage new rnx files before preparation, and do not edit rnx during a measurement:
its entire tracked working tree is a native input. prepare.py creates an ignored
project, seeds only compilation objects from the accepted Polars cost fixture,
and explicitly locks/builds. It declares the real adapter and a mapped source;
its entry writes a marker that session/eval must never create. Nothing relies
on a saved lock being valid on a later checkout. Preserve tracked results before
rerunning. Native build/network setup costs are not launch measurements.

contracts.py uses a tiny Git-tracked API-compatible crate solely to observe exact
argv and receipt orchestration. The debug tool has the existing read counter;
positive controls show full artifact-size reads. The new modes exercise generated
and override stamps, verification, legacy migration, absent/malformed/stale
receipts, touches, changed replacements and restored-time source edits. Modified
executables are refused before execution. The unchanged 0059 inert unit and
workflow fixtures retain the deliberate metadata-miss and refresh-failure tests.
A PATH trap records any unexpected Cargo or rustc invocation.

journey.py uses the ordinary product tool and real generated Polars artifact.
Its PTY has a controlling terminal, TERM=xterm-256color, 120 columns, 30 rows.
It sends actual Ctrl-C and Ctrl-D bytes, not substitute signals. Logs retain raw
terminal bytes and stripped readable copies. A fresh temporary working directory,
explicit absent config and isolated history avoid the user's files. Both launch
paths retain frames through an error, round-trip Parquet, reset and quit. The
fixture also checks exact eval bytes/status, non-Unicode argument refusal,
configuration scope, piped input, unused malformed map preservation, stale mapped
sources and acquisition of the project lock while the prompt remains open.
All processes are waited on; fixture failure kills/reaps the child.

measure.py uses ordinary releases, one CPU and one Polars thread, identical
terminal/config/splash settings, two interleaved repeats of twenty samples per
mode/product (240 observations). Fixed-seed order, warm caches, every output and
status checked, no sample dropped. Eval times spawn/capture/wait; session times
PTY setup and spawn through the complete first prompt. Quit/reap are outside
readiness timing but always checked. Full verification is its own column, not
mixed into everyday samples. The 25 ms difference is a host-specific gate.

The original sixteen workflow groups and seven 0059 contract groups were also
rerun. Their existing tracked results were restored afterwards. Logs here record
those reruns. Windows is type-checked only and project commands still refuse.
