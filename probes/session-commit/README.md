# 0063 gate 5: commitment and real owners

Build rnx and rnx-project debug binaries with `--features test-support`, then:

```
python3 probes/session-commit/setup.py
python3 probes/session-commit/check.py
```

The ignored target must be absent for a fresh setup. Root tracked inputs must
remain unchanged throughout. Setup freezes both binaries. The tiny runtime
facade re-exports the actual rnx library; the PostgreSQL facade re-exports the
shipped adapter. The added Polars-named module is deliberately a small builder
fixture, not the Polars engine. Gate 4 and final dogfood cover real engines.

Each case starts a non-Send tracked future with a drop observer, a real HTTP
request to a held server, and a real PostgreSQL query on a private cluster.
A sleep within the last input exposes exactly the two request sockets before
Rustyline resumes (the editor creates its own socketpair at each prompt).
The terminal then requests the added adapter through the real tool and probe.

Test-only stops expose before commitment, after cleanup and after the final
stamp check before exec. Artifact renames occur only in the private cache and
are restored. Cancellation is a real SIGINT. Exec failure is the actual OS
failure after removing the checked path. Cleanup panic is the started tracked
future's destructor. Replacement builder failure and panic occur only after the
probe has succeeded. Eight cases distinguish preservation from terminal loss.

No extra old-runtime turn precedes the preservation observations. Socket
identities are observed separately from the independent PostgreSQL activity
view; backend timeout residual is recorded, not called a client leak. Scoped
server threads, sessions, probe processes and the private postmaster are joined
or observed gone. Complete PTY transcripts and owner events are retained.

Fixture development corrections: the facade initially reused the shipped
adapter's package version (Cargo lock collision); socket sampling initially
included Rustyline's transient pair; one assertion expected unquoted object
keys; a post-cleanup assertion initially inspected only unread PTY bytes rather
than the full transcript. None required production-policy changes.
