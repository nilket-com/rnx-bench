# Assembly identity: measured findings before a shared-cache design

The probe passes, with two counterexamples that the next record must address.
The current product is unchanged at rnx 83398d9. Commands and limitations are in
probes/assembly-identity/README.md. Every measured fixture's source, wrapper,
Cargo lock and project lock is archived alongside its identity projections.

## Findings

| Change | Raw wrapper | Candidate assembly projection | Observation |
| --- | --- | --- | --- |
| Different project directory and Rune script; same absolute native roots | same | same | Different project locks; same constant output and executable hash in this fixture |
| Relative spelling of the same native roots | different | same after canonicalization | Same output and executable hash in this fixture |
| Relocated identical native trees, constant adapter | different | same after assigning native-parent role too | Same output; location-preserving key intentionally differs |
| Relocated identical trees using CARGO_MANIFEST_DIR | different | same after native-parent role | Different output: each adapter's compiled native directory |
| Same native roots, build script embeds OUT_DIR | same | same, including location-preserving candidate | Different output: each project's build directory |
| Extension alias change | same manifest, changed main | different | New registration name cannot alias old assembly |
| Native content change | same | different | Cargo lock unchanged; tree fingerprint changes |
| Allowed ancestor config addition | same | different | External input inventory changes |

The real Polars control independently confirms the first row's wrapper/graph
claim: two different application scripts and directories, with the same absolute
rnx and adapter roots, produce identical generated Cargo.toml, main.rs and
rnx.Cargo.lock, but different project locks. It is a lock-only control and makes
no claim about two separately compiled Polars executables being byte-identical.

The earlier broad claim that different project locations necessarily produce
different wrapper bytes was too strong. Absolute native dependency paths stay
the same if those dependencies stay in place. Lexical relative paths and actual
native relocation are separate cases. Normalizing the former can remove noise;
normalizing the latter can discard an observable build input.

## Consequence for a useful first cache

A project-independent assembly key is viable, but is not automatically proof of
behavioural equivalence to a new build in every project's directory. Even an
unchanged path dependency can embed Cargo's OUT_DIR; the exact same generated
manifest, main and Cargo lock do not settle this. No key-only tweak fixes an
input that compilation can observe but the key deliberately excludes.

A focused next draft could choose a cache-owned assembly/build directory with
stable lifetime, retain canonical native source locations initially, and make
project scripts/source mounts consumers of that assembly rather than compilation
inputs. Reusing an assembly would then mean reusing a build produced in that
specified location, not emulating a fresh per-project build. Outputs that embed
paths to build directories need those directories retained, or a stated adapter
contract that permits their removal. Merely keeping the executable is not enough
for arbitrary trusted adapters.

That still requires explicit decisions: cache scope and permissions, key fields,
Cargo configuration lookup at the cache build location, publication/concurrency,
content and metadata verification, corruption recovery and rebuild/eviction.
Existing trusted build scripts can observe environment and external files; 0057
already excludes hermeticity. A shared-cache design must state that limitation
rather than expand it silently. Cross-location native-tree sharing can be deferred
without losing sharing between projects using the same installed adapters.

No cache is implemented here, and there is no promise that a second dependency
request is instant. These results select the questions the draft must answer.
Toolchain, target, features and profile belong in a production key; this probe
records the current ones but does not claim to have executed a cross-platform or
alternate-toolchain matrix.

## Startup qualification for the later session transition

Source review: src/lib.rs dispatches project-source-version before building the
context/installing extensions. tools/project/src/handshake.rs checks that reply
with bounded streams and a deadline. It proves the command/version is supported,
not that extension builders, configuration or session startup succeed. A future
:dep transition cannot treat this handshake alone as a readiness guarantee.
Even a separate successful startup probe would not make the later exec atomic
against environmental failure; that contract remains a later decision.

## Validation and provenance

The eleven tiny cases (eight builds and three lock-only invalidation controls)
pass, as does the real two-project Polars control. All Cargo operations are
explicit, locked for build and offline. The fixtures run no database or kernel,
create no user cache or history, and all children complete before temporary roots
are removed. The source inventory and root Git status remain unchanged.

The initial projection's external-list ordering error is retained separately.
It is a fixture correction, not a discarded product result. The role-adjusted
relocation candidates are explicit files, so the equal-key counterexamples can
be checked directly rather than inferred from a summary hash.
