# Hash choice before the 0065 format decision

This is a bench-only reader experiment against the accepted native-inventory
fixture at `c2af5de`, based on root `7cd3205`. No product identity, default,
installation, lock, receipt or cache entry changes.

Prerequisite: reproduce or retain `probes/native-inventory/target` and its results
from the accepted probe. Its shallow runtime is 443 tracked files / 6,988,177 bytes
and includes a complete renamed PostgreSQL adapter even at zero declarations.
This probe uses its real Polars artifact: 107,567,832 bytes. `prepare.py` checks
that artifact against the accepted digest. Do not modify those inputs.

From rnx-bench, with Cargo dependencies cached:

```sh
python3 probes/hash-choice/prepare.py
cargo build --offline --locked --release --manifest-path probes/hash-choice/Cargo.toml
cargo fmt --manifest-path probes/hash-choice/Cargo.toml -- --check
cargo clippy --offline --locked --all-targets --manifest-path probes/hash-choice/Cargo.toml -- -D warnings
cargo test --offline --locked --manifest-path probes/hash-choice/Cargo.toml
python3 probes/hash-choice/measure.py
```

Save/remove the prior `results/hash-choice-0065/samples.jsonl` before measuring
again; it refuses overwrite. `prepare.py` overwrites only this probe's generated
files, archives and input configuration. It does not remove the previous fixture
or need to rebuild its assemblies. Run builds/checks before timing, with no other
builds in progress. No full root suite is warranted by this bench-only change.

## What changes between candidates

`prepare.py` extracts the exact published `fingerprint.rs`, removing only test
hooks and its external test module, and adds a listed-path entry for isolating
traversal from Git. A minimal wire File struct has the same fields as the product.
The production reader's no-follow/nonblocking opens, metadata checks, allowances,
16 KiB buffer and final detection-byte check remain. This is not a replacement
implementation of those checks.

- `stock`: existing SHA-256 tree framing, feeding each source chunk to both the
  tree digest and the file digest. Reads the file once, hashes its bytes twice.
- `single`: retains SHA-256 per file, feeds the final raw 32-byte digest to the
  tree after the existing name/mode/length framing. Uses a probe-only domain tag.
- `blake`: the same single-pass structure, with BLAKE3 for both digests.
- `parallel`: BLAKE3 `update_rayon` with the existing 16 KiB read buffer.
- `large`: the parallel variant with a 1 MiB heap read buffer.
- `sha_large` / `blake_large`: single-threaded 1 MiB controls, to separate buffer
  effects from worker effects.

Internal copied wire fields still say `sha256` even in BLAKE3 rows. These are
**private probe outputs**, never accepted by the real tool, not a proposed
on-disk format. Any product change must version/label its digest algorithms and
handle existing runtime installations and cache entries explicitly.

Tree rows take the accepted list and execute the actual hashing traversal.
Native rows call the actual native fingerprinter, including all three Git
commands, against the runtime root. Neither includes the broader inventory's
ancestor audit or project lock/receipt verification, and neither is described as
an everyday project launch. Nested-root reuse is not implemented or measured.

Artifact rows call the actual bounded single-file reader. SHA-256 was already
single-pass here after 0059. Artifact rows hash without executing that artifact.

## Measurement and correctness

One executable contains all candidates. Two fixed-seed interleaved repeats,
30 observations per cell, 12 cells: 720 final samples, all retained. Every cell
has two explicit warmups before sampling. A preliminary 600-sample run before
adding the buffer controls is retained separately, with its initial main source;
it is not pooled with the final run or used to select favourable samples.

Single-threaded rows are pinned to one allowed physical core. Parallel artifact
rows use four distinct physical cores and four Rayon workers. Thread-pool startup
is inside the timed interval. No mmap, detached work, or parallel small-file tree
claim. Core IDs, CPU flags, compiler, binary hash and full dependency graph are
retained. SIMD dispatch uses each pinned crate's ordinary defaults; no custom
native CPU flags are passed.

`inside_ms` includes the reader/Git work, digest formatting and conversion to a
JSON value. Inputs are decoded before that timer; stdout encoding happens after
it. `wall_ms` is Python spawn-to-exit, including startup, input decoding and output.
All files are warm; this is not storage throughput or a cold-launch claim.

Python independently computes legacy SHA-256, single-pass SHA-256 framing and
all per-file SHA-256 records. BLAKE3 references hash each whole input with the
crate's one-shot API, against which streaming and parallel output are checked;
Python independently constructs the tree framing for that reference. The empty
published BLAKE3 vector is also tested. Every measured tree checks all names,
modes, lengths and per-file digests, and every artifact result matches its full
reference. This does not replace future migration or mutation/refusal gates.

The pinned benchmark graph uses sha2 0.10.9, blake3 1.8.7 and Rayon 1.12.0.
Cargo.lock is checked in. The resolved graph, package licence expressions and
saved top-level licence texts are retained with hashes. Product dependencies
are unchanged. Initial scaffolding failures are preserved in build logs: an
uncached Rayon candidate was replaced with the cached pinned release, then an
ambiguous Rust `AsRef` required an explicit byte-slice type before compilation.

## Identity migration remains a decision

Even keeping SHA-256 while changing tree construction changes assembly keys and
runtime tree-derived IDs. Old assembly entries do not disappear; existing entries
can retain around 1.5 GB each with no eviction currently available. The record
must provide a safe removal policy or explicitly retain them until a later record.
Installed runtimes need a compatibility path because validation recomputes their
tree identity. Neither a relock nor a faster hash automatically solves these.
