# store-fast-path-0171: store fast-path experiment (rnx record 0171; result STOP)

- **base:** fork main `bb8e6937` (`~/work/rune`).
- **candidate:** branch `w3-0171-store-fast-path` (`~/work/rune-w3-0171`).
	- Run 1 is `bdac7187`.
	- Variant B is `ddc92e73`, whose binary was byte-identical to run 1's.

Same harness source, lock and features. Everything runs under `flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock`.

| Script | What it does |
|---|---|
| `CANDIDATE_REV=<8 hex> ./build.sh` | builds base and candidate, plus the native clock |
| `python3 measure.py OUT` | correctness (0168 corpus + fixtures), base reproduction, 5 PMU repeats, ABBA wall, the frozen decision |
| `python3 check_decision.py RUN/measure.json` | independent recomputation of the frozen decision from the retained arrays |
| `./diag_context.sh OUT` | S2 samples of whole context-mode invocations, including teardown (diagnostic) |

The allocation diagnostic is in `ledger/lock.log`. Evidence: rnx `plans/0171_store_fast_path_evidence.md`.

The measure JSON keeps 35 of the 40 executed correctness transcripts: a key collision between two directories both named `fixtures`. Every execution was asserted when it ran (see the evidence).
