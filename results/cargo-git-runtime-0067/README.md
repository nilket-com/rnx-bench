# Cargo Git runtime probe — 0067 direction evidence

The repository topology is usable as it stands. Cargo discovered and built the
root and both independent nested adapter packages at the same published Git
revision. No root source or manifest changes were needed. This supports rewriting
0067 around Cargo-managed sources; it does not implement that product design or
choose the checkout-verification policy.

## Sources and discovery

Baseline: `94f5f3f98ba756c5ab5293d1e5132c7fd7b52d32`, acquired from `https://github.com/nilket-com/rnx` with a private Cargo Git cache. All three
package IDs have that Git source and both adapter `../..` edges resolve to the
same root package. `metadata.json`, Cargo.toml, main.rs and Cargo.lock preserve
the resolved graph and wrapper. This includes the unchanged empty-workspace
manifests; there is no package-discovery workaround.

Two real combined executables were compiled. Both run the checked-in tiny CSV,
filter/group/sum, Parquet write/read and preview pipeline. PostgreSQL registration
is evaluated, but this probe does not run a PostgreSQL server/query. Git cold
target build: 264.11 s; developer-path cold target build:
263.93 s. Registry downloads were already available.
The first Git build is preserved; a subsequent native-package rebuild after the
static mutation controls supplies the accepted executable, with its own receipt.
These are setup observations, not matched performance comparisons.

## Coordinates and acquisition

The build-script fixture, committed on top of the real repository and archived
as coordinate-fixture.bundle, observes the exact revision under both
`cargo install --path` and `--git`. Dirty working bytes are flagged even behind a
hostile clean filter; candidate `--require-clean` refuses those binaries with a
path-override instruction. A copy without its own Git administration reports
unknown/dirty, including when an unrelated outer repository exists. Source-root
anchoring is necessary. The fixture does not alter stock rnx or claim the current
binary already records coordinates. The repository URL is a configured source
coordinate, not something the fixture infers as trustworthy from arbitrary Git
remote settings.

The real unpushed plan revision could not be acquired from the configured remote:
Cargo names the missing revision amid network-looking errors. A clean local
commit is not proof of remote availability. A rewritten record needs a usable
refusal for unpublished/unknown/dirty builds, not merely a dirty bit.

## Reuse and developer override

The two Git consumer requests pin the same complete wrapper and source revision
but have different scripts. They attach to one candidate key and produce 42 and
99. The two path consumers do the same through another key in the same private
cache. The source selector models `RNX_DEP_RUNTIME` as explicit precedence and
refuses invalid values rather than falling back. Path fingerprints come from the
current tool's implementation. A same-size restored-mtime path edit refuses;
a changed Git revision request refuses; restoration permits attachment again.

All four attachments pass inside a network-disabled namespace. A positive
network control fails as expected, compiler/Cargo traps have a positive control,
and the child syscall trace records zero compiler/Cargo execs and zero INET
syscalls. Cargo itself also resolves the saved graph offline with its Git cache
present and refuses with an empty Git cache. This is attachment with compilation
trapped, not a claim inferred from latency.

The candidate identity retains wrapper/main bytes, locked graph digest,
compiler/toolchain, target, profile/features/configuration, Cargo/Rustup homes,
cache root, audited external inputs and canonical checkout locations. Package
associations remain explicit. Only the Git-native content-tree representation
becomes source coordinates. Relocating a Cargo checkout is not asserted to be
equivalent. The path case retains its existing full native-tree fingerprints.

**Scope:** this is a fixed-request candidate harness, not a production cache
format, parser, lock command or concurrent publisher. The existing helper is
copied from the baseline, with its exact audit-only/digest delta in tool.patch.
Its real external audit is retained; only Git tree fingerprinting is bypassed
there. Attachment uses an additional raw-object verification for this probe,
not a newly accepted default policy. Integration must keep 0061's context,
publication, locking, artifact verification and ownership rules.

## Checkout verification has a measurable price

The actual checkout contains 448 tracked files, 6,755,054
bytes. Cargo adds an untracked `.cargo-ok` marker; the existing path fingerprinter
refuses it. A Git-source policy must account for that marker explicitly rather
than silently treating the checkout as an ordinary path package.

Cargo metadata accepts a same-size restored-mtime tracked-file edit. Both the
raw verifier and the existing path fingerprint controls detect changed bytes.
Raw checks also refuse a hostile-filter-hidden edit, an untracked file and an
executable-mode change. They compare `ls-tree` entries against unfiltered Git
blob identities, not `git status` or an index stat cache.

Pinned process wall time, two interleaved repeats, 20 samples per operation per
repeat, all 160 samples retained in verification.json:

| Operation | Median |
| --- | ---: |
| Read HEAD only (not content verification) | 1.97 ms |
| Compiled raw-blob verifier, including Git subprocesses | 25.95 ms |
| Separate full object-database fsck | 90.02 ms |
| Existing BLAKE3 path fingerprint of the equivalent source | 11.28 ms |

The raw verifier uses batches of 64 files, as the installation provenance path
does. It is an isolated correctness candidate, not a claim of optimal hash or
process batching. Fsck includes the actual fetched object database and is not
included in the raw-verifier number. Preliminary Python-reader timings are saved
separately and are not the native-reader result. These are not everyday-launch
numbers. Source-coordinate identity does not eliminate the cost unless the
coverage policy deliberately trusts cached source content on that path.

Working-tree checks are non-atomic. They do not turn ignored data, build scripts,
registry packages, ambient inputs or mutable Git administration into a hermetic
build. A future policy must distinguish launch, attachment/build and explicit
verification, and state what edits can go undetected under each.

## Disposition

No package-discovery stop remains. No change to the current root manifests was
needed. The developer path and Cargo Git source are demonstrably usable side by
side; second consumers reuse without network or compilation. Before rewriting
0067, choose the verification policy and the clean-but-unpublished/unknown build
behavior. Preserve the assembly identity inputs and canonical-path qualification.
Do not claim either a free verification win or a lockfile-plus-wrapper-only key.

The payload plan `d1b4c19` remains unchanged and unpushed. No runtime installation,
user assembly/runtime cache, kernelspec or original Git checkout was modified by this probe. See the
probe README for exact rerun order, preserved fixture corrections and scope.
