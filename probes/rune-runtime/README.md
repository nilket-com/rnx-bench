# Standing Rune / rnx / Lua runtime suite (0169)

Run `TMPDIR=/absolute/results-parent probes/rune-runtime/run.sh --out /absolute/results-parent/new-directory`.
The final corruption controls use hard-linked clones; TMPDIR must be on the
results filesystem. Attempt 5b measured and analysed successfully, then its
default /tmp clone placement failed EXDEV; a reviewed read-only replay with
TMPDIR corrected passed. No deciding observations were rerun for that repair.
The output must not exist. Sources are pinned to Rune main bb8e6937 and stock
rnx b240937; the shipping Rune dependency is unchanged. The isolated diagnostic
worktree `/tmp/rune-0169-profile` is constructed by `make_profile.py`, with its
patch and collector retained here. Normal main measurements use the clean fork.

The command checks lifecycle/admission and source refusal controls, builds
primary/counter/allocation subjects, runs semantic and robustness controls, checks
the resident native pipe-capturing clock against Hyperfine -N --output=pipe,
then measures randomized primary invocations. The median agreement gate remains
0.15 ms. Each immutable seeded command plan executes fresh target processes in
one native observer per block; records are buffered until block completion.
Declared and executed sequence hashes are checked, and each sample binds both
its raw record and its plan position. There is no controller journal write
between samples. Historical per-invocation observer diagnostics showed +0.11 to
+0.15 ms offsets, and also failed larger offsets; the resident diagnostic showed
-0.019 to -0.031 ms. Report contemporary offsets; subtract neither. The gate
does not establish precision below its agreement bound. Observer architecture
changed and agreement improved; no particular cause was established.
Each heavy phase holds `/tmp/rnx-runtime-bench.lock`; queue wait is outside its
execution deadline. Commands own process groups with bounded kill/reap cleanup.
The durable ledger records admission, commands, exit status and load averages.

Literal `rnx eval 42` is distinct from print-42 scripts. LuaJIT uses its default
JIT. All actual process output is verified; 3 repeats use 30 fast or 5 compute
samples each, followed by a separately labelled unpinned 42 pass. FIFO-bracketed
PMU counters, allocator observations and maximum RSS do not instrument primary
wall-clock subjects. Stock rnx has its own context/modules, not just Rune defaults.

The diagnostic covers all 34 default factories and eight ordered installation
stages, for stdio enabled and disabled. Its constructor clocks are compared to
unmodified constructors with the same 20-context-per-process lifecycle. A ratio
over 1.20 stops timing attribution. Allocation counters report running process
peak, not an exclusive per-stage peak; parent and child observations must not be
summed. Function-handler counts are registration attempts, not Arc allocations.
Inventory equality plus real collection/trait fixtures guard missing private
modules; a compiled omission feature must fail both coverage and capability.

A baseline shift exceeding max(10% of the old median, old p90-p10) stops attribution
and is retained as a warning. It is a reproduction gate, not an optimization
regression allowance. No optimization or shipping dependency change is made.
