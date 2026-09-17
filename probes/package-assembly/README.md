# 0057 gate 4: generated assembly through the private tool core

Run sequentially from rnx-bench with the accepted PostgreSQL and Jupyter fixture
prerequisites (the private PostgreSQL 18 toolset, built rnx-pg and rnx-jupyter,
and the pinned Jupyter notebook venv):

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project-assembly-probe
probes/jupyter-notebook/.venv/bin/python probes/package-assembly/run.py
```

The test-support binary calls the same private manifest parser, generator,
handoff serializer, fingerprint and capability check as the staged tool. There
is no Python copy of those rules. Python owns this fixture's Cargo calls and
private cluster/kernel lifecycle; product lock/build/run orchestration is gate 5.
It records an expected hash, not a product lock or a verified build receipt.

Generated sources remain under ignored `target/`. Release objects reuse the
accepted package-boundary probe's target directory. The fixture seeds Cargo.lock
from the adapter's accepted lockfile, permits resolution to add local packages,
and then builds locked/offline. Cargo owns compilation and the registry graph.
The output archives the actual generated manifest/main/map/lock and metadata.

Assertions: typed parameters survive quotes, SQL text, backslash and emoji;
mapped source and both native builders contribute to one result; trailing flags
are script arguments; exit 7 is preserved; a pending input interrupted while
supervising a child exits 130 and the child is reaped; old rnx-pg works without
maps and refuses mapped operation; a source-capable override works; tampering
refuses before script entry; native eval and session/reset work while file modules
remain refused; notebook restart loses bindings and retains the extensions.

The first interrupt fixture expected status 130 from a synchronous main that
immediately returned the supervisor's successful cancelled reply. It instead
returned status 0 with cancelled=true. That observation is retained separately.
The corrected fixture stays pending on an await, making driver interruption,
rather than successful completion, the event under test. No root change.

Fresh private clusters and temporary kernelspec directories are always removed.
The system PostgreSQL instance and user Jupyter directories are not touched.
Linux execution only. Windows probe compilation is reported separately; the
probe's non-Unix child-wait branch makes no product interruption promise.
