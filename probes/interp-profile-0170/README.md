# interp-profile-0170: where Rune's interpreter spends its instructions (rnx record 0170)

Profiling only, Rune 0.14.2 ("old") vs fork main bb8e6937 ("main"). Evidence and conclusions are in rnx `plans/0170_interpreter_profile_evidence.md`.
Every CPU-heavy step runs under the shared lock: `flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock …`. `ledger/lock.log` records each window.

**Steps** (results in `results/interp-profile-0170/step-*`):

| Step | Script | What it does |
|---|---|---|
| A | `counts.py OUT [symbolized\|s2]` | validation, the 0168 baseline gate (FIFO counters), representativeness of a profiling build, whole-process counts |
| B | `sample.py STEP_A_S2 OUT`, then `analyse.py` | retired-instruction and cycle self-sampling at period 1e6, ≥10k samples, LOST/THROTTLE = 0 |
| C | `dwarf.py` | DWARF classification. Insufficient here (unwinding stops after 1–2 frames); retained, not used |
| D | `split.py` | compile-only vs run whole-process instructions on the primary binaries, for the startup/execution split |
| E | `opcount.py` | dynamic opcode counts (diagnostic builds) and on/off corpus semantics |

**Builds:**
- `build.sh`: the frame-pointer build. It failed the 3% gate and is retained as evidence.
- `build-s2.sh`: line tables without frame pointers. It passed.
- `opcount-{old,new}`: the harness with rune's `op-count` diagnostic feature. The patches are in `opcount-patches/`, applied to a copy of the rune-0.14.2 crate and a detached worktree of the fork at bb8e6937. The manifests point at those copies under the author's scratch directory; recreate them from the patches to rebuild.

The perf `.data` files are xz-compressed. Their symbol tables need the S2 binaries, which `build-s2.sh` rebuilds; the self-sample symbol counts are also kept in `step-b/samples.json`.
