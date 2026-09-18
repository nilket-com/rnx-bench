# 0065 gate 2: current-format workflows and format-only cost

Run from rnx-bench with rnx beside it. Linux only. No user's scratch project,
installation store, default cache, or kernelspec is used.

Prerequisite: the accepted `native-inventory` fixture at
`probes/native-inventory/target`, including its four built shallow projects,
`env.json`, and `results/native-inventory-0065/setup.json`. It supplies the frozen
7cd3205 tool and the unchanged 443-file/6,988,177-byte runtime, including the full
renamed PostgreSQL adapter. If absent, reproduce the accepted c2af5de probe with
its recorded 7cd3205 source snapshot first. Do not substitute today's checkout.

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project --features test-support
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project --release
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/checks.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/contracts.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/publication.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/setup.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/measure.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/real.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-workflow/collect.py
```

Run measurement only after every build/check has finished. Do not build the two
feature configurations concurrently in one target directory. The setup builds
four new-key assemblies into the accepted fixture's **private** cache, retaining
old and new entries whole. It seeds each exact accepted Cargo lockfile and asserts
byte equality after resolution. It does not claim cold compilation time.

The command matrix generates genuine old shared lock-2/receipt-3 and override
lock-1/receipt-2 documents using the old tool. It then runs current commands,
checking unchanged old files, shell-parsed recovery commands with spaces and
apostrophes, new-key builds, compiler-trapped hits, all launch modes, explicit
override build, stamp/verify, source edits, failures and signals. Its tiny Rust
runtime reports arguments: this isolates tool orchestration, not Rune behavior.
The generated driver and its exact adaptations from the accepted cache-command
matrix are retained in results.

The publication replay copies current production modules byte for byte into an
isolated driver and reruns the accepted 37 cases, including interrupting the
builder and waiter during real compilation. Its audit helper alone changes to
the current BLAKE3 field/algorithm. It uses fixture receipts, so the product
receipt assertions belong to contracts.py. The formatted helper, generated
scripts and imported-file hashes are retained; no old probe is edited.

The real driver uses Polars through current shared and override projects, with
run, eval, PTY frame transforms, a catchable error, retained frame, Parquet
round-trip and reset. Two consumers use different application text and the same
assembly key. Attachment is timed separately with compilation trapped, including
a positive trap control. Every PTY child is quit and reaped.

measure.py records 3,000 samples: 50 cells (two products, four adapter counts,
three modes, project/direct; plus one-native full verify for each product), 30
samples per cell, two fixed-seed interleaved repeats, two excluded warmups.
Terminal is xterm-256color, 120 by 30; one pinned core and one Polars thread.
run/eval clock spawn through exit; session clocks PTY setup/spawn through the
complete first prompt, then quits/reaps outside timing. Every output is checked.
real.py records 120 separate full-hash attachment samples, plus untimed first
attachments. No gate requires the final nested-reuse slope at this checkpoint.

Reruns: preserve the existing journals and results first. setup.py requires
`target/current-0` through `current-3` absent; measure.py refuses an existing
`samples.jsonl`. real.py requires `target/real-traps`, `second-baseline`,
`second-current`, `real-override`, `journey-shared`, `journey-override`, and
`compiler-trap` absent, plus no `attachment-samples.jsonl`. Publication targets
may be reused (sources are refreshed); preserve/remove its old compiler-traces
before a clean replay. Contracts uses temporary directories and cleans them.
Never remove the accepted baseline cache or a live assembly just to rerun.

`graph-drift-preliminary/` preserves the first 3,000 timing samples and setup.
Fresh resolution had selected cc 1.4.7/find-msvc-tools 0.1.13 versus the baseline's
1.4.6/0.1.12. The second-consumer compilation trap exposed that mismatch. Those
samples are not the matched evidence. The corrected run pins exact Cargo bytes;
its artifacts have their own direct controls. Preliminary entries remain in the
private fixture cache; this record does not prune them.
