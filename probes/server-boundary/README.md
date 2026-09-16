# Server boundary probes

Measured by Codex on 2026-09-16, after rnx record 0053 and the accepted
0052 adapter. These are executable experiments for step four, **not an HTTP
server or a supported rnx interface**. They use pinned Rune 0.14.2 directly;
production rnx, its PostgreSQL adapter and their dependency graphs are unchanged.

```sh
cargo build --release --locked --offline --manifest-path probes/server-boundary/Cargo.toml
PYTHONDONTWRITEBYTECODE=1 python3 probes/server-boundary/run.py \
  --cpus 2,4 --output results/server-boundary-step-four
```

Run from rnx-bench. Choose two available physical cores on another machine;
the default CPUs 2 and 4 are distinct cores on the measured machine. Python 3,
Linux /proc, taskset and the PostgreSQL 18 tools used by `../postgres/cluster.py`
are required. The harness creates and removes its own Unix-socket cluster,
never uses the system server, enforces process timeouts and records cleanup.
The benchmark contains no network HTTP stack or Jupyter integration. Results
are internal dispatch latencies, not HTTP latency or a production throughput
claim. Two repeats each contain seven samples of five scheduling cases and
four ownership cases. `conditions.json` pins the binary, Rust sources, lockfile,
toolchain, CPU layout and source repository heads. `dependency-tree.txt` records
the resolved graph. No new driver version is introduced.

## Scheduling

An independent coordinator submits work through bounded Tokio channels to one
or two OS threads. Each thread owns a current-thread runtime, a LocalSet and
its own compiled Rune context/unit and VMs. No Rune value crosses threads.
The coordinator waits for a native callback from the slow VM before submitting
the healthy job. Thus an executor unable to poll its queue cannot hide its
queueing delay. Compilation and thread startup finish before submission.

Each Rune execution gets one budget of 10,000,000 instructions. The awaiting
handler sleeps for 250 ms. The CPU handler runs `loop {}` until Rune's `limited`
halt. The healthy handler returns 42. **There is no resume after exhaustion.**
The nested-async budget defect remains an exclusion, not a candidate workaround.
The healthy request must complete first for the sleep cases and for the
unsaturated two-worker CPU case. Saturation puts a CPU loop on both workers
before healthy work arrives and records the resulting delay.

Channels have capacity four, but this fixture admits at most three jobs total
and collects their task handles. It does not prove a general bounded scheduler
or a scheduling policy for arbitrary arrivals. Routing to the free worker is
explicit in the fixture; a real dispatcher must make that decision. No
thread-per-request model, work stealing or process isolation is measured.

## Pool/transaction ownership

A deliberately minimal single-slot actor owns one PostgreSQL client and its
spawned connection-driver task. A second connection is the observer. The actor
controls BEGIN, VM execution, ROLLBACK, re-admission and final driver join. It is
an ownership experiment, not a production connection pool or a public API.

A Rune handler updates a locked row and inserts an audit row, then:

0. fails with a Rune panic;
1. exhausts its whole VM budget;
2. is dropped at a 250 ms handler deadline while awaiting sleep;
3. is dropped on server shutdown while PostgreSQL is running `pg_sleep(120)`.

The first three have another borrower already in the capacity-two queue. The
owner holds the failed lease out of circulation. Observation rendezvous pause
it before rollback and after rollback but before re-admission. The observer
first gets SQLSTATE 55P03 from NOWAIT locking and sees no committed audit row.
After acknowledged rollback it can lock the row and sees the original value
and no audit row. Only then is the next borrower admitted: it must use the
same backend PID and see zero audit rows. This proves the ordering of this
explicit owner; it does not assert Rune or a pool crate does rollback for us.

Shutdown is tested during a real active command, observed through
pg_stat_activity. Dropping its Rune future does not stop that command. With
an 800 ms server statement timeout, the owner's ROLLBACK waits behind it.
The fixture records that wait and requires successful rollback before closure.
It sends no cancel request. Connection failures, rollback failures, timeout
resetting, external transaction control, commit ambiguity and cancellation
while COMMIT is in progress are not covered; production design must specify
those separately.

After the final borrower or shutdown, the owner stops admission, drops all
client references and **awaits the connection task**. It polls server activity
separately, then closes/joins the observer. Before leaving block_on it requires
socket descriptors to equal their baseline and runtime alive tasks to be zero.
It first asserts two sockets and two runtime connection-driver tasks while
the lease is quarantined. The LocalSet owner is joined separately, since that
task is not counted by the runtime metric.
The Python parent independently checks that no tagged backend remains, then
stops the cluster and verifies its directory and postmaster are gone.
There is no extra maintenance task in this minimal pool; the owned connection
driver is the background task tested. No claim about an arbitrary pool's
maintenance tasks follows.

## Limits and next decision

Two workers isolate the measured single CPU-bound handler when a worker is
available. Both busy means delay until a budget finishes. A VM instruction
budget does not bound native blocking calls, wall-clock time, allocations or
host crashes. These experiments do not alter that fact.

Rollback-before-reuse and an awaited server owner are feasible. Scope::track
alone cannot replace that owner. Whether any owner belongs in the public rnx
interface is still a design question; nothing here adds a lifecycle primitive.

The first development run stopped because the fixture expected the word
`budget` in Rune's raw error. The pinned VM says `Halted for unexpected reason
\`limited\``; that assertion was corrected. Accepted results are full fresh
runs against the final binary, not the partial run.
