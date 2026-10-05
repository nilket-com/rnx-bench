# 0175 base tests

Fork commit `c6f57bd0`, parent `3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a`.
No candidate fast-path changes. The only runtime-source addition is a cfg(test)
reader for the exact exclusive i64 iterator bounds.

Run from the fork worktree with this Cargo.lock (the fork ignores Cargo.lock):

```sh
flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock \
  timeout --kill-after=5s 900s \
  cargo test --locked -p rune --all-targets --all-features
```

On x86_64 Linux, rustc 1.98.1 (48a229cea 2026-09-01), all targets passed:
604 unit tests and two integration tests (registration inventory and UI).
The log is retained alongside the dependency lock. These are semantic tests,
not performance samples. No deciding benchmark has run.

Preparation disclosures: a default-feature compile first failed on existing
workspace/fmt test modules; all-features is the plan's actual suite. During
snapshot development, Rust Iterator::size_hint was found not to inspect this
iterator's position; it was replaced by the test-only exact bounds reader.
A first full-suite replay failed because TypeInfo's Debug contained an ASLR
formatting-function address. The corrected unusual-unit fixture binds that
error to the exact empty TypeInfo and an empty chain, and records its stable
variant and type text. All other error Debug stays exact. Base goldens were
captured before any candidate edit; committed tests cannot regenerate them.

The goldens retain current-frame slots (these traced functions have no nested
script frames), ip/last_ip, exact iterator bounds, remaining permits for raw
units, and the temporary Some/terminal None. Opaque functions and other objects
are represented by their type rather than a heap/native code address. They do
not claim equality of allocator addresses or hidden native implementation state.
