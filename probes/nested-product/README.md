# 0065 gate 5: product reuse port, stopped at the floor gate

The product passes the accepted equivalence matrix but fails the required
zero-adapter latency improvement. Do not call this a passing gate or discard the
failing rows. No optimization after the measurement is included here.

Linux; rnx alongside rnx-bench. Prerequisites are the retained native-inventory and
inventory-workflow fixtures, plus gate 4's release recovery-tool copy. The latter's
hash is asserted against saved provenance before using it as format-only control.
All these sources/builds are real, accepted fixture artifacts; no production
receipt or assembly identity is fabricated.

```sh
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project-assembly-probe
python3 probes/nested-product/replay.py
python3 probes/nested-product/checks.py
python3 probes/nested-product/measure.py
python3 probes/nested-product/fallback.py
python3 probes/nested-product/collect.py
```

Keep builds serial and finish them before measurement. Preserve results before
reruns. Replay requires target/matrix and target/extra absent. Measurement requires
target/baseline, target/format and target/reuse absent, and refuses an existing
samples.jsonl. Fallback refuses an existing fallback-samples.jsonl and an existing
native-inventory/target/s/adapters/pgcopy/target directory. It creates 4097 ignored
files there only for its own control and removes that directory in finally; do
not run another consumer of that fixture concurrently. It also asserts the project
lock pair and receipt are unchanged.

The product replay adapts the accepted 36-case and 16-case drivers only to paths
and the existing private test-support assembly-probe entry. Same assertions,
including two inventories in one process and the timed observation-window case.
No copy of the candidate implementation substitutes for product code.

measure.py records 4500 validated samples over 75 cells: three ordinary tools,
zero through three adapters, run/eval/first prompt and direct controls, plus a
separate verify cell per tool; two repeats, 30 samples per cell. It writes the
failed gate result instead of stopping before evidence is saved. fallback.py adds
360 samples showing the 4096-entry discovery budget and inherited GIT_PAGER cost.
Those shapes are sequential blocks, with project/direct interleaved inside each.

The first new product unit test inherited GIT_PAGER and correctly fell back. Its
initial assertion expected reuse, so it was fixed to invoke the exact test in a
Git-override-free child without mutating shared process environment. The original
failure log is retained. Product tests then pass 46 default / 47 test-support,
two ignored each. Counters/hooks are absent from the ordinary release executable.

The zero-adapter floor misses the required 3 ms improvement in every mode/repeat.
The root narrative documents what remains unrun after the stop: full topology and
depth slopes, fresh attachment and installed-adapter journeys, then gate 6.
The frozen source commit and implementation patch preserve this measured port for
review. No cache/runtime deletion is performed.
