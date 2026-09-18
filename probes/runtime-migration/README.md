# 0065 gate 3: authenticate retained runtimes before migration

Run from rnx-bench with rnx alongside it, on Linux. This uses private fixture
stores/caches only. The user's old installation store is never read or modified.
Prerequisites: the accepted native-inventory fixture's frozen 7cd3205 tool and
`fixed-rnx`, the existing Jupyter fixture venv and built `rnx-jupyter`, and the
PostgreSQL server tools used by the established private-cluster fixture.

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --release --bin rnx-project
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/checks.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/check.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/precommit.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/replay.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/setup.py
PYTHONDONTWRITEBYTECODE=1 probes/jupyter-notebook/.venv/bin/python probes/runtime-migration/journey.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/scratch.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/runtime-migration/collect.py
```

Keep feature builds serial in the same target directory. Preserve results before
reruns. `check.py` requires `target/matrix` absent; `replay.py` requires
`target/publication` absent. setup/journey/scratch are one sequence requiring
`target/real` absent initially. A failed journey may already have migrated and
published entries: restart the isolated sequence rather than pretending it is
still a fresh migration. Never remove a live cache/installation for cleanup.

The 30-case matrix creates genuine installation/current format 1 with the old
product, then renames the source checkout. It covers exact quoted recovery,
source/blob/metadata/ID/mixed/unknown corruption before repair, every publication
boundary, copy/Git interruption, late source/provenance edits, exact owned-path
eligibility, valid permission repair, provenance retention and repeat migration.
The precommit driver uses the old tool to select the old ID, then a current-tool
stock `:dep` refusal with a started HTTP future; its binding and original response
survive without consent, scratch creation or drain. The old selection is restored
to the fixture's new default afterwards.

The 90-case installer regression is the accepted publication driver with only
isolated paths and its bad-tool-digest field changed to `tool_blake3`. Generated
source is retained. The source/blob matrix correction makes the fixture's
read-only loose object writable only while injecting corruption, then restores
its original private read-only mode. Late-mutation pauses use the installer's
`.release` sidecar (not the project helper's remove-marker convention).

The full-source setup archives exactly rnx 7cd3205, gives it a private Git index
and commit, installs it with the old product, and physically renames the checkout
before the first build from an empty cache. An extra independently packaged
fixture adapter exposes one read of a retained OUT_DIR file. Its generated
Polars+fixture artifact is an actual old-key executable, not a copied replacement.

Before migration, journey.py starts that old session and writes a kernelspec
through the real installer naming the exact old-key artifact. It migrates, changes
the retained file, reads it through the still-live session, then starts the
previously written kernel and executes a cell through the old artifact. It also
runs the accepted four real :dep journeys from the migrated default with an empty
second cache: Polars, compiler-trapped second scratch, and absolute/relative
combined projects with a typed query on a private PostgreSQL cluster. The old
session still reads retained output afterwards. Kernels, workers and sessions are
reaped. The generated dogfood driver changes only runtime source and the installed
notice assertion; target/results come through its existing environment options.

scratch.py additionally creates an actual old-tool :dep scratch under the old
selected ID, reselects the new ID by repeating migration, reopens via its old
tool, then explicitly relocks using the new tool. Its declared old source path
remains: migrating the default never retargets old projects or scratches.

The new tool differs from the 7cd3205 snapshot specifically to implement migration.
Root launcher/runtime sources are unchanged; launcher/source skew remains an
unchecked compatibility policy, as in 0064. Times are individual observations,
not a latency gate or distributions. Old runtime/assembly entries stay on disk.

The collector validates the completed results, checks independent installed Git
objects, pins tool source/binary hashes, and saves the tool diff from a7c3f7d.
The signed root implementation commit preserves the measured source state.
