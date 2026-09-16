# 0056 gates 5 and 6

Runtime source: accepted rnx `3f8f6af`, unchanged by this acceptance step.
Reproduction: `../../probes/server-acceptance/README.md`.

`journey/` contains the separate client process, shipped ordinary program,
healthy traffic during await and CPU work, failed transaction with rollback
before backend reuse, and clean SIGTERM shutdown. Client/server PIDs, raw
HTTP outcomes, preparation spans, counts and independent database observations
are recorded. The private postmaster is reaped.

`checks/` records the final sequential root suites after review fix F1 at
`bd3dc04` (375/418/424 passes), formatting, notices and the previously run
stock selfcheck. The previous suite logs predated the relative README link
added in 3dea1cb and did not validate that commit's package. The link now uses
the repository URL, and each final configuration includes a passing
`the_packaged_manifest_makes_the_same_claims` test. `summary.json` identifies
the exact fixed commit. `build.json` identifies both stock binaries and
the fixed baseline `032579a`. The two default feature-graph files and lockfile
hashes match; the root workspace has only rnx. `comparison.json` records 25
byte-identical stdout/stderr/exit cases.

`timing-1.json` and `timing-2.json` retain every sample and block median from
two ABBA-twice runs, 80 observations per binary/workload per repeat on CPU 4.
Version is about 0.049 ms slower and JSON about 0.09 ms slower in both repeats:
observations within the Python spawn/communicate/wait measurement overhead,
not an established product regression. The independent reviewer rebuilt
032579a and ran hyperfine -N on core 4, 100 runs, ABAB: version before
562/545 µs and after 539/541 µs; JSON before 11.6/11.6 ms and after
11.9/11.6 ms (the first after block had σ 1.3 ms with an outlier). That
counter-measurement did not reproduce a consistent process-level regression.
This transcribes the local untracked `rnx/reviews/0056_review_claude.md`, not
a new Codex measurement. Original Python samples and all other deltas remain;
no speedup is claimed or unfavorable sample discarded. Builds,
tests and other fixtures finished before these timings.

`provenance.json` hashes the fixtures, JSON workload and unchanged server
package graph/notices, and records machine information. Linux is the only
executed platform in this gate. The review accepted gate 5 and conditionally accepted gate 6; F1 is fixed
and the three configurations revalidated. Record 0056 closes on Linux with
its stated open items.
