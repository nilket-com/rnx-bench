# Archived 0205 column measurement harnesses

These sources are the measured host comparator, Polars comparator, CLI fixtures
and capture drivers. Private absolute paths have been replaced by placeholders.
The three Polars Rust files also have leading indentation converted to hard tabs
with rustfmt (edition 2021, import reordering disabled). Expanding those tabs to
four-column stops reconstructs the complete pre-format archive bytes; `diff -w`
is empty. The [formatting proof](../../results/column-0205-2026-11-04/formatting-proof.json)
retains both archive hashes and the unchanged original measured-source hashes.
Other source bytes are unchanged apart from path placeholders. Original and transformed
hashes are in [harness.json](../../results/column-0205-2026-11-04/harness.json).
This is an archive, not a portable one-command benchmark launcher.

Resolve `<RNX_ROOT>` to the pinned rnx checkout, `<RUNE_ROOT>` to its pinned Rune
checkout, `<HOST_PROBE>` and `<POLARS_PROBE>` to the two archived probe directories,
`<VALGRIND_ROOT>` to the instrumented Valgrind installation, and the remaining
user/work placeholders to local directories before attempting a new capture.
Recorded driver receipt locations refer to original prerequisite runs; regenerate
those prerequisites for a new run rather than claiming the old hashes apply.
Notification calls require the original messaging service; they are not needed
to interpret the report. Drivers are archived for audit and are never invoked by
the report renderer.

The host manifest uses a path dependency: build against the rnx revision in the
report, with its unchanged locked dependency versions. Polars is a separate
locked git dependency and build profile. `build.rs` compiles the measurement shim
against Valgrind headers; user-cycle access requires the corresponding perf-event
permission. These paths and permissions do not imply a successful rerun.

The `fixtures` directory contains all twenty actual Rune scripts. Each constructs
its inputs before the map boundary, validates every output through equality with
the expected Series, and reports the first and warm execution paths. For example,
using a freshly validated production binary:

```sh
<RNX_ROOT>/adapters/polars/target/release/rnx-polars run --debug-engine \
    --budget 1000000000 fixtures/i64add-100000000-flat/program.rn
```

This direct command provides an output/path witness and millisecond map timing;
it does not reproduce all-thread Callgrind attribution on its own. See the archived
CLI boundary drivers for that measurement. A new run is separate evidence.
