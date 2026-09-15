# Integrated Linux worker supervision (record 0047)

Run from the bench root:

```sh
bash probes/jupyter-supervision/run.sh
```

Requires the adjacent rnx checkout with its release worker already built and the
pinned `probes/jupyter-transport/.venv` environment. The runner builds the kernel
and acceptance examples, runs both component test configurations, then runs each
fixture twice. It reruns the original 0048 wire fixtures through the binary
override into a new results directory, preserving the extraction evidence.

- `probe.py`: real signed jupyter_client requests, persistence, counters, origins,
  immutable parents, silent/unit/errors, source limits, interrupt recovery,
  independent control, stop_on_error, and a newly launched kernel after restart.
- `extended.py`: flushed progress before completion, split/invalid UTF-8, both raw
  stream caps, 64-request/4-MiB admission (including escaped source), escaped
  double-fork cleanup on shutdown and worker death, and the async CPU limitation.
  The kernel discovers descendants itself; fixture PIDs only verify the outcome.
- `boundaries.py` and `fake-worker.py`: blocked stream/result sinks at the actual
  Worker API, duplicate settlements that cannot extend the deadline, incomplete
  stderr barriers and malformed settlement. No acknowledgement file may appear;
  incomplete boundaries must never send execute_result or successful idle.
- `notebook.py`: private temporary kernelspec, nbclient execution, save and reopen.
  No user installation and no JupyterLab screen claim.

The short progress gate allows 400 ms before a 500 ms sleep ends; interruption
allows one second; the pending sink must fail in 4.9–6 seconds; shutdown allows
5.5 seconds from the client (five internally). These tolerate scheduling, not
unbounded waits. Logged timings are individual observations, not benchmarks.
The external per-fixture timeout catches hangs and does not replace those gates.

Results, commands, exit status, package versions and source/binary SHA-256 hashes
are under `results/jupyter-0047-supervision`. Results describe Linux only.
The Windows check compiles portable code and an explicit unsupported launcher;
it is not Windows supervision verification. Root suites are run sequentially
separately and their outputs are preserved beside these results.
