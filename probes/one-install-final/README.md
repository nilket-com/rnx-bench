# 0067 gate 5: one-install costs and regression

The product under measurement is rnx `1b894e0` (Gate 4, whose product is unchanged
from `7ae8863`). The stock baseline is `94f5f3f`. New product edits in this gate
are documentation only. Every fixture uses private build/project/cache storage;
accepted result directories are not overwritten.

From rnx-bench, with the whole `probes/one-install-final/target` and
`results/one-install-final-0067` absent:

```sh
mkdir -p probes/one-install-final/target results/one-install-final-0067
python3 probes/one-install-final/build.py
python3 probes/one-install-final/stock.py
python3 probes/one-install-final/roster.py
python3 probes/one-install-final/regression.py
python3 probes/one-install-final/lints.py
python3 probes/one-install-final/native-checks.py
python3 probes/one-install-final/smoke.py
python3 probes/one-install-final/profile-build.py
python3 probes/one-install-final/fetch.py
python3 probes/one-install-final/features.py
python3 probes/one-install-final/cold.py
python3 probes/one-install-final/measure.py
python3 probes/one-install-final/profile.py
python3 probes/one-install-final/verify-profile.py
python3 probes/one-install-final/trace.py
python3 probes/one-install-final/storage.py
```

Build/check steps may overlap except that `build.py`, root regression and the
final packaged-manifest check use the root Cargo target and must run serially.
Run **all timing steps with no other builds or fixtures running**. `cold.py` uses
normal compilation parallelism, a fresh assembly cache and cached source inputs;
it also runs alone. `stock.py`, `measure.py` and `profile.py` pin themselves to one
available CPU with one Polars thread. Python spawn/capture/wait overhead is part
of the reported process clock. First prompt includes PTY creation; persistent
cell measurements exclude startup. Journals refuse overwrite.

The normal replay above includes the corrected roster. The recorded initial
fixture renamed the third crate but missed its help namespace; registration
correctly refused before any timing. `roster-initial/`, its Git bundle and the
fixture-corrections document retain that attempt. The successful fixture copies
the **whole tracked PostgreSQL adapter** and changes its package/help namespace,
not its size into a tiny stub. All zero-to-three Git and path projects use this
same frozen source snapshot. Its bundle is archived against `1b894e0`.

Two other fixture corrections were the adapter notices script filename and
the distinct success messages for Git versus legacy-path attachment. The latter
was caught in warm-up before a headline journal existed.
`regression.py --resume` continues only incomplete checks; its original refusal
is retained. A fresh replay needs no resume. Root strict clippy has existing
findings, compared against a real baseline clippy invocation rather than treated
as passing. Native all-target clippy diagnostics in unchanged baseline sources
are retained too. Tool strict clippy must pass in both configurations.

`stock.py` retains 2,400 samples, with 100 per process cell/repeat and 200 per
persistent-cell/repeat. Each output/status is verified. A reproducible median
slowdown above 5% stops the gate. `measure.py` retains 3,360 samples: 48 headline
cells plus eight full-command cost cells, two repeats of 30 each, randomized and
interleaved. It compares project minus direct for Git/path separately, and reports
all six path first-adapter increments without reopening 0065's qualification.

`profile-build.py` preserves an isolated instrumentation patch and builds both
an unchanged standalone manager and its profiled counterpart. `profile.py`
compares those with stock and records 720 separate samples. Its four disjoint
intervals cover lock decoding/pair validation, input/context checks, receipt/ready
and artifact validation, and command construction. They begin at `git_launch`;
CLI dispatch, project opening and envelope detection are outside the intervals.
This profiler never replaces the ordinary binaries in the headline matrix.

`trace.py` stops on native source opens, Git/Cargo/rustc execs or network access
in ordinary Git eval, at every roster size. Attachments use compiler traps with
positive controls. `fetch.py` needs the retained published combined assembly from
Gate 4 (`probes/one-install`); it fetches that exact Cargo manifest/lock in two
fresh Cargo Git homes. Registry cache sources are shared. The untraced fetch time
and traced transport byte count are separate observations; TCP bytes include
protocol overhead. `storage.py` counts unique device/inode pairs per owner and
does not follow the registry symlink.

The smoke driver builds the external extension fixture in a new workspace,
checks its public assembly/failure/reset/worker contracts and absence of management
symbols, then runs the ordinary HTTP/PostgreSQL server against a private cluster.
The Gate 4 notebook/interactive journeys are retained at their accepted commit;
this gate does not overwrite or restate them as new runs.

Prerequisites: Rust/Cargo/Git, strace, nm, PostgreSQL 18 tools, the accepted Gate 4
fixture, and a populated registry cache. Remove a prior baseline worktree before moving/removing its containing target.
Old baseline worktrees are removed with
`git worktree remove` after source/binary identities are saved. No user runtime
store or assembly entry is deleted.

`verify-profile.py` records ten separately labelled diagnostic observations of
one-native Git full verification; they are not mixed into the headline samples.
`collect.py` validates sample uniqueness/counts, gates, traces and regression
results. The baseline worktree is removed after these checks; frozen binaries
and source identities remain.
