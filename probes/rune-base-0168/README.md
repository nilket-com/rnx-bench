# 0168: Rune engine base comparison

Compare released Rune 0.14.2 and the local fork at
bb8e69372353c50e271c9f115bc771c77aa6b83e (unreleased manifest 0.15.0).
No engine modifications, no rnx dependency update. See the rnx record for the
base decision and migration work; results/TABLES.md is generated, not hand-edited.

The two crates share harness.rs, allocator and fixtures. Compatibility wrappers
use std::sync::Arc on 0.14.2 and fallible rune::sync::Arc on main, and normalize
async_complete's VmResult/Result. Main's fmt feature requires anyhow; old requests
std,fmt only. Both have futures, opt-level 3, no LTO, no explicit codegen-unit or
CPU optimization override. Cargo locks retain all package differences. Toolchain
and binary/source hashes are in conditions.json.

On this machine (paths are explicit), build with ./build.sh. It verifies the fork
pin first. Three separate copies are essential: primary has no instrumentation,
counter has only the FIFO handshake, allocation has only atomic allocation
tracking. Do not time the default target after building the allocation feature.

Run from the repository root, writing into a **fresh results directory** (move
existing evidence first; never overwrite a previous failed attempt):

```
probes/rune-base-0168/build.sh
python3 probes/rune-base-0168/controls.py
timeout --kill-after=5s 600s python3 probes/rune-base-0168/counters.py
timeout --kill-after=5s 600s python3 probes/rune-base-0168/measure.py
SSH_AUTH_SOCK=/run/user/1003/openssh_agent python3 probes/rune-base-0168/trajectory.py
python3 probes/rune-base-0168/analyse.py
```

Requires taskset, perf with usable core-PMU permission, hyperfine, Python, GNU
time, stable Rust and the pinned fork at /home/me/work/rune. The timing clock
comes from probes/rustc-42/clock.rs. Reference fixture output is independently
computed by the existing Python lua-rust-0001 fixtures. controls.py has child
memory/CPU/wall bounds and kills its process group on expiry.

Whole-process clock starts before spawn and ends after pipe capture and blocking
wait. Pin is logical P-core 4; perf controller is on core 0. The late unpinned
42 control is labelled and is not pooled with pinned measurements. All 1,410
samples remain. Counter windows bracket work via FIFO enable/disable ACKs;
allocation atomic operations are absent there. RSS is a separate single pass.
Per-invocation output/status is checked by the timing driver; analyse also checks
counter/allocation/RSS output and counts. The in-process call includes native
println; reused mode executes main 20 times on a reused VM, whose call boundary
resets invocation state, with one unused fresh empty VM constructed outside the
call clock per iteration. This is not cross-request isolation evidence.

Default-context measurements include the full stdlib in both versions. The
separate registration breakdown is **public modules only**: 30 old / 31 main,
excluding private hash_map/hash_set/vec_deque modules (33/34 in full contexts).
It cannot price those missing modules or substitute for the full-context table.
Main additionally registers f64::consts. MODULE marks separate construction and
installation; REGDROP is context drop. Allocation mode resets per public-module
mark, so its registration-mode final ALLOC is not the whole registration total.

Setup failures and repairs are retained under setup/: old async return wrapper,
private-module attempt, float expectation and explicit sum generic, an accidental
baseline cargo check in the wrong worktree, and earlier control captures.
controls.py was subsequently pointed explicitly at primary and error-class
checks strengthened; it replays controls only, not deciding timings. The first
editing attempt had an indentation error and ran no child. Raw current control
captures reproduce the deep-input difference. No timed Rust/fixture source was
edited after measurement; analyse verifies those hashes.

machine-survey.json was taken after measurement, not an assertion of instantaneous
frequency during every sample. Build logs are cached incremental harness builds
(~0.7–0.8 s); initial main build was 40.26 s, old initial build failed. They are
not a comparable clean-build performance experiment. The scratch rnx main port
is blocked at compile; its check is not an execution result.
