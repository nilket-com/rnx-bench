# Rust Lua CLI probe

Lua is an additional experiment alongside rnx. No rnx changes or native bindings.

Subjects: Piccolo's unmodified interpreter example at ce709eb1dae5c543cbc78e7e12bb80249d88c55f, omniLua's shipped CLI (exact crate version and source locked before timing), installed PUC Lua 5.4 and LuaJIT, stock rnx run/eval and Python. Build Rust CLIs in separate empty targets with locked dependencies, release defaults, elapsed build wall time (warm dependency/download caches disclosed). Record binaries, source/toolchain hashes and sizes.

Three workloads: startup via an empty script (source-file startup, not pure process loader cost); source-to-answer printing 42; sustained script execution via 1,000,000 integer additions modulo 1,000,003 and a 20,000-item string/table workload. All final outputs validated against independent Python calculations; no timing of failing subjects. Startup/42 use 5 warmups, 3 shuffled rounds of 30 samples each; sustained workloads use 2 warmups, 3 shuffled rounds of 5 samples each. Numeric input is small enough to remain exact even in float-only Lua. Strings are ASCII. Same algorithm and observable output, with language-idiomatic containers. rnx eval and run are separate rows.

Clock: reuse rustc-42 native spawn/pipe capture/blocking-wait helper, no overhead subtraction; external whole-driver timeout. Before timing, contemporaneous hyperfine -N on /bin/true and cached Rust (50 runs/5 warmups), then native 50 runs/5 warmups, medians must agree within 0.15 ms or STOP. Pin core 4; report hybrid CPU policy, and a separate unpinned 42 row for each runtime (30 samples, 5 warmups), never credited to initial interleaved comparison. Retain all attempts.

Stdlib probes enumerate string/table/math/io/os/utf8/coroutine and shipped JSON modules. Missing JSON is a gap, not an invented extension or silent omission. Verify CLI script/REPL/eval capabilities from source and controls. Project conformance/speed claims remain unverified unless their own full suite is actually executed; the small probe cannot certify conformance or general speed.

Decision is descriptive: measured costs, working capabilities and limitations inform the user's separate-project decision. No arbitrary fastest-wins gate. Claude reviews this protocol before deciding measurements, and reviews local probe commit before push.

Accepted additions: recursive fib(27), peak RSS in a separate /usr/bin/time pass, and OMNILUA_VERSION=5.4 explicitly (0.7.1 defaults to 5.4). Pure-script recursion measures VM calls, not the future native/userdata bridge. Rune has no Vec.join; its string fixture gathers identical items then appends them with separators, rather than table.concat. This is an API/algorithm implementation difference disclosed beside the measurements.
