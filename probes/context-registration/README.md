# Rune default-context profiling on nano (probe: context-registration)

Measured by Codex on 2026-09-13. This is an isolated diagnostic experiment,
not a change to rnx or to the committed rnx-bench baseline. Neither repository
was modified. No kernel settings were changed.

The first module-level experiment is preserved in `results/`, alongside the follow-ups.
The follow-up below measures installation stages and individual trait
implementations; its raw results live in separate subdirectories.

A subsequent [upstream source check](results/upstream/README.md) at main
commit `bb8e6937` confirms eager expansion remains. It also records the
type-specific captured handlers that constrain a sharing proposal. Main
has not been benchmarked by this experiment.

## Follow-up: installation stages and trait expansion

Using the same toolchain, release settings, CPU affinity, and fresh-process
method, installation breaks down as follows:

| Module | Total installation stages | Trait implementations | Share |
|---|---:|---:|---:|
| `std::iter` | 0.536 ms | 0.469 ms | 88% |
| `std::ops` | 0.546 ms | 0.502 ms | 92% |

Those trait stages install **1,699 function-map entries** (891 + 808) and
898 metadata records (464 + 434). These are registry entry counts, not
distinct native bodies: named functions can be registered under both
associated-function and full-item hashes.

A further pass times each of the 78 trait implementations in these modules:

| Trait implementation group | Mean |
|---|---:|
| `Iterator` for 12 types in `iter` | 0.425 ms |
| `Iterator` for 9 types in `ops` | 0.294 ms |
| `Ord` for 6 types in `ops` | 0.084 ms |
| `PartialEq` for 7 types in `ops` | 0.071 ms |
| `DoubleEndedIterator` for 12 types in `iter` | 0.043 ms |

**Installing `Iterator` implementations for those 21 types alone takes
about 0.719 ms.** It adds 1,387 function-map entries and 715 metadata records.
This is measured startup registration, not script iteration or JIT work.

The source explains the work being performed: the `Iterator` trait handler
in `modules/iter.rs` locates protocol handlers and registers methods such as
`count` for each implementing type. `TraitContext::function_inner` routes
these registrations through `Context::install_associated`, which builds
names, installs function aliases and type-name constants, and calls
`install_meta` to update name and metadata indexes.

**Optimization target:** reduce the per-type registration cost along that
path while preserving the exposed methods, aliases, and diagnostics. The
measurements have not isolated allocation, hashing, path construction, or
map growth within it. They establish neither an achieved speedup nor that
all 0.719 ms can be eliminated. Removing iterator methods is not proposed.

Stage controls: whole context construction was 2.556 ± 0.018 ms without
stage clocks, versus 2.583 ± 0.017 ms with them and their final reporting.
The individual-trait pass adds nested clocks and buffered samples, so use
it for attribution rather than as a pristine process-startup measurement.
All stages and all per-trait function/metadata counts were checked for
consistency across 100 fresh processes. A timer measures a loop in the
context of the original module order, not the isolated cost of an entry.

Details: [stage table](results/stages/summary.md),
[trait table](results/traits/summary.md), with CSV observations beside each.
`results/stages/environment.txt` records the binary hash and build conditions
for both passes. The original `results/` baseline remains preserved.

To reproduce this follow-up, restore a fresh Rune 0.14.2 source copy into
`./rune`, then apply all three patches in order:

```sh
patch -d rune -p1 < instrumentation.patch
patch -d rune -p1 < stage-instrumentation.patch
patch -d rune -p1 < trait-instrumentation.patch
bash run_stages.sh
```

## Findings

Rune 0.14.2 installs 33 default modules in dependency order. Timing each
module's construction, installation by reference, and destruction separately
gives these means across 100 fresh processes, pinned to CPU 4:

| Work | Mean |
|---|---:|
| Construct module descriptions, summed | 0.239 ms |
| Install them into the context, summed | 2.258 ms |
| Destroy module descriptions, summed | 0.024 ms |
| Total measured registration work | 2.520 ms |

Installation is approximately 90% of measured registration time. The largest
module totals are `ops` (0.591 ms), `iter` (0.586 ms),
`collections::hash_set` (0.223 ms), `string` (0.190 ms), and
`collections::hash_map` (0.147 ms). `ops` and `iter` together account for
about 47%. Full breakdown: [results/modules.md](results/modules.md).

The same binary with per-module instrumentation disabled measures context
construction at 2.512 ms (standard deviation 0.014 ms). With instrumentation
enabled, including its final reporting, it measures 2.550 ms. These were
interleaved in a deterministic shuffled order under matching affinity.

A separate lifecycle measurement finds context construction at 2.516 ms and
**context destruction at 0.313 ms**. This destruction is different from
destroying the temporary module descriptions during registration.

Hyperfine measures the uninstrumented context process at 3.377 ms versus
0.455 ms for the same binary returning immediately. That delta includes
construction **and destruction**, plus other differences between the paths;
it must not be labelled pure context construction time. Earlier process-level
phase deltas need the same qualification. These observations do not resolve
the earlier unmatched 7–9 ms Instant measurement.

The instrumented hyperfine row includes an `env` launcher and 33 lines of
output, so its elapsed time is not a clean measure of timer overhead.
Per-module clocks exclude that reporting, which occurs after registration.

## Interpretation and next experiment

Source inspection shows `Context::install` processes types, traits, items,
associated functions, trait implementations, reexports, and constructors.
Trait implementations can invoke handlers which register additional functions.
The iterator and operator modules register many iterator types and trait
implementations. This is a candidate explanation for their cost, **not yet
a measured attribution within installation**.

This initial experiment motivated the follow-up above. It establishes no
eval speedup and proposes no reduced standard library.

## Build conditions and limits

- Rust **1.98.1**, the currently installed default toolchain. Earlier rnx
  evidence records 1.95; these are new measurements, not an exact reproduction
  of those builds.
- Rune exactly 0.14.2, `default-features = false`, `features = ["std"]`, Cargo
  release profile. The rnx lockfile seeded dependency resolution; this crate's
  resulting lockfile is preserved.
- The probe uses the system allocator without rnx's allocation-accounting
  wrapper and omits rnx host/text registration. It measures Rune, not complete
  rnx startup.
- Rune is a local source copy with a diagnostic patch. The disabled branch
  retains the original registration calls but is not a separately built,
  pristine Rune control. The patch adds an environment lookup and branches.
- Ten warmups; 100 fresh processes per mode. Processes have warm filesystem
  caches; this is not a cold-cache boot benchmark. Module timing retains
  upstream registration order, so costs reflect that position and context.
- `measure.py` retains every module observation, both context modes, and
  lifecycle samples. `run.sh` preserves toolchain, CPU, hashes, feature tree,
  and process-level hyperfine exports in `results/`.

## Reproduction

The source copy and build output are disposable. Restore the Rune copy from
the Cargo registry's `rune-0.14.2` directory into `./rune`, then apply:

```sh
patch -d rune -p1 < instrumentation.patch
bash run.sh
```

Use the preserved Cargo.lock and Rust 1.98.1 for matching builds. `run.sh`
uses offline Cargo resolution and requires the dependencies already cached,
plus Python 3, taskset, and hyperfine. Results are overwritten when rerun.
