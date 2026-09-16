# 0056 gate 4: extract the measured server through the public API

The executable now lives in `rnx/servers/http-postgres`, a separate workspace.
This fixture adds no private-root test module. Its schema and each handler use
`rnx::server::Program`, `Extensions`/`Scope` and the Rune re-export. The older
archived prototypes remain unchanged for comparison.

From rnx-bench, with the pinned Cargo dependencies cached and PostgreSQL 18's
server tools installed:

```sh
python3 probes/server-extraction/build.py
python3 probes/server-extraction/run.py wire
python3 probes/server-extraction/run.py transactions
python3 probes/server-extraction/run.py shutdown-int
python3 probes/server-extraction/run.py shutdown-term
python3 probes/server-extraction/run.py scheduling
python3 probes/server-extraction/classification.py
python3 probes/server-extraction/blocked_stderr.py
python3 probes/server-extraction/normal.py
```

Run scheduling without builds or other probes competing for its four CPUs.
It repeats each of six rows three times, pins workers/coordinator to the first
three allowed CPUs and the client to the fourth. These observations do not
establish a speedup over earlier binaries. One repeat missed the saturated
overlap precondition; its trace remains in `scheduling-overlap-miss/`. The
final fresh-directory run passes the unchanged assertions. The cause of the
68.77 ms preparation delay in that missed attempt is not isolated.

The three existing `wire.py` harnesses accept `RNX_SERVER_BINARY` and
`RNX_SERVER_PROGRAM` overrides; absent those, their original archived-test
command is unchanged. All 57 wire assertions, eight transaction cases,
scheduling assertions and thirteen shutdown states are reused unchanged.
Shutdown runs under both signals. Conditions record the actual binary and
program hashes, with the archived build clearly labelled as reference.

The classification integration fixture deliberately raises each SQLSTATE
from a deferred trigger: it checks propagation through HTTP, COMMIT
classification, one attempt, and lease retirement. It does **not** reproduce
serialization or deadlock mechanisms; those remain the accepted gate 3
`commit-classification` evidence. A second connection sees zero victim rows,
and the same worker's next lease has a different backend PID. The `40003`
control stays ambiguous even though the observer sees rollback.

The blocked-stderr fixture fills an OS pipe before launch, leaves it unread
through the five-second native-poll shutdown deadline, requires exit 1 and
no clean-close event, then checks that its original bytes are still there.
The owner report persists in the separate event log. Backend disappearance is
observed independently after exit; process termination is not labelled graceful
cleanup. The driver-stall and native-stall injections are package-test-only.

`normal.py` runs the executable built without test support: echo, a committed
write, a failed transaction, clean shutdown despite the test injection variable,
and a compile refusal for the fixture's missing test functions. Stdin is a Unix
socket and the final identity baseline must preserve that inherited socket
while reporting zero owned sockets. This is a build/ownership smoke check,
not gate 5's full example journey.

Every database fixture starts its own private Unix-socket cluster through the
existing cleanup-owning `Cluster` helper. No system cluster or user database is
used. Raw results are under `results/server-extraction-0056`. Build provenance,
source hashes and both binaries are in `build.json`; the package carries its
own resolved graph and deterministic licence inventory. The original missing
`syntree 0.18.0` licence text remains explicitly listed.

Gate 4 is ready for review. Gates 5 (example journey) and 6 (stock comparisons)
remain open. Linux is the only executed server platform.
