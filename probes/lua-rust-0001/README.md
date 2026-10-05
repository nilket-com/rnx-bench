# Lua alongside Rune: CLI experiment

Protocol in PLAN.md; deciding report in ../../results/lua-rust-0001/summary.md.
No adapter or rnx changes. Piccolo example unchanged, omniLua 0.7.1 default release build.

## Reproduce in a fresh scratch checkout

Use a fresh results directory (the scripts refuse overwriting deciding data), or
copy this probe to a scratch rnx-bench tree. The paths below match the recorded run:

```sh
mkdir -p /tmp/lua-rust-0001
git clone https://github.com/kyren/piccolo.git /tmp/lua-rust-0001/piccolo
git -C /tmp/lua-rust-0001/piccolo checkout ce709eb1dae5c543cbc78e7e12bb80249d88c55f
python3 probes/lua-rust-0001/build.py
timeout --kill-after=5s 600s python3 probes/lua-rust-0001/run.py
python3 probes/lua-rust-0001/audit.py
python3 probes/lua-rust-0001/analyse.py
```

Required installed subjects/tools: ~/.local/bin/lua54 and luajit, /usr/bin/python3,
/usr/bin/time, hyperfine, stable rustc/cargo, and the stock rnx binary at
probes/fmt-0167/target/stock (SHA in conditions.json). No global Cargo install is
performed; omniLua installs into the private scratch root. Rust CLIs build
sequentially, in empty independent targets; cached downloads and warm OS pages
are not flushed. Both dependency locks are retained in locks/.

The timing helper is identical to rustc-42/clock.rs. It captures stdout/stderr,
uses a blocking wait and does not count its own startup. Every timed invocation
must produce its independently calculated expected output. Python calculates the
numeric/string/fib oracle before timing; answers are retained in validation.json.

The timed driver as actually run is also retained as measured-driver.py. The final
run.py only adds an early refusal to overwrite a completed run, so rerunning cannot
replace the deciding data. No timed command or workload changed. Audit/analysis
were written after timing; JSON fixture naming initially shadowed Python's json
module, so it was renamed json_roundtrip.py before the untimed capability check
passed. This did not touch a timed fixture or sample.

REPL/eval support is inspected in shipped CLI source/help, not measured
interactively. Library presence means the global table exists, not full module
coverage. A Lua JSON module absent in this environment is reported absent; no
third-party library is added. Python/rnx JSON round trips are untimed capabilities.

## Interpret with care

Empty-script startup includes interpreter initialization and empty-source loading.
Sustained work still includes startup and compilation. LuaJIT may compile traces;
no JIT disabling or extra optimization is applied. The fixtures are deliberately
small, exact integer/ASCII workloads, not representative native analytics work.

All source-to-answer tables compare literal stdout 42, not a returned VM value
with different display costs. rnx run raises its instruction budget before the
script path; rnx eval uses the same body as an expression block (including fib's
local definition). No model loading or adapter work appears in these results.

One unpinned control is retained for each subject, after the primary shuffled
comparison. Changing affinity and chronological load can affect these results;
no scheduler explanation was measured. No full Lua test suite was run, so project
conformance and broad benchmark claims are unverified.
