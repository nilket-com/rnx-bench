# 0054 gate 2: assembly, with the actual rnx installers

Measured by Codex on 2026-09-16 against rnx `c28cf22`. **Gate 2 remains open**:
the assertions reproduce an HTTP cleanup stop. A passing fixture is not a
claim that a server can use the current cleanup entry point.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/server-assembly/run.py \
  --cpus 2,4 --output results/server-assembly-0054/run-0
```

The Linux harness archives the exact rnx HEAD into a temporary directory. It
adds `probe.rs` as a private cfg(test) module and a cfg(test) accessor to the
existing execute::Runtime's inner runtime. Those are the only injected source
changes. They expose no production API, replace no implementation, and change
no manifest or lockfile. The full core, filesystem, path, time, text, HTTP and
environment installers run, then the real Extensions::with_lifecycle and
install_with path. Temporary files disappear on completion. Build artifacts
stay under this probe's ignored target directory. Proxy variables and RNX_CONFIG
are removed from the subprocess environment. No PostgreSQL server is used.

The command runs one selected private release test with test-support enabled
for allocation measurements. It does **not** run or claim the full root suite.
The harness pins the test to two distinct physical cores on this machine;
adjust the CPU list elsewhere. Each run records source/harness/lockfile/binary
hashes, rnx revision, toolchain, CPU information and the exact command.

## Assembly actually tested

One schema context invokes the extension builder once and compiles one Unit.
That Unit is shared across workers and all samples in the process. Each serving
context has its own RuntimeContext, with identical registrations but different
captured lifecycle and HTTP state. The immutable argv contents are identical,
and each env::args call converts a fresh Rune value. The environment functions
retain their existing process reads. We do not claim a single shared set of
stateful native closures or introduce ambient scope resolution.

Two worker threads each own a current-thread runtime and LocalSet. Serial
admission builds one context per worker and reuses it for serial executions.
Multiplexed admission allows at most four handler VMs per worker and builds a
fresh context, Scope and HTTP state per handler. Each gets one whole
10,000,000-instruction budget; no halt is resumed. Request/response messages are
owned Rust data; only Unit is shared between worker threads. Returned values
are converted through rnx's real JSON writer before crossing the boundary.

Context builds, runtime-context creation, extension-builder invocations and
retirement are counted/asserted. Every retirement is also checked by trying a
new tracked operation and requiring the retired-context error. The shared unit
resolves JSON, path, env, time, the extension and HTTP against the new runtime
registrations. This is evidence for these compatible registrations, not a
contract that arbitrary different adapter schemas can share a Unit.

## Scheduling and accounting

Each complete run has three samples of each shape/workload (18 cases):

- Awaiting: sixteen 40 ms sleeping requests, evenly assigned to two workers,
  then a quick request behind worker zero's queued work. This intentionally
  fills both shapes and includes queue delay in the healthy request's latency.
- CPU: a loop is observed entering worker zero before healthy work is sent to
  worker one. The loop ends at its whole budget.
- Saturated: both workers enter a CPU loop before healthy work reaches worker
  zero. Multiplexing is not CPU preemption.

The schema compilation and serial worker construction finish before request
submission. Fresh multiplexed context construction happens after submission
and its latency is included. build_total_ms separately sums wall-clock build
intervals (including RuntimeContext construction), not CPU time. Unit compilation
is timed separately. Complete_ms ends when all response messages arrive and
excludes final worker teardown. Throughput is a finite-batch dispatch rate,
not HTTP throughput.

memory::peak uses the real test-support counting allocator. Peak increase is
process-wide tracked allocation growth, not RSS or isolated application memory.
It includes the fixture's threads/channels/results. retained_delta_bytes is
sampled after worker threads join but while result rows and harness objects
remain; it is not an assertion of leaked application bytes. Compare matching
workloads. Raw numbers and definitions are retained rather than treating them
as a production memory bound.

The two per-worker request channels have capacity 16, with at most one job
per worker dequeued while waiting for a semaphore permit. Task handles remain
until the finite batch joins. This is a bounded fixture, not proof of the
production queue's accounting or overload responses.

## Ownership assertions

The extension creates tracked futures and deliberately stores them strongly in
a thread-local fixture map. An operation therefore remains retained after its
handler VM fails, so revocation cannot pass merely by dropping the VM. The
failing handler starts an operation, selects a short timer, then panics. Its
operation must report `operation cancelled` on repoll. An older operation in
another context remains live and later returns its original value. The fixture
checks both same-worker multiplexing and cross-worker isolation, closes the
contexts, clears the retained wrappers and asserts zero live inner operations.

## HTTP stop, not a waived gate

Real http::get calls reach two held loopback fixtures. Each has a distinct rnx
HTTP state and uses the shared compiled Unit. A failure in B must yield clean
read-zero EOF on B, while A remains open and later returns `ok`. A read error
is not accepted as EOF. Cross-worker cleanup succeeds when entered between
block_on calls on B's separate runtime, with A unaffected.

On a shared runtime, the existing State::clear:

1. aborts its own requests and drops its client;
2. synchronously calls Runtime::drain_http;
3. requires the **entire runtime** to reach zero alive tasks.

Calling it inside the long-lived block_on panics when it tries nested block_on.
The fixture catches this only to record the stop. It then pauses the runtime
and calls the same cleanup outside block_on as a diagnostic control. That
returns `HTTP cleanup did not finish within 100 ms` while A's legitimate request
is pending. In both final runs, four tasks were live before this control. B
closes cleanly, A is not cancelled, and after releasing A the fixture can close
both states and assert zero tasks. All fixture threads are joined.

Pausing the runtime is not a proposed server workaround. Even serial workers
need an await-compatible cleanup boundary if the server stays inside one
long-lived block_on; multiplexing additionally needs completion accounting scoped
to the owner being closed. Existing CLI/session semantics are not changed.
No HTTP library or admission shape is selected from this partial gate.

## Development corrections

An initial helper name shadowed a runtime constructor; that compile error was
in the fixture. A first output assertion used Rune Value's Debug outside its VM
interface environment; it now uses rnx's actual JSON writer. A Python executable
hashing typo used os.X rather than os.X_OK. Final evidence comes from two fresh,
complete runs of the corrected source, not those partial development runs.
