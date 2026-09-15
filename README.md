# rnx-bench

Reproducible startup and JSON-loop measurements for rnx against other dynamic
runtimes, made on `nano` (Intel i7-14700, Linux 7.0.0-31) on 2026-09-13.
Everything here was measured on this machine by Claude; nothing is carried
over from the earlier Gemini chat, whose numbers came from a different box
(i9-12900K) and were never independently verified.

## Layout

- `scripts/` — the exact programs each runtime ran. Every JSON script builds
  `{a: [x, 2, 3], b: "hello"}` 10,000 times, serialises it each time, and
  prints the last string.
- `run_json_loop.sh` — runs every program once and requires exit status 0,
  exactly one line on stdout, and that line equal to the reference after
  canonicalisation (sorted keys). Records versions, then runs hyperfine.
  Refuses to benchmark if any check fails.
- `run_bare.sh` — evaluate the literal `42` and exit.
- `results/` — hyperfine JSON and markdown exports, `versions.txt`, and
  `json_outputs.txt`.

## Conditions

Rust 1.98.1 (the default toolchain on nano; rnx's manifest records 1.95 as its
tested toolchain). `hyperfine -N` (no shell), `taskset -c 4` (one core; this cut σ from ~2.5 ms
to ~0.1 ms), 3–5 warmups, 30–50 runs. rnx is `cargo build --release --locked`
at commit 3af1ccb (record 0030 applied: `version` and `help` no longer build
a Rune context), Rune 0.14.2. Node appears twice: the Ubuntu package is
built with `node_use_node_snapshot=false` and is ~5× slower to start than the
official binary; both are reported. Scala and Kotlin are
precompiled to JVM bytecode jars (`scripts/jvm/`, scala-cli assembly with
upickle; kotlinc with org.json) and run with the system OpenJDK 25, so their
numbers exclude source compilation but include JVM startup and whatever JIT
compilation the JVM does during the run. Perl appears with
both its pure-Perl `JSON::PP` and the C `JSON::XS`. R runs through `Rscript`
with jsonlite installed into `~/R/library`; Ruby is the distro 3.3.8.

## Bare startup (`42`)

| runtime | mean |
|---|---|
| /bin/true | 0.25 ms |
| Lua 5.4.7 | 0.37 ms |
| LuaJIT 2.1 | 0.40 ms |
| rnx version (after 0030) | 0.49 ms |
| Perl 5.40 | 0.74 ms |
| Bun 1.4.2 | 1.8 ms |
| rnx run | 3.5 ms |
| rnx eval | 3.9–4.3 ms (drifted between runs) |
| Python 3.14.4 | 8.1 ms |
| Node 22.22.1 official | 11.6 ms |
| Deno 2.9.6 | 11.9 ms |
| Kotlin 2.4.20 jar, OpenJDK 25 | 32.4 ms |
| Ruby 3.3.8 | 34.5 ms |
| Node 22.22.1 distro | 58.9 ms |
| R 4.5.2 (Rscript) | 90.8 ms |
| Julia 1.13.0 | 107 ms |
| Scala 3.9.0 jar, OpenJDK 25 | 116 ms |

## 10,000 JSON serialisations

Elapsed time for a short-lived process, so startup is included. rnx and Deno
are within a few percent and should not be ranked against each other on this.

| runtime | mean |
|---|---|
| Bun | 3.5 ms |
| Perl + JSON::XS | 8.3 ms |
| LuaJIT + cjson | 8.4 ms |
| Lua 5.4 + cjson | 9.4 ms |
| rnx (`host::json_stringify`) | 11.4 ms |
| Deno | 12.0 ms |
| Node official | 17.2 ms |
| LuaJIT + json.lua | 18.1 ms |
| Python `json.dumps` | 30.7 ms |
| Lua 5.4 + json.lua | 40.4 ms |
| Ruby `JSON.generate` | 46.8 ms |
| Perl + JSON::PP | 68.6 ms |
| Node distro | 68.8 ms |
| Kotlin jar + org.json | 105 ms |
| Scala jar + upickle | 256 ms |
| Julia + JSON.jl | 458 ms |
| R + jsonlite | 970 ms |

Observed key order in the raw outputs: rnx, Perl (both), Lua 5.4 + json.lua, and both
LuaJIT variants printed `{"b":..,"a":..}`; the others printed `{"a":..,"b":..}`.
Three further rnx probes: `#{a,b,c,d}` → `b,a,c,d`; `#{d,c,b,a}` → `b,a,c,d`;
`#{zeta,alpha,mid}` → `mid,alpha,zeta`. So rnx's order does not depend on
insertion order. No ordering contract is inferred from this; it is consistent
with hash-table iteration but that has not been checked against Rune's
`Object` implementation.

## Everything against rnx

Generated from `results/bare.json` and `results/json_loop.json`; the bare
baseline is `rnx eval 42`. "Faster"/"slower" are ratios of means. The encoder
column shows that the choice of encoder matters a great deal; it does not
isolate implementation language as the cause, since algorithm, allocation,
API behaviour, and startup all differ between rows.

| runtime | bare `42` | vs rnx | 10k JSON | vs rnx | JSON encoder |
|---|---|---|---|---|---|
| Bun 1.4.2 | 1.8 ms | 2.5× faster | 3.5 ms | 3.3× faster | built-in (C++) |
| Perl 5.40 | 0.74 ms | 5.8× faster | 8.3 ms | 1.4× faster | JSON::XS (C) |
| LuaJIT 2.1 | 0.41 ms | 10.6× faster | 8.4 ms | 1.4× faster | cjson (C) |
| Lua 5.4.7 | 0.38 ms | 11.3× faster | 9.4 ms | 1.2× faster | cjson (C) |
| rnx (Rune 0.14.2) | 4.3 ms | baseline | 11.4 ms | baseline | host::json_stringify (Rust) |
| Deno 2.9.6 | 11.9 ms | 2.7× slower | 12.0 ms | 1.0× slower | built-in (C++) |
| Node 22.22.1 official | 11.6 ms | 2.7× slower | 17.2 ms | 1.5× slower | built-in (C++) |
| Python 3.14.4 | 8.1 ms | 1.9× slower | 30.1 ms | 2.6× slower | json (C) |
| Ruby 3.3.8 | 34.5 ms | 8.0× slower | 46.8 ms | 4.1× slower | json (C) |
| Node 22.22.1 distro | 58.9 ms | 13.6× slower | 68.8 ms | 6.0× slower | built-in (C++) |
| Kotlin 2.4.20 jar | 32.4 ms | 7.5× slower | 105.1 ms | 9.2× slower | org.json (JVM) |
| Scala 3.9.0 jar | 116.1 ms | 26.8× slower | 255.9 ms | 22.4× slower | upickle (JVM) |
| Julia 1.13.0 | 106.5 ms | 24.6× slower | 458.0 ms | 40.1× slower | JSON.jl |
| R 4.5.2 | 90.8 ms | 21.0× slower | 969.7 ms | 85.0× slower | jsonlite (C/R) |

Encoders written in the scripting language itself, for comparison: Lua 5.4 + json.lua 40.4 ms (3.5× slower), LuaJIT + json.lua 17.9 ms (1.6× slower), Perl + JSON::PP 68.6 ms (6.0× slower).
rnx after record 0030: `rnx version` 0.50 ms, `rnx run` 3.5 ms; `rnx eval` is the bare baseline above.

## Where rnx's startup goes

A scratch crate against the same Rune 0.14.2 was built as one binary with a
mode argument, so each phase is a process-level delta under the same
hyperfine conditions (100 runs, pinned):

| mode | mean | delta |
|---|---|---|
| exit immediately | 0.56 ms | process floor |
| + `Context::with_default_modules()` | 3.7 ms | +3.1 ms |
| + `context.runtime()` | 3.7 ms | ~0 |
| + compile `pub fn main() { 42 }` | 3.7 ms | ~0 |
| + run it | 3.7 ms | ~0 |
| rnx version | 4.2 ms | +0.5 ms over the crate: host/text install, larger binary |
| rnx eval 42 | 4.6 ms | |

(Those absolute numbers are from an earlier run than the table above; the
machine drifted ~0.5 ms between runs. The deltas are the point.)

An in-process `Instant` measurement of the same phases read 7–9 ms for the
context, higher than the 3.1 ms process-level delta. The cause is
unresolved: the two runs were not pinned the same way and were minutes
apart, and no evidence was gathered about page faults or allocator
behaviour. The process-level deltas are the ones used here because they
were taken under the same conditions as every other number in this file.

Conclusion: ~75% of `rnx eval 42` is building Rune's default-module context.
Compile and execution of a trivial program are below the noise floor.

## Lazy context (record 0030, committed)

`src/main.rs` built the context before dispatching any command. Record 0030
(plan 001d5b1, impl 3af1ccb) answers `version` and `help` first. The
throwaway measurement that motivated it, before the record existed:

| | current | lazy |
|---|---|---|
| rnx version | 4.2 ms | 0.59 ms |
| rnx eval 42 | 4.6 ms | 4.7 ms |

Under the record, measured before/after: `version` 3.6 → 0.49 ms, `help`
3.6 → 0.50 ms, `eval 42` unchanged; see the evidence file beside the record
in the rnx repository. `eval`/`run` need something else: fewer default modules, cheaper registration, or precomputed metadata —
none measured yet.

## Rebuilding the JVM jars

The jars are not committed. From `scripts/jvm/`:

```sh
scala-cli --power package bare.scala --assembly -o bare-scala.jar -f
scala-cli --power package json.scala --assembly -o json-scala.jar -f
kotlinc bare.kt -include-runtime -d bare-kotlin.jar
kotlinc json.kt -cp ~/opt/json.jar -include-runtime -d json-kotlin.jar
```

## Namespace migration (record 0049)

Current `scripts/json.rn` uses `json::stringify`. Saved tables, notebooks,
source snapshots and raw exports retain the API and binary measured at
their original commits; their `host::` spellings are historical evidence.
`probes/process/measure.py` retains a dedicated `json-0044.rn` workload
for its old revisions. `probes/jupyter-notebook/startup.py` intentionally
requires the old 0047 worker hash. Neither is a current-head comparison.
The new `probes/namespaces` comparison records separate before/after sources
and requires equal successful outputs before timing them.
