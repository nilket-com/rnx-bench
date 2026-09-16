# Package boundary probe

Step five, before a project manifest is designed. These are two independent
experiments, not a package manager or a change to rnx. The root repository is
unchanged. Results are in `results/package-boundary/`.

## Reproduce

From rnx-bench, with rnx checked out beside it:

```sh
cargo build --locked --offline --manifest-path probes/package-boundary/Cargo.toml
python3 probes/package-boundary/source.py
probes/jupyter-notebook/.venv/bin/python probes/package-boundary/native.py
probes/jupyter-notebook/.venv/bin/python probes/package-boundary/conditions.py
```

The native fixture requires the accepted PostgreSQL and Jupyter fixtures' tools,
including the built rnx-pg and rnx-jupyter binaries. It uses their private cluster
and kernelspec helpers; it never uses the system database or user kernelspec.
Generated projects, binaries and fixtures stay under ignored `target/`.
The scripts replace their own results. Run them sequentially.

## Source dependencies: a disk root, not a crate root

The Rust probe uses Rune 0.14.2's public SourceLoader API. A declared top-level
module name maps to an external directory; the remaining full item components
resolve below it. The directory's `mod.rn` is the fixture's entry convention,
not a proposed manifest field or finalized package layout. Nested candidates
keep `name/mod.rn` before `name.rn`.

Nine cases pass:

| Case | Observation |
| --- | --- |
| Two dependencies outside entry tree | Nested and inline modules return 1117 |
| Different process working directory | Same value, same physical sources |
| Rename consumer alias | Package files unchanged; self/super still work |
| Both nested candidates exist | mod.rn wins, changing value to 1127 |
| crate::marker inside dependency | Calls consumer's marker, not package's |
| Transitive mod other inside dependency | Searches dependency/other, not sibling mapping |
| Runtime fault two files deep | Actual dependency file, line 2 |
| Compile fault in dependency | Actual dependency file |
| Reference without mod declaration | Compilation refuses, loader is never called |

The trace retains every `root`, full item, candidate and selected path. Rune
passes the consumer entry as the root even for these nested loads. Item names
retain the consumer alias. This mapping gives packages independent filesystem
locations while their code remains nested under the consumer's Rune namespace.
It does not establish that separate semantic crate roots are impossible through
other Rune facilities.

Consequences for the draft: decide declaration/discovery rules, document what
`crate::` means, and specify transitive aliases explicitly. A single first-item
map does not give each dependency its own dependency map. No source rewriting,
synthetic declarations, transitive resolver or private Rune API was tested.

The probe deliberately lacks production source allowances, path validation,
Rune-compatible missing-module messages and package security rules. It reads
small controlled fixtures directly. Integration must preserve record 0050's
bounded loader and diagnostics; this probe does not replace it. Eval, sessions,
workers and config source-loading policy are unchanged.

## Native dependencies: generate, then let Cargo build

Hard-coded declarations name two adapters: a tiny local plain builder and the
accepted PostgreSQL lifecycle builder. The generator sorts names, creates Cargo
dependency aliases with explicit package names, and emits a wrapper calling the
public Extensions API. Reversing declaration order gives identical Cargo.toml
and main.rs bytes. A second sibling directory accepts the copied lockfile under
locked offline metadata resolution. This is deterministic generation for the
recorded layout, not a cross-machine reproducible-binary claim.

The accepted adapter lockfile seeds the first offline build; Cargo adds the
local packages, then a locked build succeeds. Run, eval, a session across reset,
and a notebook across kernel restart each execute the parameterized query plus
the local function and return 42. Both builder kinds are inputs known to the
fixture, not automatically inferred from a Rust crate. Names and builder paths
will need an explicit contract; arbitrary renaming of adapter help is not proven.

A deliberate source edit changes the local function from 2 to 3. The next locked
build changes the executable and result while Cargo.lock stays byte-identical.
Restoring the source restores this build's original executable hash. Therefore
Cargo.lock plus the generated manifest hash is insufficient for path dependencies:
source identities must also cover rnx and local adapters. Artifact reproducibility
also depends on toolchain, target, features and build environment.

The override uses an existing rnx-pg, records its hash, executes a query returning
40, and refuses a modified copy before launch. Hash identity says nothing about
which modules it provides. This simple check is not an atomic verify-and-execute
mechanism and makes no TOCTOU guarantee.

The source loader and generated executable experiments are separate. The current
rnx executable has not acquired mapped-source loading. Connecting the two requires
a product design; neither manifest syntax nor package commands are selected here.

## Scope and provenance

Linux execution only. There is no timing claim. Native assembly is an ordinary
CLI/worker executable, not a generated standalone HTTP server; how a server host
is declared remains open. Local sources only: registry fetching, Git resolution,
version conflicts, publishing and dependency cycles were not tested.

`conditions.json` records compiler, source heads, script/source hashes, Python
versions and dependency additions against the accepted locks. `*-graph.json`
records Cargo's resolved package/version/source/checksum-lock companions and
license declarations (not a substitute for license texts). This is a source-only
probe; existing root and adapter THIRD-PARTY-NOTICES.md cover their accepted graphs.
The graph comparison names any version differences rather than implying the root
graph was changed. The generated local fixture is recorded in the evidence.

The source-only compiler probe resolved five registry version differences from
the root lock (cc, cfg-if, smallvec, zerocopy and zerocopy-derive); their declared
licenses are in source-graph.json. Rune itself remains exactly 0.14.2. Native
assembly adds only the generated app and local fixture to the accepted adapter
package/version set; it introduces no registry version differences.
