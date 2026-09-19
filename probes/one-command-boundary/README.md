# 0067 gate 1: one command, source coordinates and wire boundaries

This is an isolated prototype, not the product implementation. `prepare.py`
clones rnx `9570b25`, makes the management crate a library with a narrow dispatch,
and builds a stock binary by **real `cargo install --git --rev ... rnx --locked`**
from a private fixture origin. Only `rnx` is installed. No payload is embedded.
The fixture repository URL is deliberately substituted in the private manifest.

The actual REPL protocol, startup probe and project Git-source workflow are not
ported here. `--probe-dep` is a small gate-only coordinate decision driver: it
prints a notice/refusal and, only with `--consent`, invokes real Cargo acquisition.
It does not claim binding preservation, cancellation, shell quoting for arbitrary
paths, recovery hint availability, or a completed `:dep` transition. Those remain
gate 2. The new wire readers are also isolated from product dispatch.

## Reproduce

Linux needs Rust/Cargo, Git, Python 3.14, `nm`, strace and bubblewrap with user/network
namespaces. The normal Cargo registry cache is used read-only by convention through
a symlink (Cargo can populate it); the Cargo Git cache, fixture origin, install
roots and build targets are private. Initial Cargo installation may populate
registry dependencies. Path build controls run offline with networking disabled.

From the bench root, with `probes/one-command-boundary/target` absent:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/one-command-boundary/prepare.py
python3 probes/one-command-boundary/coordinates.py
python3 probes/one-command-boundary/boundary.py
python3 probes/one-command-boundary/evidence_controls.py
python3 probes/one-command-boundary/build_network.py
python3 probes/one-command-boundary/generated.py
python3 probes/one-command-boundary/schema_setup.py
python3 probes/one-command-boundary/vectors.py
python3 probes/one-command-boundary/checks.py
python3 probes/one-command-boundary/archive.py
```

Use an isolated bench worktree for reruns: results are written under
`results/one-command-boundary-0067` and `commands.jsonl` appends. Move the entire
prior target and results aside, rather than deleting selected nested directories.
`RNX_PROBE_RESUME=1 coordinates.py` is only the documented continuation after the
retained Cargo-wording assertion failure, not the normal replay command.
`--record-vectors` is a maintainer-only schema change operation; ordinary reruns
compare the checked-in vectors and their digests without updating them.

`fixture.bundle`, `unpublished.bundle` and `style-check.bundle` preserve the actual measured fixture
commits and the plan ancestor, with published rnx `94f5f3f` as prerequisite.
Fetch their heads into an isolated rnx clone if `9570b25` is unavailable locally.
`prototype.patch` is the first fixture revision against that plan. The scripts
recreate both fixture revisions; their commit IDs/time and local URL can differ
on a rerun. Fixed schema vectors use `/fixture`, never these dynamic paths. The archived
coordinate matrix precedes one equivalent build-script lint correction; the
separate style-check install verifies the corrected source. Fresh runs already
use that corrected template; `style_check.py` records the historical correction
and is not part of a fresh replay.

## Coordinate controls

Fourteen classifications are measured on actual installed binaries: fresh Git,
second Git revision, cached first revision, clean pushed path, hostile-clean-filter
dirty bytes (where `git diff` lies), staged addition, staged deletion, chmod with
mtime unchanged, restored clean, clean unpushed, unrelated enclosing repository,
no Git administration, missing Git, and a genuine Cargo checkout with its fetched
object evidence removed. Acquired means the package is clean, under the canonical
Cargo checkout root, linked to a DB below Cargo's Git DB directory, and the DB's
local FETCH_HEAD records the configured URL with a fetched object containing the
revision in its ancestry. This is local evidence in trusted Cargo storage, not
remote availability or a defense against somebody forging Cargo's administration.
Missing or unrecognized evidence is unverified. Different Cargo acquisition
implementations may therefore produce unverified without blocking use.

All dirty/unknown requests (even with consent supplied) and all descriptions and
declines run with a positive-controlled Cargo trap and network tracing in an
isolated network namespace. No scratch request directory is created. The pushed
path build succeeds at consented acquisition without an override; the unpushed
build fails only after consent with Cargo's actual missing-revspec diagnostic.
A separate traced stock path installation has no Internet socket calls.

Cargo mtime rebuild tracking cannot see chmod alone. The prototype's stock build
script deliberately registers a missing private OUT_DIR marker, forcing a fresh
coordinate scan on each stock build. It writes generated constants only when
changed. This has a build-time cost; no runtime scan is introduced. Defaults-off
consumers return before discovery. A forced release rebuild with Git trapped
proves that path, in addition to graph and symbol checks.

## Crate and document boundaries

The optional path dependency needs root `[workspace] exclude = ["tools/project"]`
so the existing independent tool workspace does not become a conflicting second
workspace root. The internal graph contains no rnx dependency. The runner-only
consumer graph and symbols omit management. Both adapters disable rnx defaults;
the server already did so. The real generated combined wrapper disables defaults
and explicitly enables allocation accounting and project sources. Its resolved
feature graph is inspected; that combined wrapper is not compiled in this gate.
The accepted earlier Git-source feasibility probe covers actual native builds;
gates 3 and 4 will exercise this implementation's native product workflow.

Fixed versions: declaration 2, lock 4, receipt 5, identity 3/generator 3, ready 3.
Manifest/source-map format 1 and old path lock 3, receipt 4, identity 2/generator 2,
ready 2 keep their original readers. New declarations select exactly path OR
Git URL plus full lowercase 40-hex revision. This prototype's Git URL scope is
HTTPS plus absolute `file:///` fixture origins. Pure Rune sources remain paths.

Identity retains exact wrapper/main, Cargo lock digest, toolchain, profile,
features, target, Cargo/Rustup/cache homes, external inputs with absent candidates,
and path-native associations/fingerprints. Git associations carry package ID,
name, URL, revision, canonical checkout and repository-relative manifest. They
replace only those source trees' content fingerprints; overlapping path/Git
ownership and Git-owned entries in the external audit are rejected. Mixed sources
have a fixed vector. Canonical JSON has serde declaration-field order, no trailing
newline, ordered collections and strict duplicate/unknown-field refusal. BLAKE3
of those bytes remains the key.

These are **shape and binding readers**, not proof of live Cargo or filesystem
truth. Relative declaration paths are resolved by the later workflow, not this
schema-only driver. No new envelope is selected by product commands here.

The fixture root lockfile was regenerated offline when adding the optional
management crate. It contains incidental compatible dependency updates; this
prototype makes no default-graph or matched-startup claim. The product port should
retain unrelated pins when adding its management dependencies.
