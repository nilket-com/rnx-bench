# 0065 gate 1: reader and encoding contract

Run from rnx-bench with the matching rnx implementation checkout alongside it.
The accepted hash-choice probe supplies an independent whole-input BLAKE3 API
for Python-side framing. Build it first if its ignored target is absent:

```sh
python3 probes/hash-choice/prepare.py
cargo build --offline --locked --release --manifest-path probes/hash-choice/Cargo.toml
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-encoding/checks.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-encoding/vectors.py --check
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-encoding/check.py
```

If the old inventory input fixture is absent, reproduce the accepted hash-choice
prerequisites as described there. The reference executable's hash-reference mode
only hashes the supplied bytes; it does not run Polars. `vectors.py --check`
compares the checked-in vectors without editing them; omitting --check regenerates
them explicitly.

The checks driver builds the actual project's existing private assembly-probe
binary with test-support after running fmt, strict all-target clippy and suites
serially in both feature configurations, then notices. It verifies unchanged root
scope, unchanged manifest/source-map formats, absence of Rayon/mmap in the resolved
BLAKE3 features, and exact correspondence of frozen legacy reader function bodies
to 7cd3205 (only the test-hook qualification differs).

The reader driver calls that binary's test-only fingerprint-v1/v2 entry points,
not a replacement reader in Python. It checks 37 paired filesystem cases, matching
semantic records and exact refusal messages. Python hashes legacy file contents
with hashlib and frames BLAKE3 trees independently against the accepted one-shot
reference. Files are created under a temporary directory and removed on exit.
Every subprocess has a five-second bound; FIFOs must refuse without hanging.

Cases include empty sources and files, all three sides of the 16 KiB boundary,
allowances, executable mode, quotes/Unicode/nesting, dirty working-tree bytes,
ignored/untracked files, missing tracked files, symlink roots/index/components,
FIFOs, non-Unicode paths, gitlinks and unmerged index entries. Source-vs-single
read accounting and deterministic mid-read EOF/growth are additionally covered
by the unit suite, as are independent static vectors, duplicate names and all
six current document versions (including mixed/unknown field refusals).

One fixture correction is recorded: replacing a tracked directory with a symlink
first triggered Git's untracked refusal. Adding that replacement path to the
fixture's ignore rules reaches the intended tracked-component check. Both readers
refuse it; no product rule was relaxed.

These drivers overwrite their own result logs and JSON. Save/restore published
results around a reviewer rerun. No user store, cache or project is changed, and
there is no performance measurement here. Workflow upgrades, installed-runtime
migration, nested-root reuse and final timing remain later gates.
