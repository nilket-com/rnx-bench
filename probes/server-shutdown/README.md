# 0054 gate 6: shutdown is an observed outcome

Private Linux prototype, measured by Codex on 2026-09-16. This copies the
accepted gate-5 `server-transactions/` prototype from bench `b0d1cf1`. Its
connection/transaction policy is unchanged. The lockfile, resolved graph and
additional notices are byte-identical to that prototype. No root source,
manifest, dependency graph, adapter, kernel or public API changes.

```sh
python3 probes/server-shutdown/build.py
python3 probes/server-shutdown/shutdown.py --output results/server-shutdown-0054/run-0 --signal TERM
python3 probes/server-shutdown/shutdown.py --output results/server-shutdown-0054/run-1 --signal INT
python3 probes/server-shutdown/transactions.py --output results/server-shutdown-0054/transaction-regression
python3 probes/server-shutdown/regression.py --output results/server-shutdown-0054/wire-regression
```

Run from rnx-bench. `--case NAME` selects a single matrix row. The build archives
rnx HEAD and injects the private modules; it remains locked and offline. Results
retain source/driver/graph/lock/executable hashes, exact injected manifest and
command, PostgreSQL version, raw events, proxy observations, server output and
independent RSS/FD samples. Each matrix run owns a fresh private PostgreSQL
cluster and each row starts a fresh server and Unix-socket proxy. No system
cluster or public service is touched. The shared cluster guard stops and reaps
the postmaster even after a failed assertion; success separately requires it
gone. Development smoke results are outside the repository.

## Changes from the accepted owner

- The coordinator's five-second allowance starts before listener disposal and
  connection-task cancellation. Its deadline event names active credits,
  remaining request ids, unjoined worker indices, connection-task count and
  owned socket descriptor/identity pairs. Completed and queued request ids are
  removed from that ledger, so a finished owner cannot be reported as pending.
- Queued ids are recorded before disposal. The fixture asserts they never
  construct contexts after shutdown. All connection tasks are cancelled; a
  client may see EOF/reset instead of a response. No graceful-response promise
  is introduced for those cancelled HTTP connections.
- Worker failures are collected after joining those threads, recorded as a
  failed-shutdown event and cause the test process to fail. They never fall
  through to a clean-close event.
- Two explicit fixture injections reach failure paths. `RNX_POOL_STALL_DRIVER`
  parks a driver task **after** the real connection future ends, keeping its
  task counter live. Retirement times out, aborts and awaits that task, records
  its backend/worker identity and remaining driver count, and fails the worker.
  `/healthy?shutdown-stall` sleeps 6.5 seconds inside a native poll, longer than
  the existing five-second allowance. Neither injection is a production API or
  evidence that an ordinary driver naturally stalls in that state.

A driver failure unwinds its worker. Any other driver disposed by runtime
unwinding is not called an awaited owner: the outcome is failure. In the native
stall case the coordinator cannot safely join or stop the blocked worker at the
deadline. It reports the unjoined owner and fails; the test process's termination
ends that thread. This is process containment, not thread preemption. The
supported entry point must retain an explicit failure policy; it does not exist
yet. Exit 101 below is the Rust test harness's failure status, not a newly chosen
rnx product status. The parent waits/reaps the process and the separate database
observer waits for backend disappearance; neither is substituted for a clean
owner report.

## Matrix and assertions

Every signal follows an observed event or database state; launching a request
and sleeping is not accepted as proof that it was running. Each case verifies
new TCP admission is refused after the shutdown event.

| Row | State observed before signalling | Required result |
| --- | --- | --- |
| idle | Four idle pool backends/drivers | Await pool tasks, join workers, clean close |
| partial-reads | One incomplete head and one incomplete body | Dispose transport; build no handler |
| awaiting | Rune await-start | Cancel handler and clean close |
| cpu | Rune CPU-start, fault not yet produced | Fault only after shutdown starts; await budget halt, then close |
| active-sql | Observer sees pg_sleep active | Drop handler, await rollback after statement completion, row absent |
| queued-awaiting | Eight active awaits plus sixteen queued | Cancel active; queued ids never construct contexts |
| queued-sql | Four active SQL leases, four pool waiters, sixteen queued | Cancel waiters without construction, acknowledge four rollbacks |
| pending-rollback | Real rollback reply withheld | Keep owner through shutdown, release reply, then close |
| pending-commit | Real commit reply withheld; observer sees row | Preserve COMMIT, release acknowledgement, close with row committed |
| rollback-deadline | Rollback reply withheld past 1.2 s | Record unacknowledged cleanup, retire, then clean resource teardown |
| commit-deadline | Commit reply withheld past 1.2 s | Record ambiguity/no retry, retire, row remains committed, clean resource teardown |
| driver-deadline | Driver parking injection enabled | Abort-and-join evidenced; worker failure, no clean close, exit 101 |
| overall-deadline | 6.5 s native poll observed | Report still-owned request/worker/sockets near 5 s; no clean close, exit 101 |

For pending replies, shutdown is observed before the proxy releases anything.
For acknowledgement deadlines, the proxy releases only after an observed
`cleanup deadline` error. This proves the owner's clock, not a proxy timeout.
The proxy's observation barrier is at most four seconds. No retry or database
reconciliation is added. A request error followed by retired connections and
fully joined tasks can end in resource-clean shutdown (exit zero); that status
does not mean the transaction succeeded or its rollback was acknowledged.

The coordinator's five-second timeout is checked against its own event clock,
with a 4.8–5.5 s fixture window. The 1.2 s acknowledgement deadline is checked
at 1.1–1.7 s. Normal shutdown must complete within a 5.5 s outer observation;
the process watchdog is seven seconds. The native-failure outer observation
must finish below 6.5 s, before the injected call would return. These tolerances
separate an actual timeout from natural completion. They do not bound arbitrary
OS stalls, native calls or machine scheduling in a product deployment.

## Two independent observations

The server's clean-close event requires equal context builds/retirements, zero
active credits, connection permits and newly owned sockets, and preserved
inherited descriptors. Each worker first closes its pool and reports zero
leases, idle clients, driver counters and runtime tasks, then reaches the final
whole-runtime drain and joins. Failure cases explicitly lack that event.

A separate observer uses psql directly against the private cluster, bypassing
both the pool and fault proxy. It records tagged backend PIDs, state and query
approximately every 15 ms **plus psql invocation cost**, before and after the
signal. It must independently reach zero and check the final audit rows before
cluster teardown. Observations can reach zero before the parent's process wait
returns; neither clock is treated as the other. The external signal-to-exit
number includes process-wait polling/reaping and the close helper writing its
artifacts, and is not a precise measurement of the instant of process exit.
The server event clock separately records shutdown and close/failure.

Both 13-case matrices pass: 11 resource-clean rows and two explicit failures in
each. The clean rows build and retire 30 contexts per matrix. The eight accepted
transaction cases and all 57 wire cases also pass with this binary. No server,
proxy thread or private postmaster remains. Raw test-runner logs and licence
texts retain their original whitespace.

This evidence leaves the supported server-entry contract open. Before that
contract is fixed, distinguish definitive PostgreSQL COMMIT rejection (such as
a deferred constraint failure) from a lost/malformed completion. This prototype
retains gate 5's conservative ambiguity label for both. General pool session
reset, arbitrary script transactions, pooling performance and Windows execution
remain unproven. Root suites/startup are unchanged and are not remeasured for a
private archived prototype.
