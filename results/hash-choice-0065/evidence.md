# Hash-choice probe before the 0065 identity decision

Status: measured on Linux, ready for review. Product rnx and rnx-project are
unchanged at `7cd3205`. Input fixture: accepted bench `c2af5de`. Reproduction and
exact candidate definitions: `probes/hash-choice/README.md`.

## Single-threaded result

The same executable selects all candidates. The actual 443-file runtime tree
contains 6,988,177 bytes; its whole-file contents are read once in every variant.
The existing algorithm hashes each byte twice. The two candidates hash content
once and construct the tree from name, executable bit, length and raw file digest.
This changes tree identity, and is not deployed by this probe.

Medians in milliseconds, two interleaved repeats pinned to physical core 0:

| Workload | Existing double SHA-256 | Single-pass SHA-256 tree | Single-pass BLAKE3 tree |
|---|---:|---:|---:|
| Tree reader, fixed accepted file list | 10.54 / 10.66 | 6.93 / 6.81 | **5.55 / 5.60** |
| Runtime native fingerprint, including Git | 14.77 / 14.78 | 10.86 / 10.86 | **9.72 / 9.57** |

Removing the second SHA-256 content pass saves 3.61 / 3.85 ms in the tree reader.
BLAKE3 then saves another 1.39 / 1.21 ms. The native row retains the submodule,
untracked and staged Git commands; it does not implement nested-root reuse.
Neither row includes the broader ancestor audit or project verification/exec.
This is therefore not a new everyday-launch number or a new adapter-count slope.
The Git topology is the same nested working-tree context as the accepted probe.

The real Polars artifact is **107,567,832 bytes**. Artifact SHA-256 already hashes
each byte once after 0059. With the unchanged 16 KiB read buffer:

| Artifact reader | One-core median |
|---|---:|
| SHA-256 | 66.03 / 66.03 ms |
| BLAKE3 | **35.30 / 35.27 ms** |

The measured saving is 30.73 / 30.76 ms in full artifact hashing. This is not the
whole `--verify` command, which still checks other inputs and launches the program.
Ordinary metadata-stamp hits do not perform this full artifact read today.

## Multicore is a separate choice

All these rows hash the same artifact to the same digest. The parallel rows use
four workers on distinct physical cores 0, 2, 4 and 6. Pool startup is inside the
clock. The larger buffer is heap allocated; no mmap or whole-artifact buffering
is introduced. The final byte and metadata checks remain in the reader.

| Algorithm | Cores | Read buffer | Median |
|---|---:|---:|---:|
| SHA-256 | 1 | 16 KiB | 66.03 / 66.03 ms |
| SHA-256 | 1 | 1 MiB | 65.49 / 65.47 ms |
| BLAKE3 | 1 | 16 KiB | 35.30 / 35.27 ms |
| BLAKE3 | 1 | 1 MiB | 33.35 / 33.39 ms |
| BLAKE3 `update_rayon` | 4 | 16 KiB | 57.62 / 57.51 ms |
| BLAKE3 `update_rayon` | 4 | 1 MiB | **16.29 / 16.26 ms** |

Simply applying Rayon to every existing small buffer is slower than one-core
BLAKE3. The larger buffer saves about 1.9 ms by itself; the matched 1 MiB control
separately demonstrates the additional parallel gain. This does not settle a
production worker count, buffer threshold or multicore default, and no parallel
small-file inventory claim is made.

## Validation and retained evidence

The final journal contains **720 samples**, 12 cells, 30 samples per cell in each
of two fixed-seed repeats, with two explicit warmups per cell. Every sample's full
result is validated. An initial 600-sample run, before the single-threaded large-
buffer controls were added, is retained separately and is not pooled into these
numbers. It reached the same qualitative result; no slow samples were removed.

Python independently frames and hashes both SHA-256 tree encodings and all file
records. It reproduces the accepted legacy tree digest exactly. BLAKE3 streaming
and parallel outputs match whole-input one-shot references; tree framing is
constructed independently in Python. The published empty BLAKE3 vector passes.
Every measured tree checks all filenames, modes, sizes and per-file digests, not
only a final tree hash. The artifact matches the accepted input SHA-256 identity
and all BLAKE3 paths match the one-shot BLAKE3 reference.

The copied ordinary reader keeps its allowance, no-follow/nonblocking opens,
component checks, metadata checks and detection read. The single-pass candidate
changes only how validated file content enters the tree digest. Upstream test
hooks and its external test module are excluded from this standalone harness;
this benchmark does not claim to replace the future equivalence/refusal gates.

Formatting, strict all-target clippy and the vector test pass. Cargo.lock and the
resolved 34-dependency graph are retained, with declared licences and top-level
licence texts for all 34 packages. Direct pins are sha2 0.10.9, blake3 1.8.7 and
Rayon 1.12.0. No root dependency or product format changes. Initial scaffolding
build errors are retained and explained in the README, before any timing.

Exact generated readers are archived alongside the recipe and published original
revision. Input paths/digests, reference outputs, binary digest, CPU topology/flags,
compiler, build/check logs, phase and process-wall clocks are retained. Core
selection is recorded, not silently inferred from logical processor count.

The internal clock includes result-value construction and digest formatting;
process-wall timings include input decoding and stdout encoding too. Files are
warm and the host is Linux. No cold-storage, hardware-independent throughput,
Windows or full-product launch speedup is claimed.

## Decision supported, migration still required

BLAKE3 is a measured candidate: it improves source reading beyond single-pass
SHA-256 and nearly halves the large artifact's full hash on one core. These results
support considering it before fixing the replacement identity format. They do not
require parallel hashing to obtain a useful gain.

Tree construction changes alone already affect runtime tree IDs and assembly
keys. An algorithm switch also touches file digests, receipts and artifact hashes.
Fields presently labelled `sha256` cannot silently hold BLAKE3 in product documents;
the copied field name in this private harness is not a proposed wire format.

The record must decide how old installed runtimes continue validating, how legacy
locks/receipts are handled, and what becomes of old cache entries. New assembly
keys do **not** remove old entries: each retained Polars-sized assembly can occupy
around 1.5 GB. There is no eviction today. Either ship a safe explicit removal
mechanism or state that old entries remain until a later cleanup record; do not
present relocking as reclaiming that disk space.

Nested-root reuse remains its own equivalence experiment. No caching, reduced
content verification, removal policy or migration has been implemented here.
