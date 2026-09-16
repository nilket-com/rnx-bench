# 0054 gate 5: a transaction lease belongs to the server

Private Linux prototype, measured by Codex on 2026-09-16. This is a separate
copy of the accepted `server-http/` gate-4 prototype from bench `6d146e2`,
with a pool owner and one fixture route added. It changes neither stock rnx
nor the accepted PostgreSQL adapter. There is no public server or pool API.

```sh
python3 probes/server-transactions/build.py
python3 probes/server-transactions/transactions.py --output results/server-transactions-0054/run-0
python3 probes/server-transactions/transactions.py --output results/server-transactions-0054/run-1
python3 probes/server-transactions/regression.py --output results/server-transactions-0054/wire-regression
```

Run from rnx-bench. The build archives rnx HEAD and injects `probe.rs` and
`pool.rs` as private test modules. `Cargo.lock` starts from the accepted HTTP
prototype lock and adds exactly pinned tokio-postgres 0.7.18 and its resolved
requirements; no baseline package version was removed. Builds are locked and
offline after resolution. `graph.json` inventories all targets and features;
`ADDITIONAL-NOTICES.md` adds the shipped Linux dependency licences to the
archive's existing notices. Non-Linux graph entries are inventoried, not a
claim to have built or distributed them. No binary is checked in.

Each case records the archive/build/module/graph/lock/executable hashes, events,
RSS/descriptor samples and fixture conditions. Repeat results also hash the
Python driver, fault proxy and shared private-cluster helper and name the
PostgreSQL version. The final repeats use the same binary. Initial development
runs live outside the repository and are not evidence. An initial unseeded
resolution selected unrelated dependencies; it was discarded in favour of the
accepted HTTP lock plus the PostgreSQL graph before final runs.

## Contract under test

Each worker owns a private two-slot pool, eagerly connected: four connections
and driver tasks total. Each connection has one exclusive lease. Tokio drives
its connection task on that worker's current-thread runtime, including while
idle. The pool owns its JoinHandle; no request, lifecycle scope or task-handle
drop substitutes for joining it. Counters are compared with actual runtime task
metrics at idle startup and close. There is no additional eviction/reaper task.
This is a minimal pool, not adoption of a production pool library.

The HTTP admission limits stay two workers, four active credits each, one
sixteen-entry central queue. Pool waiters consume an already charged active
credit; they do not form another unbounded admission queue. Waiting for a pool
permit is cancellable and constructs no handler context. Once a connection is
taken, BEGIN is owner work; cancellation then requires rollback before release.

`/db` runs the same compiled Rune handler with real per-handler batteries and
lifecycle. A borrowed native argument is copied into a lifecycle-tracked query
future; the future borrows an Arc to the leased client. The application owns
BEGIN/COMMIT/ROLLBACK; scripts cannot issue those through the fixture's one
native function. VM failure, budget halt, response-validation failure or detected
cancellation before successful completion leads to rollback. The VM, registration
closures and tracked operations end before transaction cleanup. The lease,
request's active credit and connection driver outlive those handler values.

A validated successful handler starts COMMIT. Once that command is dispatched,
client disconnect does not switch to rollback or imply cancellation of COMMIT.
The owner awaits acknowledgement or its cleanup deadline. Any unacknowledged
COMMIT is conservatively an **ambiguous commit; no retry**. The owner retires
the connection and never queries the database to reconcile that operation.
This includes server errors as a conservative first-prototype policy; finer
classification is not claimed. A failed/unacknowledged rollback also retires.
Replacement restores capacity but never repeats application SQL. The sequential next-borrower gate selects the replacement on that worker and
proves its PID is new; concurrent borrowers are not promised a particular idle
connection.

The Rune handler has already ended when transaction completion is decided.
Ambiguity is therefore a request/transaction-owner error, recorded by request
id in the server events, not a catchable exception returned to an already-ended
Rune VM. HTTP preserves the accepted generic 500 response; a disconnected
client receives none. These are prototype contracts, not additions to
`postgres::query` or a public transaction API.

Fixture bounds: connect 1 s, server statement_timeout 800 ms per command,
COMMIT/ROLLBACK acknowledgement 1.2 s, driver retirement 1.2 s. HTTP's admitted
clock remains 2 s and its independent coordinator continues running. There is
no PostgreSQL CancelRequest. Dropped queries may remain active until the server
notices or the statement timeout expires; rollback queues behind protocol
completion. A retirement deadline aborts and joins the driver and fails the
fixture explicitly, never reports clean shutdown. That failure path is not
exercised by these successful gate-5 runs and needs gate-6 coverage.

## Deterministic observations

`proxy.py` is a fixture-only PostgreSQL v3 frame relay over private Unix sockets.
It forwards the real command to PostgreSQL, withholds the first response frame
and the rest of that command's reply, and exposes a barrier. It neither invents
success nor rewrites driver errors. It bounds fixture frames to 16 MiB and waits
at most four seconds for the harness. The owner keeps its ordinary 1.2 s clock.
No proxy is proposed for the product. The observer uses psql directly on the
private cluster, outside the proxy, the pool and rnx.

Eight cases run in each repeat:

- **Rollback acknowledged:** a Rune panic follows an INSERT. While rollback's
  reply is withheld, the independent observer sees no row, no acknowledgement
  or teardown exists, and the active HTTP credit is still charged. Releasing
  the reply permits reuse of that exact backend PID on its worker.
- **Rollback acknowledgement lost:** at the same barrier, the observer kills
  that backend, then the proxy cuts the transport. This is loss while the
  owner is awaiting ROLLBACK, not a claim PostgreSQL was still executing SQL
  when killed: it may already have rolled back. The owner receives an error,
  joins/retires the connection, and the next borrower on that worker gets a
  PID absent from the initial pool.
- **COMMIT acknowledgement lost:** PostgreSQL has committed, the observer sees
  one row, but the owner has no acknowledgement. Cutting transport produces
  ambiguity and retirement. Exactly one COMMIT travelled on that backend;
  subsequent successful requests leave the original row count at one. The
  observer's knowledge is not fed back into the owner's error.
- **Disconnect during COMMIT:** at that same barrier, an HTTP RST is observed
  through the request's cancellation signal before the transport is cut. The
  owner still reports ambiguity and retires; cancellation does not undo a commit.
- **Cancel an active SQL command:** observe pg_sleep active, then send HTTP RST.
  The handler drops, rollback waits for command completion, acknowledgement
  permits same-PID reuse, and the INSERT is absent.
- **Connection loss during an active command:** observe the sleeping backend,
  terminate it, require rollback failure/retirement and a new PID on next borrow.
- **Budget halt:** INSERT followed by a whole-budget Rune loop. Rollback is
  acknowledged, nothing was committed, and the same PID is reusable.
- **Pool contention:** eight active requests, four leased sleeping connections,
  four pool waiters with no handler context. Cancel all; the four waiters refuse
  without borrowing, four leases roll back, and a subsequent request succeeds.

The barriers, PID comparisons, row counts, cancellation order and active-credit
observation are assertions. No timing-based guess determines when to cut a
connection. The harness allows three seconds for observations and five seconds
for a request result. The contention observation must happen before the 800 ms
statement timeout; failure to establish that state fails rather than skips it.

## Pool tasks and what remains open

In the first seven cases, after handler teardown and HTTP disposal, the process
has exactly five socket descriptors: listener plus four pooled connections.
The observer sees four tagged backends. This is intentional pool ownership,
not leaked request work. Each worker reports two drivers with no active leases.
Shutdown closes idle clients, awaits every driver, reports zero pool tasks,
then performs the existing final runtime drain and joins worker threads. Client
socket closure and backend disappearance are checked separately. Proxy threads
are joined and the private cluster is stopped/reaped by the shared guard.

Both transaction repeats and the full 57-case raw-wire regression pass with
the pool enabled. These shutdowns occur after the tested requests settle.
**Gate 6 remains open:** shutdown during active SQL, pending rollback/COMMIT,
awaiting/CPU work and queued admission needs its own matrix. Public server
entry, pool reset/session-state hygiene beyond this restricted application,
arbitrary SQL transactions, pooling performance, Windows execution and stronger
isolation from trusted native code are not established by this probe.
