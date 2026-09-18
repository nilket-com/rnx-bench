# Native inventory measurements before the 0065 draft

No cache policy is implemented. Product rnx and rnx-project sources stay unchanged.
This probe measures the runtime-tree floor, incremental adapter costs and canonical
path shape before choosing any optimization or changing verification coverage.

Run serially from rnx-bench, with rnx alongside it and cached Cargo dependencies:

```sh
python3 probes/native-inventory/prepare.py
python3 probes/native-inventory/setup.py
python3 probes/native-inventory/checks.py
python3 probes/native-inventory/measure.py
python3 probes/native-inventory/collect.py
python3 probes/native-inventory/trace.py
```

A full rerun requires this probe's `target/` and result directory to be absent;
save prior results first. `measure.py` refuses an existing sample journal. Setup
builds four real assemblies; those setup durations are not speed comparisons.
No other build should run while checks or timings execute. The full measurement
uses 30 samples per cell, two repeats, two explicit warmups per cell, one allowed
CPU and one Polars thread. Every sample stays in the JSONL journal. Output, exit
status, inventory identity and profile framing are checked for every launch.

## Inputs and controls

Preparation copies the published tracked runtime snapshot. It adds a complete
PostgreSQL-adapter copy under `adapters/pgcopy`, changing its Cargo package/crate
name and registered help namespace. It does not substitute a stub or shrink the
source tree. The original has 21 files / 517,330 bytes; the renamed copy has 21
files / 517,312 bytes. Exact renaming code and affected filenames are preserved.
The runtime fixture includes that extra adapter at **every** declaration count,
so its 443-file / 6,988,177-byte floor is constant. It is deliberately larger than
the original snapshot; it is not reported as the unmodified checkout's byte count.

The four declared rosters are: none; Polars; Polars plus PostgreSQL; then those
two plus pgcopy. Each still includes the runtime itself. The real product lock
resolves every graph; the probe's reconstructed metadata and resulting inventory
must equal the lock's actual native inventory, as ordinary shared launch does.
The runtime tree also contains the shipped adapters' files, which are read again
when those subtrees are separately declared. That is existing inventory behavior,
not deduplicated by this probe.

The shallow, deep and long-shallow layouts have identical tracked working bytes,
file counts, executable modes and tree digests. The deep root adds eight directory
components. The long-shallow root has the same path-string length as the deep root
but the same component count as the shallow root. Git administration is independently
created at each runtime root; every adapter remains two levels below that root.
External candidate counts and present files are recorded. Added absent ancestor
candidates are part of the measured depth effect, not silently removed.

Two complementary measurements keep the executable issue explicit:

- **Fixed target:** one inventory-probe executable per instrumentation control
  imports the real private inventory functions, validates the full result against
  the expected digest and execs the **same stock rnx binary** with eval 42 in every
  count/path cell. The native-call interval and whole launch are both recorded.
  Configuration decoding, output digest serialization/checking and exec are fixture
  work; this is not called a full `rnx-project` launch. The exact fixed executable
  hash is preserved, with its own direct-launch control.
- **Product:** one unchanged project-tool binary launches four genuinely assembled
  applications through ordinary project eval. Each roster necessarily has its own
  artifact and therefore its own direct eval control. The instrumented copy runs
  those same inputs/artifacts too. No forged receipt or bypassed verification is
  used to make unlike rosters claim to be one application executable.

## Clocks and attribution

Only isolated tool copies gain clocks. The stock copy adds a private probe binary;
its existing product sources stay byte-identical. The timed copy adds in-memory
counters and one profile line before exec. Exact changed files, manifests, original
revision, lock equality and binary hashes are archived. Both copies pass tests,
formatting and strict clippy. No production profiling hooks are installed.

Per native tree, separately time the submodule `rev-parse`, the untracked listing,
the staged listing and the existing file-hashing traversal. Within traversal,
record path-component/metadata checks, open/metadata, read calls and digest updates.
These regions include normal instruction and clock bookkeeping costs; they are not
isolated syscall or SHA-throughput measurements. `tree_other` is the per-sample
remainder (ordering, framing, detection-byte/final metadata, digest formatting and
bookkeeping), not a claim that those operations took zero time. `native_other`
contains root setup and index decoding outside Git/traversal. Clock hierarchy is
inclusive; subtract children within each sample before summarizing. Do not add a
parent and its children or expect sums of independent medians to equal a median.

The audit is shared, deduplicated work. Candidate time is attributed to the longest
native root containing that candidate; ancestors outside all native roots are
labelled **shared**. Counts show that a declaration does not get its own duplicate
ancestor audit. The overall audit interval also contains candidate bookkeeping.
The inventory total includes metadata/root setup in addition to trees and audit.

Fixed-target routes compare stock, timed-with-clocks-off and timed-with-clocks-on.
Full product routes compare stock, timed-with-clocks-on and each artifact directly.
Their end-to-end deltas bound instrumentation impact instead of assuming it away.
The Python spawn/wait clock includes launch overhead equally across controls.
The slope is descriptive for this specific roster and file/byte mix, not a promise
that any arbitrary third adapter costs the same amount.

This is warm single-host Linux evidence. Path shape alone is controlled here;
matching or failing to match a prior installed-runtime delta does not establish
other installed-state effects. There is no cache invalidation policy, skipped read,
changed Git enumeration, new default or weakened `--verify` in this probe. Those
remain decisions for the draft after these results are reviewed.

`trace.py` runs one untimed process trace after measurement. In this fixture
context, every submodule check launches another Git to inspect the parent working
tree. Thus four native roots produce 12 direct Git commands and four nested Git
children. This nested-repository fixture context is recorded, not generalized to
every possible installation or checkout placement.
