# 0064 gate 1: an independent installed runtime

Isolated experiment against rnx plan commit `b4510d4`. No production source,
manifest, lockfile, dependency, public API or protocol version changes. The
three-file tool patch is archived in `prototype.patch`; `runtime_probe.rs` is its
new module. Everything else comes from the exact base tree, including the native
fingerprinter, catalogue, inventory, assembly/cache, startup probe and root CLI.

Run from `rnx-bench` with a **fresh** `probes/runtime-install/target`:

```sh
python3 probes/runtime-install/setup.py
python3 probes/runtime-install/index.py
python3 probes/runtime-install/journey.py
python3 probes/runtime-install/checks.py
```

The setup requires the recorded root commit to be available. Cargo/Rust/Git and
cached pinned registry sources must be installed, as must PostgreSQL 18's server
tools used by the existing private-cluster helper. Builds use `--locked --offline`;
this is a cold **assembly target**, not a download benchmark. Two real Polars
assemblies (alone and with PostgreSQL) consume several GB and a few minutes.
No user installation, cache, state directory or kernelspec is used. The first
launcher/tool builds and the installed assemblies use separate fresh targets.

Results go to `results/runtime-install-0064/`. Move that directory aside before
rerunning if keeping previous evidence: the inherited journey appends its phase
journal. Remove only the generated `target` between full runs; it includes the
private installation/cache, two renamed fixture repositories, and build targets.
Never rename the user's checkout. The real original fixture is renamed to
`target/unavailable-original` before the first installed assembly build and stays
there through inspection.

`index.py` has eight groups: dirty bytes/modes/odd names, linked worktree with both
source routes renamed, hostile Git/filter/CRLF with a positive filter control,
and five inherited refusals (symlink, FIFO, untracked, backslash, non-Unicode).
It reads every installed staged blob independently and compares its raw bytes.

`journey.py` installs the full patched snapshot and locks equal native recipes at
the original and installed locations against the **same** identity-only cache.
It then renames the source, uses an entirely separate empty assembly cache, and
reuses `probes/session-dogfood/check.py` with exactly one substitution: its runtime
root comes from `RNX_INSTALLED_RUNTIME`. That variable belongs solely to the
Python harness; no product reads it. `RNX_DEP_RUNTIME` is absent. The driver
provenance records the original and effective hashes and exact replacement.
The ordinary stock binary and tool are copied outside the renamed source before
installation. A real installation notice is asserted in both stock transcripts.

The four real journeys cover first stock Polars build, second stock attachment
with compilation trapped, absolute mixed Polars/Postgres project and relative
mixed project attachment. They exercise decline, binding loss, history, restart
numbering, working-directory ownership, bounded preview, Parquet round-trip,
catchable error recovery, private-cluster typed queries, and scratch reopening.
Then the probe inspects actual generated manifests, wrapper mains, native lock
inventories and full Cargo metadata for source-location paths.

## Scope of this experiment

`runtime-probe install` is a probe-only command. It accepts arbitrary fingerprintable
fixture roots for the index controls, directly writes its private installation
and current documents, and requires an absent destination. It is **not** the
product installer. Atomic publication, concurrency, interrupted installation,
managed-storage defenses, static Cargo escape checks, robust document validation,
reinstall/selection commands and the complete discovery/refusal matrix belong to
later gates. The UTC helper invokes `date` here; this does not add a product
runtime dependency decision. Git remains required by the unchanged inventory.

Git environment sanitation happens in child commands, never through process-wide
environment mutation. Index objects use `hash-object --no-filters`; index entries
use explicit cacheinfo. Dirty provenance compares raw HEAD tree/object identities,
not `git diff` or `status`, which can invoke clean filters. The hostile-filter
control caught that mistake in the first prototype and passed after replacement.

A source hash is not source preservation: the patch plus the retained base commit
reconstructs every installed file, checked by `checks.py`. Installation provenance
records the old source path deliberately, outside the identity/source/build tree.
Path-exclusion checks apply to build inputs, not that provenance. Equal sources
at distinct canonical native roots have different assembly keys, as 0061 requires.
No assembly promotion, same-binary promise, latency claim or mixed-version
compatibility claim is made.

The source-reconstruction check initially ran `git apply` inside the bench's
repository without initializing its disposable base repository; its exact-file
assertion caught the resulting no-op. Initial path inspection also caught a
fixture false positive: `/home/me/work/rnx` is a textual prefix of `rnx-bench`.
Inspection now uses path delimiters and separately checks every local Cargo
manifest's ancestry. Neither required changing the installed prototype or rerunning
the cold builds. Their successful journey outputs were retained unchanged.

For a checks-only rerun, remove the generated `target/patch-check` directory first;
`setup.py` also requires `target/patch-base` to be absent (a full fresh-target run
handles both). Run checks after the journey has finished: the inherited one-second
handshake test can report timeout instead of its expected oversized-reply error
under concurrent build load. No test deadline is changed here.
