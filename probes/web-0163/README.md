# 0163: reusable invocation slots

A measurement prototype, not the product server. B is 0162's host with a fresh
context per request; B-prime (`web0163-b`, called `S` in the driver) builds four
slots on each worker and returns each slot after its invocation closes. Both
compile the same Rune program, use two workers, an active limit of four and a
queue of sixteen per worker. The slot host converts the result to owned bytes
before close. A retired slot fails the prototype worker loudly; replacement and
production shutdown are for the product-host record.

Build from these repositories with the implementation applied:

```sh
CARGO_INCREMENTAL=0 cargo build --offline --locked --release --manifest-path probes/web-0162/b/Cargo.toml
CARGO_INCREMENTAL=0 cargo build --offline --locked --release --manifest-path probes/web-0163/b/Cargo.toml
python3 probes/web-0163/phases.py --control
python3 probes/web-0163/phases.py --baseline --out /tmp/b-phases.jsonl
python3 probes/web-0163/phases.py --out /tmp/slot-phases.jsonl
taskset -c 2 probes/web-0163/b/target/release/context
python3 probes/web-0163/run.py /tmp/0163-fresh-output
```

The load driver requires `oha`, `taskset`, and the same CPUs as 0162: server
CPUs 2,4; load CPUs 8,10,12,14. It checks all 26 wire fixtures and three requests
on one HTTP connection before measuring. Three interleaved repetitions use
concurrency 1 and 32 on `/` and `/hello/world`, with three seconds of warm-up
and ten seconds measured. It reuses 0162's fail-closed load validator: only 200
responses, no errors, finite positive throughput and latency, and measured
established connections equal to concurrency. Full oha JSON is retained for
both warm-up and measured runs. RSS is sampled by the original driver on the
first repetition of each condition; readiness is a single process observation,
not a startup distribution. `slot_startup` events report each worker's cost to
build its four slots. Instrumented phases run separately with one worker and
retain all 660 records and their validated summaries.

The decomposition runs 20 warm-ups and 300 samples on CPU 2. Every figure is a
median of **construction plus disposal**: Rune defaults, runtime from an
already-built context, old prepare/close, and slot build/drop. It does not
subtract these overlapping totals or claim the registration cost itself fell.

Saved results are in `results/web-0163`. A and Flask from 0162 are historical
context only; this record measures only matched B and B-prime. No axum or Flask
performance claim follows from it.
