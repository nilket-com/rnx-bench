# rnx-bench

Measurements of rnx and the Rune engine against other dynamic runtimes: the
harnesses, the exact programs each runtime runs, and the retained results.

All measurements are made on one machine, `nano`: Intel i7-14700, Linux
7.0.0-31. Two methods are used, and their figures are never mixed:

- **Standard suite:** hyperfine whole-process runs (`hyperfine -N`, no shell,
  pinned to one core with `taskset -c 4`). Each figure is a short-lived
  process's elapsed time, startup included.
- **Probes:** probe-specific harnesses, each documented beside its sources.
  Their figures (for example warmed per-invocation slopes) are not
  interchangeable with the standard suite's.

Validity rules:

- Outputs are checked before timing: the JSON suite refuses to benchmark
  unless every program exits 0 and prints exactly one line equal to the
  reference after canonicalisation; probes state their own output checks.
- A result holds for the binaries, versions and session it names. Dated
  results stay dated; nothing is relabelled as current.
- Where a probe pre-registers verdict rules, its verdicts follow them.
  Intervals are reported, a point estimate is never presented as a
  demonstrated difference, and kernels stand alone with no aggregate score.

## Current: Rune native tier versus LuaJIT

One sealed session on 2026-10-12 ([results](probes/rune-native-0184/RESULTS.md)):
Rune's experimental native tier (fork commit 346623b6, feature
`fresh-core-native`, not on by default) against LuaJIT 2.1.1788856981, timed
children pinned to CPU 4. Ratio = Rune native time / LuaJIT time, so below 1 is
faster for Rune; marginal 95% paired-bootstrap intervals; all 400 samples
valid. These are warmed per-invocation slopes from the probe's own harness, not
hyperfine whole-process runs.

| kernel | vs LuaJIT | vs LuaJIT -joff | native vs Rune interpreter |
|---|---|---|---|
| calls (primary) | 1.0190 [0.9644, 1.0282] | 0.0736 [0.0730, 0.0742] | 84.27× faster |
| while | 1.0172 [1.0142, 1.0256] | 0.1568 [0.1556, 0.1579] | 31.31× faster |
| numeric | 0.4457 [0.4453, 0.4462] | 0.2480 [0.2476, 0.2483] | 20.94× faster |

- **Target met:** the calls target (upper bound ≤ 1.25, i.e. at least 80% of
  LuaJIT's speed) was met.
- About 98% of LuaJIT's speed on calls is a **point estimate only**; calls is
  **not shown faster** than LuaJIT.
- **Controls unresolved:** the two controls (fib, shared_rows; native tier on
  versus off) were unresolved against their 1% margin. The checkpoint was
  accepted by explicit exception, **not a statistical pass**.
- LuaJIT does no overflow or fuel checks and uses doubles and host CPU
  features; Rune checks both on i64 with baseline x86-64 code.
- **Experimental:** the native tier is not part of public Rune main or rnx;
  rnx currently depends on released Rune 0.14.2. The exact engine source is
  not yet public, so end-to-end reproduction is pending.

## Dated: cross-runtime startup and JSON (2026-09-13)

[Full tables and conditions](results/cross-runtime-2026-09-13.md). Measured on
2026-09-13 with rnx 3af1ccb on Rune 0.14.2, by hyperfine, on two workloads:
bare startup (evaluate `42` and exit) and 10,000 JSON serialisations in one
process, across the runtimes in [`scripts/`](scripts/). It is an older engine
and a different question from the native-tier probe, and it has not been rerun
since.

## Probe index

Active probes, each with its own method and conditions:

- [rune-native-0184](probes/rune-native-0184/README.md) — the current Rune
  native tier versus LuaJIT result above (archival sources).
- [rune-base-0168](probes/rune-base-0168/README.md) — released Rune 0.14.2
  versus unreleased upstream main (bb8e6937) as an engine base
  ([tables](results/rune-base-0168/TABLES.md)).
- [interp-profile-0170](probes/interp-profile-0170/README.md) — where Rune's
  interpreter spends its instructions.
- [lua-rust-0001](probes/lua-rust-0001/README.md) — Rust-hosted Lua engines
  (Piccolo, omniLua) beside rnx, Lua and Python
  ([summary](results/lua-rust-0001/summary.md)).
- [web-0164](probes/web-0164/README.md) — `rnx serve` HTTP throughput against
  axum and Flask references.
- [context-registration](probes/context-registration/README.md) — the cost of
  building Rune's default-module context.
- [rustc-42](results/rustc-42/summary.md) — standalone rustc build times for
  a tiny program against a 60 Hz frame budget.

The full catalogue, including record-specific gates, is in
[probes/README.md](probes/README.md).

## Reproduction

### Standard benchmarks (runnable)

From the repository root:

```sh
./run_bare.sh        # bare startup: evaluate 42 and exit
./run_json_loop.sh   # 10,000 JSON serialisations, after the output checks
```

Both write hyperfine JSON and Markdown into `results/`, overwriting the dated
exports, and `run_json_loop.sh` also records versions and the output checks.
Prerequisites: hyperfine, a release build of rnx, and each runtime on `PATH`.
The rnx binary and official Node locations are set at the top of the scripts,
and the org.json jar path is in `run_json_loop.sh`'s Kotlin command; edit them
for your machine. The Scala and
Kotlin jars are built first ([scripts/jvm/README.md](scripts/jvm/README.md)).
The programs are in [`scripts/`](scripts/); rnx's JSON program uses the built-in
json module, `json::stringify`, which walks the Rune value with cycle and depth
guards, refuses values JSON cannot represent, and serialises the rest with
serde_json.

### Archival probe sources

Some probes publish their sources for reading and checking but cannot be rerun
from a plain checkout, because they need unpublished or local artefacts. The
native-tier probe is the main case: its engine commit is not public, and its
binaries, raw records and generated inputs are not distributed. See
[probes/rune-native-0184/README.md](probes/rune-native-0184/README.md) for what
blocks a rerun. Other probes state their own prerequisites in their READMEs.

## Next measurement

A genuinely updated cross-runtime comparison needs, in order: the reviewed
native engine landed; rnx wired to that source and feature, and verified to
actually execute admitted regions on the chosen compute workloads; matching
cross-runtime workloads with reference outputs and defined semantics; pinned
versions with one method per comparison; and then the full contemporary
runtime set run and validated on a quiet machine. Startup and JSON are
different questions and may not benefit from the native tier, so changing a
dependency or publishing the probe does not by itself refresh the dated
comparison.
