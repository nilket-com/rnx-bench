# Worker containment gate for rnx 0047

Measured on Linux against the rnx release implementing 0046. This is a separate
question from control-descriptor inheritance: which process will enforce a
child's deadline after the worker dies?

```
PYTHONDONTWRITEBYTECODE=1 probes/jupyter-transport/.venv/bin/python probes/jupyter-containment/probe.py --rnx /absolute/path/to/rnx
```

The adjacent rnx checkout provides `tests/worker_parent.py`. The fixture uses
Linux PR_SET_CHILD_SUBREAPER only in its own process, records the exact child/group
IDs it created, and kills/reaps all survivors in finally blocks. The sleeping
fixture would end itself after 30 seconds; that is its own behavior, not an rnx
deadline. No descendant is intentionally left running. This is not a Windows
containment result.

Every request sets a two-second process::run deadline. The control cases show
that deadline expiry and cooperative interruption end an ordinary child group.
The counterexamples are:

1. Kill the worker, then observe the child still running 2.5 seconds later.
2. Stop the worker before sending SIGINT, then kill it: the child still survives
   past the deadline. Sending an interrupt is not proof cleanup ran.
3. Have the child fork a descendant which calls setsid, then cooperatively
   interrupt the worker. The escaped descendant survives; the confirmation run
   also waits past the requested deadline before checking it.

The source explains why: host.rs creates an Instant and polls it in the worker's
run_child_with loop. This is not an OS timer inherited by the child. Killing the
worker kills the supervisor which enforces the deadline. group.end addresses
that supervisor's recorded group; host.rs explicitly states that a descendant
which leaves it is outside that cleanup.

Therefore the 90-second maximum permitted argument is **not** a remaining
lifetime guarantee after the supervisor dies. Interrupt-first is useful but
insufficient for 0047's unconditional surviving-descendant stop condition.
The next decision must specify stronger containment and its platform constraints,
or explicitly revise the promise. This probe chooses neither on the user's
behalf, and no kernel implementation follows it until review.
