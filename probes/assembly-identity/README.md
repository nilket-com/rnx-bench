# Assembly identity probe before the shared-cache record

Run from rnx-bench with the accepted ordinary rnx-project release alongside:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/assembly-identity/check.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/assembly-identity/real_pair.py
```

Both scripts use temporary directories, the real project lock/build commands,
and offline Cargo. No root source changes, cache service, manifest change or
production identity algorithm is introduced. Preserve the tracked evidence before
rerunning. The tool hash and root commit are in conditions.json. The real Polars
control locks twice but does not rebuild the large adapter. The tiny native
fixture has no downloaded dependencies and is compiled independently per case.

check.py builds a deliberately tiny API-compatible runtime and native adapter.
It is an assembly test, not a substitute for Rune evaluation. The product tool
provides generated manifests, main, locked Cargo graph, native Git working-tree
fingerprints and external-input inventories. Every case archives those files and
the exact fixture sources. Driver output records executable hashes and stdout.
Sources are preserved, not merely identified by hashes.

Two candidate projections are diagnostic only:

- A location-preserving projection canonicalizes wrapper dependency paths and
  gives the invocation directory's external candidates an application role.
- A content projection replaces native roots with their actual tree digests,
  keeps package associations and external candidates, and similarly labels the
  application root. In the relocation fixture, the shared native parent also
  requires a role; both the naive and parent-adjusted projections are archived.

These projections are specific to this controlled layout. String replacement is
not proposed as a production path normalizer. A production algorithm must resolve
and encode structured paths, preserve association/alias distinctions, establish
configuration semantics and refuse unaccounted inputs. The probe does not test a
version solver, alternate compiler/target, malicious build script or shared-cache
publication policy. No launch-speed or cache-hit measurement is claimed.

Cases cover distinct project sources at the same absolute native roots, relative
spelling of those same roots, relocated byte-identical native roots, a native
compile-time path observation, a build script observing OUT_DIR at unchanged
native roots, and real name/content/config changes that must miss a key. The
positive relocation case is a path-independent constant; the negative cases
intentionally make compilation location observable through public Rust/Cargo
facilities. Neither is a defect in the existing non-hermetic project tool.

The preliminary location projection failed to re-sort its external candidate
list after replacing the application path. The saved preliminary-ordering.log
records that fixture failure. Sorting the projected list fixes it; production
source and inventory logic were not changed. All final assertions pass.
