# Server execution entry — record 0056 gate 1

Run `python3 probes/server-entry/run.py` from rnx-bench. This separate workspace
uses the sibling rnx repository through a path dependency and the optional
`server-runtime` feature. It accesses no private root module and injects no
source into rnx. Its lockfile pins the resolved graph. Results are in
`results/server-entry-0056/`; the conditions record source hashes because the
initial measurements preceded the implementation commit.

The fixture compiles a real two-file Rune program exactly once. It constructs
requests with `rnx::rune::runtime::Object` and reads response fields using
`Value::borrow_ref::<Object>()` and `as_integer`. No JSON writer participates.
A compile-time assertion requires Program to be Send + Sync. Root's compile-fail
doc test rejects sending Invocation to another worker.

A controlled native future records its first poll and synchronous drop. The
fixture polls real Rune handler executions, not the tracked future directly.
For cancellation it verifies started=1, dropped=0, drops the run future, then
asserts dropped=1 and close's `cancelled` category with no intervening runtime
turn. Destructor panic instead produces `cleanup`. Caller unwinding also
leaves an explicitly closeable cancelled invocation.

Both isolation cases start the two operations before failing either. On one
worker both run futures are held together. Across two workers a barrier proves
both started, then another barrier holds the survivor until its neighbour's
failure has settled. The survivor remains pending and undropped, then returns
its original 41 plus the public request's 1. Wakers are notified when fixture
readiness changes, including inside Rune select. Exact builder and captured
context-token destruction counts are asserted for schema, each invocation and
partial construction failure.

Other checks cover zero/sentinel budgets, budget halt with no resumption,
module-attributed runtime and compile diagnostics, catchable process exit and
cleanup of a partially installed context. This is not an HTTP, database,
shutdown or performance gate. No filesystem socket or server is created.

During fixture development an assertion unwound through a live tracked
operation and exposed the existing panic catcher's attempt to change the hook
while already unwinding. Root now catches cleanup without hook replacement on
that path; its focused regression additionally catches a destructor panic while
preserving the caller's original panic. Such nested panic diagnostics use the
caller's hook rather than the usual temporary silent hook.

## Gate 2: host boundary

Run `python3 probes/server-entry/host_boundary.py` on Linux. This invokes the
root's test-only subprocess fixture with `server-runtime,test-support`, then
checks compile-fail documentation and generated public type listings. The
private test controls set the real existing script flag and emit the existing
config-open counter; they add no public accessor or production behavior.

One child installs its own SIGINT/SIGTERM handlers and verifies actual delivery
before and after compilation, successful and failed execution, and close. It
sets the CLI script flag before testing the server exit refusal. A valid config
is installed: server operations report zero opens; an explicit config load as
positive control reports one. Owned compile and VM failures produce no library
output. The parent rejects unexpected child stdout and all child stderr.

Another child starts a native call blocked on a condition variable. After
observing the call has started, its host waits 5.25 seconds, confirms the worker
has not finished, releases it and joins it. The library installs no kill timer;
this is a finite observation, not proof of arbitrary native-call cancellation.
It deliberately does not test or implement the standalone server's hard exit.

**Run feature configurations serially in one target directory.** Default and
`test-support` integration tests launch the same executable path; concurrent
builds can replace it during the other configuration's test. Separate target
directories are required if running configurations concurrently.
