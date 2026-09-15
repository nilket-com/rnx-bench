# Linux containment replacement for record 0047

Build `cc -Wall -Wextra -Werror -pthread pdeath.c -o pdeath`, then run
`python3 probe.py`. It imports the real rnx worker fixture and uses the current
release binary; hashes and results are in `results/jupyter-0047-replacement/`.
Linux only, with pidfd_open/pidfd_send_signal support. No production patch.

The parent sets PR_SET_CHILD_SUBREAPER, starts a worker and runs process::run
with a fixture which double-forks and starts a new session. Cleanup independently
scans every /proc/self/task/*/children entry, uses pidfds to signal, and repeats
kill/reap until empty within five seconds. No other reaper runs concurrently.
The known fixture PID is used only to assert the outcome, never to discover
cleanup targets. The parent launches no unrelated helper children. Cases cover
cooperative interruption followed by close, hard worker death, and a stopped
worker killed before its supervisor can clean up. Fixture readiness is published
by atomic rename; an initial confirmation attempt exposed and fixed a partial
JSON read with the original direct write. No product defect was involved.

The separate C probe demonstrates direct-child SIGKILL on parent death,
parent-process death before prctl caught by a pre-fork PID/recheck, and spawning
thread death while the process remains alive. A fourth case exits the spawning
thread before the child sets prctl: getppid still matches and the child survives.
That negative case matters for the future shared rnx change. It does not claim
credential-transition coverage, Windows jobs, hostile-code isolation, cgroup
containment, or cleanup after the harness itself dies. All owned children are
killed/reaped after each case. Existing rnx process behavior is unchanged.
