# Cargo Git runtime probe before rewriting 0067

This is an isolated probe, not implementation of the committed 0067 payload
plan. That plan remains unpushed and unchanged. Root production files, manifests,
locks and user installations are not modified.

The actual published source is pinned to rnx
`94f5f3f98ba756c5ab5293d1e5132c7fd7b52d32` at
`https://github.com/nilket-com/rnx`. The root and two nested independent adapter
workspaces are unmodified. The saved Cargo.lock pins the registry graph too.
First acquisition uses network; registry downloads already on this machine are
shared through a symlink, but the Git cache and assembly targets are private.

Run from rnx-bench. Preserve the checked-in results before a rerun. All paths
below `probes/cargo-git-runtime/target` are fixture-owned; remove that whole target
before a clean rerun (including the coordinate repositories, installs, consumer
outputs, ready documents and trap logs). Keep the saved `results/.../Cargo.lock`
as the graph seed. Python needs no third-party modules. Rust/Cargo, Git, strace
and bubblewrap with unprivileged network namespaces are prerequisites.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/prepare.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/coordinates.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/unpublished.py
rustc --edition 2024 -O probes/cargo-git-runtime/src/verify.rs \
  -o probes/cargo-git-runtime/target/raw-verify
# assemblies.py creates the developer checkout before building. For a fresh
# sequential rerun, verification belongs AFTER assemblies.py completes.
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/assemblies.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/verify.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/selection.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cargo-git-runtime/offline.py
```

`prepare.py` resolves actual Cargo Git packages, asserts both adapter edges point
at the same rnx package ID, and builds an isolated copy of the existing inventory
helper. Its exact two-file delta is retained in `tool.patch`. Audit-only mode
skips native tree reads for Git sources but keeps package associations, canonical
roots, ancestor/workspace/config candidates and the real external-input audit.
Path mode uses the unchanged product fingerprints. This instrumentation is not a
new product parser or storage format.

`coordinates.py` adds an independent tiny package with a build script to a clone
of the real repository. The fixture commit is saved as a Git bundle, incremental
against the published baseline. It tests `cargo install --path` and `--git`,
raw-byte dirty builds despite a clean filter, and an unpacked non-Git package
inside an unrelated enclosing repository. The latter must produce unknown,
not the enclosing repository's revision. The explicit dirty/unknown refusal is
candidate policy. This does not claim production rnx currently records Git
coordinates, or that every distribution contains Git administration.

`assemblies.py` builds an actual combined Polars/PostgreSQL wrapper twice, once
with Git coordinates and once from a private developer checkout. Candidate
identity documents retain the exact wrapper/main, locked Cargo graph digest,
compiler/toolchain, target, profile, features, build configuration, Cargo/Rustup
homes, cache root, canonical source locations and audited external inputs.
Application scripts are excluded. Git-native content trees are replaced by
package-associated Git coordinates; path-native trees keep product BLAKE3
fingerprints. Neither policy asserts a hermetic build. Two separate consumer
receipts reference each assembly and execute different scripts; both assemblies
also run the real CSV/Polars/Parquet pipeline. PostgreSQL is compiled and its
registration evaluated, not queried against a server in this probe.

`offline.py` validates and attaches those candidate receipts in a network-isolated
bubblewrap process, with compiler/Cargo traps and a positive trap control. It
also runs Cargo's cached resolution offline and requires an empty Git cache to
refuse offline. This is a source/assembly-key feasibility demonstration, NOT
production cache publication/concurrency/receipt compatibility. Current
rnx-project still accepts path declarations only. The retained identity is not
regenerated from arbitrary user manifests during attachment; it is the fixed
probe request. A rewritten record must integrate resolution and all existing
cache ownership checks before claiming product support.

`verify.py` includes static mutation controls and 160 pinned, interleaved samples
(two repeats, twenty samples for each of four operations). The native Rust
verifier uses raw `ls-tree` entries and `hash-object --no-filters` in batches of
64, plus HEAD, index path set, modes, regular-file/ancestor checks and an untracked
listing. It exempts only Cargo's `.cargo-ok` marker. It does not run status/diff
or trust index stat caches. Object fsck is measured separately. No atomic
snapshot or hostile-concurrent-writer guarantee is claimed; ignored build data,
external environment, Git administration and registry contents are not made
hermetic by source coordinates. These are process-level verification timings,
not product startup numbers and not predictions for a future optimized reader.

The selected draft policy is deliberately not changed by this probe. The numbers
allow choosing between trusting Cargo-managed checkout content by default and
full revalidation on launch, or validation at attachment/build with an explicit
verify operation. Every choice must state its mutation coverage.

All command failures are retained in commands.jsonl. Preliminary artifacts are
named separately. The exploratory run corrected: an initially misplaced target
(later relocated; metadata rerun), an offline fetch of an uncached local Git
fixture, an enclosing-repository provenance mistake, and an omitted `run` word
in the first script invocation. Python verification timings are preliminary;
the final comparison uses the compiled Rust reader. Initial README mutation
controls overlapped the first Git build; after restoring and verifying the
checkout, all three Git-native packages were cleaned and rebuilt before the
accepted pipeline and offline runs. The rebuild and original build receipts are
both retained. Sequential reruns above avoid that overlap.
