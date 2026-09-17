# 0061 gate 2: assembly identity matrix

The product's new private cache_identity module is tested directly from an isolated
probe binary. Existing product commands still use their local assembly workflow;
this does not implement a shared cache hit, lock format 2 or receipt v3.

From rnx-bench with rnx alongside, an installed Rust toolchain, Git, Python 3 and
the accepted tool release dependency cache:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/cache-identity/build.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/cache-identity/check.py
```

Preserve results/cache-identity-0061 before rerunning. build.py copies the actual
product modules, checks their hashes after formatting, adds only the private
probe binary, and builds/lints it with the unchanged lockfile. The gate-one
context guard and configuration policy remain prototype orchestration. The key,
canonical serializer, shape validation and generator canonicalization come from
the product modules, not a Python reimplementation. Each emitted key is checked
against SHA-256 of the module's actual canonical bytes, and Rust decode/encode
round-trips it. Reversing all inventory collections gives identical bytes/key.

check.py uses real Cargo metadata and native Git working-tree inventories. The
runtime and adapter are deliberately small, generated-wrapper-compatible Rust
fixtures, not Rune evaluation. Every case archives their actual sources, Cargo
lock, metadata, wrapper, context and identity. The native declarations resolve
from real project manifests; source mounts are valid directories with their own
manifest/module. Different scripts, mounts, renamed mounts and edited mounted
source retain the native key. Project source validation remains the product
workflow's separate responsibility; the identity helper does not waive it.

Same canonical native paths converge from absolute and relative spellings.
A symlink to the cache root converges on its canonical selection. Relocated native
roots miss even with identical bytes. Registration name, builder function, hook,
native content, runtime content, a resolved local dependency, actual native
feature activation, explicit installed toolchain selection, configuration presence,
cache root and Cargo home each miss. Restoring the original inputs restores the
original key. Eight cases also compile/run using the exact generated wrapper.

Target/profile and arbitrary selected-feature-string changes are synthetic unit
tests against the key document, not executed cross-target builds. The real feature
case changes a native crate's default features and compiles it. The explicit
RUSTUP_TOOLCHAIN case selects the same installed compiler explicitly: it proves
selection presence participates, not a second compiler installation. Changed
Cargo graph and native contents are observed from real files, not fabricated
hash differences.

The library tests also pin strict canonical decoding, unknown/duplicate fields,
unsupported versions, invalid digests, duplicate collections, missing native
associations, path refusal and document/shared-byte limits. Decoder validity does
not authenticate filesystem observations; later attachment/launch must rebuild
and compare the authoritative live identity.

No root API, dependencies, kernel or adapters change. Product workflow regression
is deferred to integration, while existing tool suites, strict Clippy, formatting,
notices and Windows type-check run here. Windows execution is not claimed.
