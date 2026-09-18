# Native inventory probe before the 0065 draft

Status: measured on Linux, ready for review. No product code changed and no cache
policy was adopted. Source baseline: rnx `7cd3205`; bench baseline `3861efd`.
Reproduction and clock definitions are in `probes/native-inventory/README.md`.

## Everyday cost versus adapter count

One unchanged project-tool executable ran each real project. Each assembled
application has its own direct-launch control; unlike rosters are not claimed
to be the same executable. All execute `eval 42`, with no database or engine work.
Times below are medians in milliseconds, two interleaved repeats on CPU 0.

| Declared adapters | Project launch | Its direct artifact | Project minus direct |
|---|---:|---:|---:|
| None | 23.01 / 23.00 | 5.54 / 5.52 | **17.48 / 17.48** |
| Polars | 28.82 / 28.81 | 6.66 / 6.62 | **22.15 / 22.19** |
| Polars + PostgreSQL | 32.90 / 32.89 | 6.73 / 6.64 | **26.17 / 26.24** |
| Those two + renamed PostgreSQL copy | 36.85 / 36.93 | 6.68 / 6.64 | **30.17 / 30.29** |

The descriptive fitted slopes are **4.21 / 4.25 ms per adapter**. The actual
increments are 4.67 / 4.71 ms for Polars, 4.01 / 4.05 ms for PostgreSQL, and
4.00 / 4.05 ms for its renamed copy. This is a roster-specific slope, not a
constant charge promised for arbitrary adapter sizes.

Zero adapters still inventories the runtime. The fixture's constant runtime root
contains 443 tracked files / 6,988,177 bytes, including the extra copied adapter
at every count. Polars contributes a separately inventoried 23 files / 984,808
bytes; PostgreSQL 21 / 517,330; pgcopy 21 / 517,312. The copy preserves the whole
adapter, including notices and tests; only package/crate/help names change. The
fixture runtime is consequently larger than the unmodified baseline snapshot.

The runtime tree already includes those adapter files. Declaring each adapter
causes its subtree to be inventoried again. No per-launch or persistent reuse is
introduced to hide that work.

## Where inventory spends its time

These are the **clocked** fixed-target measurements with three adapters at the
shallow root. They are inclusive medians; columns are not summed to manufacture
the independently measured total. `tree_total` includes the following read/hash
rows; the audit is separate and shared across roots.

| Native tree | Submodule check | Untracked listing | Staged listing | Tree traversal/read/hash | Native total |
|---|---:|---:|---:|---:|---:|
| Runtime | 1.72 / 1.72 | 1.17 / 1.17 | 0.77 / 0.77 | 10.91 / 10.90 | 14.66 / 14.63 |
| Polars | 1.71 / 1.71 | 0.73 / 0.73 | 0.66 / 0.67 | 1.29 / 1.28 | 4.41 / 4.41 |
| PostgreSQL | 1.67 / 1.68 | 0.72 / 0.72 | 0.65 / 0.65 | 0.74 / 0.74 | 3.80 / 3.81 |
| pgcopy | 1.79 / 1.78 | 0.74 / 0.74 | 0.67 / 0.67 | 0.76 / 0.75 | 3.97 / 3.95 |

The runtime's traversal contains about **7.47 ms of digest updates**, 1.32 ms of
path/metadata checks, 0.47 ms of open/metadata, 0.84–0.85 ms of reads and about
0.76 ms of other traversal work. The latter includes framing, ordering, final
metadata/detection reads, digest formatting and clock bookkeeping. These are
instrumented regions, not pure SHA or syscall microbenchmarks.

The whole ancestor audit is only **0.365 ms** here. Candidate times attributed to
runtime/Polars/PostgreSQL/pgcopy are approximately 0.100 / 0.029 / 0.029 / 0.033 ms;
shared ancestors contribute about 0.050 ms, with the remainder in audit bookkeeping.
Counts are 10 runtime-owned candidates, 5 per adapter and 45 shared candidates.
At zero adapters there is no fictional per-adapter copy of shared audit work.
`trees.json` and `summary.json` retain every count/layout/repeat, not just this row.

An untimed process trace explains why the submodule check deserves its own column.
Four native roots cause twelve direct Git commands. In this fixture's nested Git
context, each of the four `rev-parse --show-superproject-working-tree` commands
also launches a Git parent-index listing: **sixteen Git processes altogether**.
All four roots are in the same runtime working tree, inside the ignored bench
target directory. This process count is proven for that context, not generalized
to every possible source installation. The full trace and command are retained.

## Canonical path depth

A separate fixed-target probe imports the actual inventory implementation,
reproduces each real lock's native inventory, validates its digest, then execs
**the same fixed rnx binary** for every row. The isolated interval measures the
native call (with metadata encoding), not a different adapter startup.

Shallow roots have 9 canonical components and 56 characters; deep roots have
17 components and 111 characters. The long-shallow control has 9 components and
111 characters. All have identical tracked bytes, file counts, executable modes
and tree digests. The deep layout adds 40 absent ancestor candidates; no file is
silently removed to keep its audit artificially constant.

| Adapters | Deep minus shallow inventory | Long-shallow minus shallow | Deep minus equally long shallow |
|---|---:|---:|---:|
| 0 | 0.58 / 0.63 | 0.04 / 0.11 | 0.55 / 0.52 |
| 1 | 0.78 / 0.77 | 0.20 / 0.16 | 0.58 / 0.61 |
| 2 | 0.93 / 0.78 | 0.22 / 0.15 | 0.71 / 0.64 |
| 3 | 0.92 / 0.95 | 0.17 / 0.26 | 0.76 / 0.69 |

Depth has a repeatable causal cost in this control. At three adapters, the runtime's
path/metadata interval rises from about 1.32 to 1.67 ms, open/metadata from 0.47 to
0.57 ms, and total audit from 0.365 to 0.558 ms. Digest time remains around 7.5 ms.
The equally long shallow path is much closer to the short shallow one.

This supports depth as an explanation for much of 0064's approximately one-ms
installed delta. It does **not** establish that every part of that historical delta
was due to depth: the historical installation had its own path shape, snapshot
and Git administration. The controlled result is the table above.

## Measurement and validation

There are **2,940 retained samples**: 49 cells, 30 samples per cell, two fixed-seed
interleaved repeats. Two warmups per cell are explicit and outside the journal.
Every output, exit, expected inventory digest and profile frame was checked.
No samples were discarded. Setup/builds completed before timing; assembly build
observations (37–113 seconds) are setup costs, not matched compilation claims.

Instrumentation is measurable. Clocked product launches are **0.51–0.86 ms** above
stock. Fixed-target clocked launches are **0.54–1.01 ms** above stock across all
layouts/counts. The same timed binary with clocks disabled differs from stock by
-0.08 to +0.18 ms. Thus use uninstrumented samples for launch/path comparisons;
use clocked regions for attribution with that overhead stated, not subtracted by
an invented per-phase correction.

The stock product sources remain byte-identical; only its private probe target
and manifest entry are added. Timed sources add clocks and one stderr frame,
with no skipped reads, Git calls or validation branches. Both isolated copies
pass formatting, strict all-target test-support clippy and all 40 tool tests;
the two unrelated opt-in integrations stay ignored. Cargo locks are unchanged.
A helper's unused-emit warning in the private library target was given a targeted
allowance before final checks and measurement; the binary uses that helper.

Exact modified/new sources, generation recipes, original revision, binary hashes,
configs/inventory results, checks, host facts and raw samples are retained. A digest
alone is not substituted for reconstructable source. rnx remains clean at `7cd3205`.
No new Windows execution, cold-cache timing, hermeticity or universal slope is claimed.

## What the draft can now decide

The runtime floor is largely content hashing and filesystem work. Most additional
adapter cost in this roster is repeated Git work, not ancestor auditing. Repeated
repository checks and overlapping tree reads are therefore concrete candidates
for an equivalence probe before considering persistent caches. This evidence does
not prove a replacement algorithm or authorize a narrower fingerprint contract.

Any persistent cache must state its identity, invalidation rules and missed edits,
and keep full native checks under `--verify`. None exists in this probe. The next
record should use launch cost versus adapter count as its product gate, and keep
source size and Git-repository topology visible beside the slope.
