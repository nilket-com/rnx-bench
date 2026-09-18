# 0064 gate 6: regression and closing evidence

Run from rnx-bench with rnx alongside it, registry sources cached, private PostgreSQL
cluster tools available and the frozen legacy tool from `cache-commands/build.py`.
Stage product source changes before starting and keep those bytes fixed until every
fixture finishes. Root and tool feature configurations run serially, not concurrently.
No speed measurement is performed here; gate 5 owns the timing evidence.

```sh
python3 probes/runtime-final/checks.py
python3 probes/runtime-final/scope.py
python3 probes/runtime-final/replay.py contracts
python3 probes/runtime-final/replay.py journey
python3 probes/runtime-final/replay.py cache
python3 probes/runtime-final/collect.py
```

For a complete rerun, `probes/runtime-final/target/` and
`results/runtime-final-0064/` must be absent. Save any prior attempt before removing
fixture-owned directories. The drivers refuse occupied journey targets. Cross checks
need the Windows GNU and MSVC Rust targets; `CC_x86_64_pc_windows_gnu` and
`AR_x86_64_pc_windows_gnu` override the recorded unpacked MinGW tool paths.
Windows is type-checked, not executed. The non-Unix installation/transition branches
explicitly refuse; root session source is unchanged from the accepted 0063 baseline.

`checks.py` runs three root suites serially, notices, release selfcheck, both
tool suites and strict all-target clippy, and Windows checks. `scope.py` compares the
normalized default graph and protected sources with `1ecc35c`, checks public docs,
and runs the two opt-in real tool integrations. It then leaves the root feature
binary for `replay.py` to rebuild explicitly before use.

`contracts` reruns preparation, startup and commitment against real product binaries.
Tiny facade adapters are the accepted fault injectors; commitment includes real HTTP
and PostgreSQL owners. Only the historical missing-runtime expectation changes to
0064's installation command, and setup isolates XDG_DATA_HOME. It also replays
installation discovery/old-scratch reopening, the 90-case publication matrix, and
repair with both ordinary and test-support binaries. The repair replay adds assertions
for the corrupt-runtime diagnostic and missing Git, including unchanged entry state.

`journey` rebuilds one exact snapshot for the stock launcher, tool and installation,
then physically renames the original fixture checkout before a cold installed build.
The four accepted Polars/PostgreSQL journeys, second-consumer compilation traps and
reopen checks run unchanged apart from fixture/output locations and source baseline.

`cache` replays command migration, artifact stamps and full verification, interactive
contracts, Polars override PTY, publication failures, local legacy workflow and real
mapped PostgreSQL workflow. Only legacy lock creation uses the frozen pre-cache tool;
current code builds and launches. The Polars override uses this gate's built artifact.
Existing nested drivers retain their established ignored target locations; their
published results are redirected, and effective scripts are saved for audit.

All new results live in `results/runtime-final-0064/`. Original fixture sources and
accepted results stay untouched. Effective replay sources are archived with their
original hashes. `source.patch` against published `5198758` preserves the exact
product changes used for this pass; later plan/evidence text is not silently claimed
as measured source. Missing toolchains, assertion failures and rerun corrections must
be recorded rather than discarded. No installer, runtime or coverage optimization
belongs in this checkpoint.

The initial run reused an effective-script/stdout name for the two repair
configurations. The executed orchestration source is saved as
`replay-driver-used.py`; both variants were then rerun with separate source/log
paths under `repair-confirm-*`, without changing policy or assertions. The driver
now prefixes replay archive names with their group so a fresh rerun preserves
both directly. These are not new timing samples.

`checks.py` captures the source patch and measured HEAD before building, so a
reviewer can rerun from a later documentation-only commit without claiming that
commit was the original measurement. The recorded first pass captured the same
patch before starting; it also matches the independently archived journey patch.
