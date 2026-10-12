# Cross-runtime startup and JSON, 2026-09-13

A dated measurement. It is not refreshed and does not describe the current rnx
or Rune engine; in particular it predates, and says nothing about, the
experimental native tier.

- **Date:** 2026-09-13, on `nano` (Intel i7-14700, Linux 7.0.0-31).
- **Engine:** rnx 3af1ccb on Rune 0.14.2, `cargo build --release --locked`,
  Rust 1.98.1.
- **Workloads:** bare startup (evaluate the literal `42` and exit), and 10,000
  JSON serialisations of `{a: [x, 2, 3], b: "hello"}` printing the last string.
- **Method:** hyperfine 1.20.0, `-N` (no shell), pinned with `taskset -c 4`;
  bare 5 warmups and 50 runs, JSON 3 warmups and 30 runs. Whole-process
  elapsed time, so the JSON figures include startup.
- **Sources:** [`bare.json`](bare.json), [`bare.md`](bare.md),
  [`json_loop.json`](json_loop.json), [`json_loop.md`](json_loop.md),
  [`versions.txt`](versions.txt), [`json_outputs.txt`](json_outputs.txt).
  These working-tree exports are overwritten by any rerun of `run_bare.sh` or
  `run_json_loop.sh`. The immutable 2026-09-13 records are the ones in commit
  `ef410412ae7077ebe4bab35c3231a4152e68d6a0`, for example
  `git show ef410412ae7077ebe4bab35c3231a4152e68d6a0:results/bare.json`.

The measurements used the scripts and API at rnx 3af1ccb; the current
`scripts/json.rn` uses `json::stringify`. At that commit rnx's encoder was its
built-in Rust walk serialised with serde_json.

## Summary against rnx

The bare baseline is `rnx eval 42`. "Faster"/"slower" are ratios of means.
The encoder column shows that encoder choice matters a great deal; it does not
isolate implementation language as the cause, since algorithm, allocation, API
behaviour and startup all differ between rows. rnx and Deno are within a few
percent on JSON and should not be ranked against each other on this.

| runtime | bare `42` | vs rnx | 10k JSON | vs rnx | JSON encoder |
|---|---|---|---|---|---|
| Bun 1.4.2 | 1.8 ms | 2.5× faster | 3.5 ms | 3.3× faster | built-in (C++) |
| Perl 5.40 | 0.74 ms | 5.8× faster | 8.3 ms | 1.4× faster | JSON::XS (C) |
| LuaJIT 2.1 | 0.41 ms | 10.6× faster | 8.4 ms | 1.4× faster | cjson (C) |
| Lua 5.4.7 | 0.38 ms | 11.3× faster | 9.4 ms | 1.2× faster | cjson (C) |
| rnx (Rune 0.14.2) | 4.3 ms | baseline | 11.4 ms | baseline | built-in (Rust, serde_json) |
| Deno 2.9.6 | 11.9 ms | 2.7× slower | 12.0 ms | 1.0× slower | built-in (C++) |
| Node 22.22.1 official | 11.6 ms | 2.7× slower | 17.2 ms | 1.5× slower | built-in (C++) |
| Python 3.14.4 | 8.1 ms | 1.9× slower | 30.1 ms | 2.6× slower | json (C) |
| Ruby 3.3.8 | 34.5 ms | 8.0× slower | 46.8 ms | 4.1× slower | json (C) |
| Node 22.22.1 distro | 58.9 ms | 13.6× slower | 68.8 ms | 6.0× slower | built-in (C++) |
| Kotlin 2.4.20 jar | 32.4 ms | 7.5× slower | 105.1 ms | 9.2× slower | org.json (JVM) |
| Scala 3.9.0 jar | 116.1 ms | 26.8× slower | 255.9 ms | 22.4× slower | upickle (JVM) |
| Julia 1.13.0 | 106.5 ms | 24.6× slower | 458.0 ms | 40.1× slower | JSON.jl |
| R 4.5.2 | 90.8 ms | 21.0× slower | 969.7 ms | 85.0× slower | jsonlite (C/R) |

Encoders written in the scripting language itself, for comparison: Lua 5.4 +
json.lua 40.4 ms (3.5× slower), LuaJIT + json.lua 17.9 ms (1.6× slower), Perl +
JSON::PP 68.6 ms (6.0× slower). Other rnx commands in the same bare run:
`rnx version` 0.50 ms, `rnx run` 3.5 ms.

## Full hyperfine exports

Bare startup (`bare.md`, µs):

| Command | Mean [µs] | Min [µs] | Max [µs] | Relative |
|:---|---:|---:|---:|---:|
| `true` | 271.4 ± 17.5 | 253.6 | 372.2 | 1.00 |
| `rnx eval` | 4329.3 ± 886.1 | 3847.2 | 6322.7 | 15.95 ± 3.42 |
| `rnx run` | 3544.0 ± 14.7 | 3517.0 | 3582.0 | 13.06 ± 0.85 |
| `rnx version` | 504.3 ± 12.8 | 490.1 | 548.4 | 1.86 ± 0.13 |
| `python3` | 8084.9 ± 38.3 | 8024.5 | 8273.7 | 29.79 ± 1.93 |
| `perl` | 740.1 ± 22.1 | 711.1 | 847.3 | 2.73 ± 0.19 |
| `ruby` | 34483.9 ± 288.1 | 34165.2 | 35740.6 | 127.08 ± 8.27 |
| `Rscript` | 90765.2 ± 741.2 | 89935.1 | 94303.2 | 334.48 ± 21.77 |
| `bun` | 1758.3 ± 25.0 | 1725.1 | 1820.4 | 6.48 ± 0.43 |
| `node_official` | 11586.8 ± 315.7 | 10987.5 | 12350.1 | 42.70 ± 2.99 |
| `node_distro` | 58931.4 ± 453.1 | 58067.1 | 60037.9 | 217.17 ± 14.12 |
| `deno` | 11874.1 ± 568.0 | 10558.7 | 12683.4 | 43.76 ± 3.52 |
| `lua54` | 383.9 ± 13.3 | 370.0 | 450.5 | 1.41 ± 0.10 |
| `luajit` | 409.5 ± 18.9 | 394.9 | 489.9 | 1.51 ± 0.12 |
| `scala_jar` | 116066.1 ± 1625.7 | 112522.7 | 118742.7 | 427.71 ± 28.26 |
| `kotlin_jar` | 32399.5 ± 879.6 | 30918.3 | 35449.4 | 119.40 ± 8.36 |
| `julia` | 106521.4 ± 3878.3 | 98644.4 | 131906.0 | 392.54 ± 29.10 |

The `rnx eval` row has a wide spread (± 886.1 µs); treat its mean as approximate.

10,000 JSON serialisations (`json_loop.md`, ms):

| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `rnx` | 11.4 ± 0.1 | 11.3 | 12.0 | 3.27 ± 0.18 |
| `python3` | 30.1 ± 0.5 | 29.6 | 31.3 | 8.62 ± 0.49 |
| `perl_pp` | 68.6 ± 3.1 | 67.0 | 81.9 | 19.63 ± 1.39 |
| `perl_xs` | 8.3 ± 0.1 | 8.2 | 8.5 | 2.38 ± 0.13 |
| `ruby` | 46.8 ± 0.4 | 46.4 | 48.2 | 13.41 ± 0.73 |
| `bun` | 3.5 ± 0.2 | 3.2 | 3.8 | 1.00 |
| `node_official` | 17.2 ± 0.3 | 16.6 | 18.3 | 4.92 ± 0.28 |
| `node_distro` | 68.8 ± 0.4 | 68.1 | 69.9 | 19.69 ± 1.07 |
| `deno` | 12.0 ± 0.5 | 11.0 | 13.3 | 3.43 ± 0.23 |
| `lua54_cjson` | 9.4 ± 0.1 | 9.3 | 10.0 | 2.69 ± 0.15 |
| `lua54_pure` | 40.4 ± 0.9 | 39.7 | 44.7 | 11.57 ± 0.67 |
| `luajit_cjson` | 8.4 ± 0.2 | 8.2 | 8.6 | 2.41 ± 0.14 |
| `luajit_pure` | 17.9 ± 0.7 | 17.1 | 18.8 | 5.13 ± 0.34 |
| `scala_jar` | 255.9 ± 4.4 | 244.9 | 262.6 | 73.29 ± 4.16 |
| `kotlin_jar` | 105.1 ± 1.6 | 102.0 | 108.4 | 30.11 ± 1.69 |
| `rscript` | 969.7 ± 6.0 | 959.9 | 992.7 | 277.69 ± 15.10 |
| `julia` | 458.0 ± 8.9 | 454.3 | 504.7 | 131.17 ± 7.53 |

## Conditions

- Rust 1.98.1 was the default toolchain on nano; rnx's manifest records 1.95
  as its tested toolchain. Pinning to one core cut σ from ~2.5 ms to ~0.1 ms.
- Node appears twice: the Ubuntu package is built with
  `node_use_node_snapshot=false` and is ~5× slower to start than the official
  binary; both are reported.
- Scala and Kotlin are precompiled to JVM bytecode jars (scala-cli assembly
  with upickle; kotlinc with org.json; see
  [`scripts/jvm/README.md`](../scripts/jvm/README.md)) and run on the system
  OpenJDK 25.
- Perl appears with both its pure-Perl `JSON::PP` and the C `JSON::XS`. R runs
  through `Rscript` with jsonlite; Ruby is the distro 3.3.8.
- Exact versions are in [`versions.txt`](versions.txt).

## Output checks and key order

`run_json_loop.sh` refuses to benchmark unless every program exits 0, prints
exactly one line, and that line equals `{"a":[9999,2,3],"b":"hello"}` after
canonicalisation with sorted keys ([`json_outputs.txt`](json_outputs.txt)).

Observed key order in the raw outputs: rnx, Perl (both), Lua 5.4 + json.lua and
both LuaJIT variants printed `{"b":..,"a":..}`; the others printed
`{"a":..,"b":..}`. Three further rnx probes: `#{a,b,c,d}` → `b,a,c,d`;
`#{d,c,b,a}` → `b,a,c,d`; `#{zeta,alpha,mid}` → `mid,alpha,zeta`. So rnx's
order did not depend on insertion order. No ordering contract is inferred from
this; it is consistent with hash-table iteration, but that was not checked
against Rune's `Object` implementation.
