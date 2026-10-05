# Rust Lua CLI probe

Piccolo and omniLua both deliver sub-millisecond warm, pinned source-to-answer startup here. Piccolo is slower on numeric/recursive VM work; this does not establish how native Polars/Candle bindings would perform. Lua remains an additional possible project, with rnx unchanged.

## Pinned wall time

Median milliseconds, including process startup and source parsing/compilation. Sustained rows are end-to-end fixed-size workloads, not VM-only clocks; no startup cost is subtracted.

| Subject | Empty script | Print 42 | Numeric loop | Strings/table | fib(27) |
|---|---:|---:|---:|---:|---:|
| lua54 | 0.407 | 0.418 | 6.333 | 4.801 | 9.518 |
| luajit | 0.444 | 0.454 | 8.305 | 3.162 | 1.556 |
| piccolo | 0.675 | 0.687 | 38.457 | 5.171 | 70.512 |
| omnilua | 0.659 | 0.678 | 16.122 | 7.301 | 17.290 |
| rnx-run | 3.734 | 3.784 | 90.430 | 15.382 | 37.556 |
| rnx-eval | 4.084 | 4.123 | 91.090 | 15.757 | 37.907 |
| python | 8.103 | 8.115 | 59.439 | 10.676 | 21.806 |

All 1,785 timed invocations validated exit status, empty stderr and exact expected stdout. Startup/42: 5 warmups, 90 samples each; sustained: 2 warmups, 15 samples each. Three seeded shuffled rounds; raw samples, round medians and distribution summaries retained. This tiny suite does not verify a project’s general speed claim.

## Unpinned source-to-answer control

Separate later 30-sample runs, five warmups; these are not interleaved with the pinned run.

| Subject | Median ms |
|---|---:|
| lua54 | 1.511 |
| luajit | 1.643 |
| piccolo | 2.462 |
| omnilua | 2.473 |
| rnx-run | 11.895 |
| rnx-eval | 12.420 |
| python | 20.967 |

Intel i7-14700 hybrid CPU, Linux; initial comparison pinned to core 4, unpinned controls allow cores 0–27. Governor powersave, intel_pstate; recorded frequency policy does not establish actual execution frequency. Scheduling, migration and changing host load are plausible unmeasured explanations for slower unpinned runs.

## Peak RSS

KiB, one separate /usr/bin/time pass per subject/workload, not a statistical memory bound and not part of the timed clock.

| Subject | Empty | 42 | Numeric | Strings | fib |
|---|---:|---:|---:|---:|---:|
| lua54 | 2176 | 2188 | 2212 | 4660 | 2288 |
| luajit | 2456 | 2556 | 2660 | 4560 | 2548 |
| piccolo | 3976 | 3904 | 3956 | 7304 | 3940 |
| omnilua | 4380 | 4236 | 3992 | 8860 | 3992 |
| rnx-run | 12600 | 12712 | 13180 | 15860 | 12940 |
| rnx-eval | 12272 | 12836 | 12480 | 15572 | 12820 |
| python | 9488 | 9412 | 9452 | 11172 | 9712 |

## Binaries and builds

| Subject | Binary bytes |
|---|---:|
| lua54 | 326728 |
| luajit | 604392 |
| piccolo | 2710648 |
| omnilua | 2790360 |
| rnx-run | 20360568 |
| rnx-eval | 20360568 |
| python | 7477160 |

piccolo release build/install from an empty target: 7.23 s.
omnilua release build/install from an empty target: 6.98 s.

One build each, no precision comparison implied; package downloads/index updates included, OS and existing Cargo caches warm. Piccolo’s own unmodified interpreter example at ce709eb1dae5c543cbc78e7e12bb80249d88c55f; omniLua CLI 0.7.1, packaged lockfile, default features, OMNILUA_VERSION=5.4 explicitly (also its default). Binary/compiler/lock hashes and full build logs retained. No LTO/PGO/allocator tweaks. rnx uses the stock 0167 binary, not the older installed cargo-bin copy.

## Shipped functionality

Presence below means the global table exists, not that every member is implemented. Piccolo’s example initializes Lua::full(), its load_io installs print rather than a standard io table. The measured CLI has no io table, os table, utf8 table or require.

| Subject | string | table | math | io | os | utf8 | coroutine | require |
|---|---|---|---|---|---|---|---|---|
| piccolo | table | table | table | nil | nil | nil | table | nil |
| omnilua | table | table | table | table | table | table | table | function |
| lua54 | table | table | table | table | table | table | table | function |
| luajit | table | table | table | table | table | nil | table | function |

No json/cjson/dkjson module resolved in any measured Lua CLI environment; no module was added. Python and rnx shipped JSON round-trip functionality was checked separately (json-capabilities.json), not used to manufacture a cross-language timing comparison.

Piccolo has an existing file runner and REPL (-r enters REPL after file); no -e eval switch. omniLua, PUC Lua and LuaJIT supply file/REPL/-e; rnx supplies run/eval/session; Python supplies file/-c/REPL. CLI source inspection establishes REPL availability; interactive behavior is not benchmarked.

## Interpretation and limits

Piccolo is a believable candidate for the next small vertical slice: warm startup is close to omniLua and much smaller than rnx/Python here. Its recursive fixture takes about twice rnx’s time; pure VM throughput and library completeness are real tradeoffs. The numeric loop uses modulo each iteration; LuaJIT’s result here is not a general JIT verdict. All runtimes produce the same independently calculated answers, with exact small integers. Rune gathers identical strings then appends delimiters because it lacks Vec.join; Lua uses table.concat and Python str.join. Those API implementations differ, so this is a functionality workload, not a claim of identical allocation strategies.

Piccolo fuel bounds VM work, not long native adapter calls; this probe measures no userdata bridge, cancellation, callbacks, or Polars/Candle operation. A separate-project vertical slice requires the user’s decision.

The lua-rs repository URL redirects to omniLua and the published crate metadata uses the new name; that rename is verified. Full upstream Lua conformance and the project’s published aggregate speed claims remain unverified: no full upstream suite was run here. Selected fixtures passing is not conformance certification.

## Clock and attempts

Native helper reused byte-for-byte from rustc-42: command setup/helper startup outside Instant, spawn, stdout/stderr pipe capture and blocking wait inside; no shell or overhead subtraction. Contemporary hyperfine -N and native preflight on true/cached Rust passed within 0.15 ms; full samples retained in preflight.json. The driver ran under an external 600-second timeout with five-second kill grace.

setup-attempt1 stopped before timing: the library discovery script used _G, which Piccolo lacks. Discovery was changed to explicit globals; all workload validations had already passed. The attempt’s preflight and validations are retained. The deciding attempt completed without any sample removal or configuration tuning.
