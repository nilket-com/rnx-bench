# Record 0047 replacement probes — 2026-09-15

Plan revision: rnx `123bfd0`. **Kernel implementation remains stopped.**
Sources are `probes/jupyter-libzmq` and `probes/jupyter-containment-replacement`.
Initial and confirmation JSONL traces are preserved. The confirmation containment
run adds the early spawning-thread-exit negative case and waits for the stopped
worker's actual stop state. The first confirmation attempt had a fixture
readiness-file race; atomic publication fixed it before the saved confirmation.

## Native transport

Locked zmq 0.10.0 / zmq-sys 0.12.0 / bundled libzmq 4.3.4. The system's 4.3.5
is not linked. An offline fresh-target release build took 7.02 s, maximum RSS
277912 KiB as reported by /usr/bin/time. This is a probe build, not kernel size
or startup. Versions, executable hashes/sizes, Linux package licence declarations,
build logs and source hashes/line references are beside this file. Licence
declarations are not a finished redistribution notices audit.

Both transport runs observed:

| Input / condition | Observation |
| --- | --- |
| 64 MiB frame length, no body | peer EOF, no sampled RSS growth |
| 2048 legal 8 KiB MORE parts (16 MiB) | zero application parts; RSS +17010688 B |
| 4096 legal 8 KiB MORE parts (32 MiB) | zero application parts; RSS +34025472 B |
| empty final part | 4098 parts reach receiver, including routing and final part; application refuses |
| other shell peer during unfinished input | replies in under 1.5 ms in these runs |
| control and heartbeat | remain responsive |
| 20000 PUB sends with reading and stalled subscribers | all sends succeed; reading peer receives output; delivery not guaranteed |
| socket-owner joins and context drop | clean exit in approximately 33–36 ms |

The exact timings and subscriber counts are observations, not performance gates.
RSS is sampled externally at page resolution inside a 512 MiB address-space
limit; only 32 MiB of body is sent. This finite counterexample plus source
inspection refutes a claimed frame-cap × HWM receive bound; it does not measure
infinite growth or deliberately exhaust memory.

The suggested application-side fix is unavailable: recv_bytes is already called
one part at a time, but native ypipe::write keeps the flush boundary unchanged
for incomplete items. pipe::write advances message accounting only at the final
part. Until then the parts are not available to the application. Fair-queue
stickiness after delivery begins does not imply a peer can expose an endless
unfinished multipart to that loop. Other shell requests still answered in this
probe. Rejecting after 32 application parts is too late to bound native memory.

Signed replies, wrong-signature silence, malformed/extra-buffer refusal,
additional routing envelopes and empty-key mode also passed. No-subscriber
publication and full JupyterLab integration are not new acceptance claims here.
The unresolved receive path stops integration before those later gates.

## Linux containment

The new discovery loop found escaped/double-forked descendants itself and reaped
all children after cooperative shutdown, hard worker death and stopped-worker
termination, in about 10–11 ms in these fixtures. This is a standalone Linux
prototype using the unchanged rnx binary, not production containment or Windows
evidence. Process discovery and cleanup share one reaper and no unrelated child
processes. The fixture independently checks its known descendant is gone.

Direct-child parent-death signaling worked once armed. Death of the whole parent
before setup was caught by the PID check (exit 92). Death of the spawning thread
after setup killed the child while its parent process stayed alive. Death of that
thread BEFORE setup left the child alive with an unchanged parent PID. The
shared-rnx follow-up must establish spawning-thread lifetime, not just copy a
prctl/getppid pair. Final cleanup reported no children.

No browser capture, Windows execution, root-rnx test rerun or production code
change is claimed. These are pre-integration probes and the stop remains active.
