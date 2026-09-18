# 0065 F5: positional observations and the unchanged launch matrix

The accepted F3/F4 checkpoint remains at rnx 248e29a / bench 175b2a9. This
iteration changes only the bookkeeping representation: a read-order stamp vector,
a byte-keyed directory set with a last-directory fast path, and contiguous child
file ranges. F4's pre-derivation validation schedule and phase clocks are unchanged.
Bookkeeping drops to about 0.25 ms. Five first-adapter comparisons pass; one eval
repeat measures 1.016205 ms against the strict 1 ms bound. That failure and all
samples are retained, with no rerun or post-measurement optimization.

Prerequisites are the retained native-inventory, inventory-workflow and
nested-inventory fixtures described in nested-product/README.md. Frozen real
projects use the same complete 443-file runtime with zero through three adapters.
Nothing in a user's checkout, installation store or scratch project is changed.
Only our isolated fixture's ignored target directory is created and removed.

From rnx-bench, build both configurations serially. Preserve the ordinary binary
before compiling test support; restore it before measure.py freezes the tools:

```sh
mkdir -p probes/nested-position/target results/nested-position-0065
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
cp ../rnx/tools/project/target/release/rnx-project probes/nested-position/target/ordinary
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
cp ../rnx/tools/project/target/release/rnx-project probes/nested-position/target/profiled
cp probes/nested-position/target/ordinary ../rnx/tools/project/target/release/rnx-project
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project-assembly-probe
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/run.py checks
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/run.py replay
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/roster.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/untracked.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/window.py
```

Run the retained `results/nested-position-0065/launch-driver.py` to repeat the real
pre-launch restored-mtime source refusals in default and verify modes. It uses
`target/ordinary`, restores the exact fixture bytes and time in finally, and
asserts the project lock pair and receipt remain unchanged.

Finish all builds/checks before measurement, and run the measurements serially:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/run.py measure
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/run.py fallback
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/profile.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/trace.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/nested-position/collect.py
```

Keep existing results before rerunning. Replay requires target/matrix and
target/extra absent; window.py requires target/window absent; untracked.py requires
target/untracked absent. Measure requires target/baseline, target/format,
target/reuse and samples.jsonl absent. Fallback/profile require their respective
journals absent, and profile also refuses a leftover phases.jsonl. Roster and
fallback refuse an already existing fixture adapter target directory. They never
remove one they did not create. All fixture targets are isolated from previous checkpoints.

run.py archives effective drivers from the accepted nested-product scripts. The
headline matrix, seeds and assertions are unchanged: 4500 samples, 75 cells,
two repeats of 30 with matched direct launch, eval and first prompt. It explicitly
adapts two topology expectations: ignored nested repositories and 14,000 ignored
build files are eligible. Equality and allowances remain exact. Its fallback
measurement retains 360 samples, replacing the former discovery-budget shape with
14,000 ignored files and GIT_PAGER with the commonly exported GIT_EDITOR.

roster.py checks three Git calls and 443 reads at every eligible declaration count,
one shared check for all three children, and the independent GIT_EDITOR counts.
untracked.py proves a non-ignored untracked nested repository refuses on both
roots. window.py records the new F4 observation window: an index addition between
children can be missed until the next invocation. This is a stated schedule change,
not a claim that concurrent edits are observed at identical times.

profile.py retains 480 separate samples. The opt-in test-support clocks partition
one invocation into exclusive phases and assert the intervals sum to its clock.
It measures the profiling overhead against the ordinary tool and does not mix
these samples into the product gate. Median phase totals are not additive medians.
trace.py records statx and successful execs only after timing; it counts Git's
internal child as well as tool-issued Git processes and makes no traced-time claim.

collect.py verifies sample uniqueness/completeness, the headline gate result,
all fixture outcomes and the measured source/binary identities. It archives the
patch from 248e29a; the signed root checkpoint also preserves measured source.
Old measurement checkpoints and old runtime/assembly entries are retained whole.
