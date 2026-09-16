# 0056 gates 5 and 6

Runtime source: accepted rnx `3f8f6af`, unchanged by this acceptance step.
Reproduction: `../../probes/server-acceptance/README.md`.

`journey/` contains the separate client process, shipped ordinary program,
healthy traffic during await and CPU work, failed transaction with rollback
before backend reuse, and clean SIGTERM shutdown. Client/server PIDs, raw
HTTP outcomes, preparation spans, counts and independent database observations
are recorded. The private postmaster is reaped.

`checks/` records sequential root suites (375/418/424 passes), formatting,
notices and stock selfcheck. `build.json` identifies both stock binaries and
the fixed baseline `032579a`. The two default feature-graph files and lockfile
hashes match; the root workspace has only rnx. `comparison.json` records 25
byte-identical stdout/stderr/exit cases.

`timing-1.json` and `timing-2.json` retain every sample and block median from
two ABBA-twice runs, 80 observations per binary/workload per repeat on CPU 4.
Version is about 0.049 ms slower and JSON about 0.09 ms slower in both repeats:
observed regressions with cause not isolated. All other deltas remain in the
data too; no speedup is claimed or unfavorable sample discarded. Builds,
tests and other fixtures finished before these timings.

`provenance.json` hashes the fixtures, JSON workload and unchanged server
package graph/notices, and records machine information. Linux is the only
executed platform in this gate. Gates 5 and 6 are ready for review, not marked
accepted by the implementation itself.
