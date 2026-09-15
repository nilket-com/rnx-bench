# Record 0049 namespace migration

Codex, nano (Linux), 2026-09-15. Plan `57cd19f`, accepted source baseline
`4652830`. No dependency or feature changes in rnx or its kernel package.
The before binary's SHA256 matches the accepted 0047 notebook export.
`conditions.json` preserves versions, binary hashes/sizes, source variants,
full output/exit comparisons, session memory reports and timing commands.

## Result

`host` is no longer a registered Rune crate, even with test-support.
JSON is `json::parse` / `json::stringify`, streams are `io::stdin` /
`io::eprint`, and exit is `process::exit`. Legacy process calls use the
existing options-object facade. Test fixtures moved to feature-gated
`rnx_test`; the production build refuses that namespace.

The supervisor's `run_child_with` region is byte-identical to the accepted
source (`supervisor-unchanged.json`). JSON's reader and guarded writer are
unchanged except for adding their registrations and updating an API comment.
The compatibility wrappers and old module installer are removed. Interrupt
setup lives in `install_core`, which all former installer callers now use.
Pure configuration contexts do not call it.

## Checks

- Root default suite: **347 passed**. Test-support: **388 passed**.
- Separate kernel suites: **23 passed** each; kernel clippy with denied
  warnings passes. The kernel package source/manifests/lockfile are unchanged.
- Root formatting and both notice generators pass.
- Release selfcheck and the worker boundary/lifecycle fixture pass, including
  all removed names, exact u64 JSON, recoverable exit refusal and NUL stderr.
- All four prior supervision fixtures pass with migrated stream calls.
- The isolated installed-kernel notebook executes new JSON/stream/process
  calls, catches exit refusal, fails an old name, retains bindings and saves
  a notebook that passes strict nbformat validation. IOPub errors retain
  exactly the three protocol fields (plus notebook `output_type`).
- The real browser journey passes select/execute/reconnect/interrupt/restart/
  save/reopen. Screenshots are actual Chromium captures. The namespace-specific
  cells are in `namespaces.ipynb`; `Journey.ipynb` is the existing browser
  regression workflow, not a claim that its screenshots show every new API.
- Windows module/unit and 16 integration-test source targets type-check in
  isolated probe packages. These use explicit supervisor/stream stubs or an
  unusable executable placeholder, not the real Windows runtime. The latter
  enables Win32_Security for the existing CreateProcessW console fixture.
- Full root Windows check still fails at ring's missing MSVC `lib.exe`.
  Kernel Windows check passes with its inherited unused-mut warning. No
  Windows, macOS or BSD execution is claimed.

`checks.json` records checks and their logs. Clippy on root with
`--all-targets --features test-support -- -D warnings` fails on the accepted
baseline and the implementation alike: **35 emitted code-bearing diagnostics,
none added or removed**, including bin/test duplicates. Both JSON message
streams and the multiset comparison are preserved. No lint was suppressed,
and no unrelated completion/renderer cleanup was made to call this clean.

## Migration inventory

`inventory-before.txt` preserves active pre-migration source references.
`inventory-after.json` lists the remaining active-tree references and their
classification: internal Rust paths, negative API tests, migration text.
`migrated-rnx-files.txt` lists the implementation/test/documentation files.
Old plan transcripts, raw exports, notebooks and snapshots remain historical.

The six current bench callers migrated are scripts/json.rn,
scripts/run_time_0038_examples.py, probes/colour/terminal.py,
probes/worker-boundary/examples.py, and probes/jupyter-supervision/{probe,extended}.py.
Two other executable probes intentionally remain revision-specific:
probes/process/measure.py now uses a preserved json-0044.rn for its original
binaries; probes/jupyter-notebook/startup.py asserts the old 0047 worker hash.
They are labeled historical and point current comparisons here. Prior raw
results were not edited. The new measure driver has explicit before/after
sources and never asks an old binary to accept the new namespace.

Existing process assertions were retained. The old compatibility comparison
now compares default versus explicit timeout options. Error tests still
require the program name, cap/delivery/cancellation gates keep their predicates,
and UTF-8 advice now requires process::run_bytes. No process test expectation
was relaxed to accept a new behavioral divergence. Help inventory counts
change from eight generic functions to seven across the three domains;
completion tests use json:: rather than assuming one host:: prefix.

## Measured cost

Whole processes, pinned core 4, 10 warmups and 100 runs. All selected outputs
match, including JSON refusal payloads wrapped as values rather than propagated
errors with intentionally different source excerpts. Hyperfine outlier warnings
are retained. Runs were sequential, so drift and path/layout effects are not
isolated; no speedup is claimed.

| command | before mean ms | after mean ms |
| --- | ---: | ---: |
| version | 0.582 | 0.551 |
| eval 42 | 4.211 | 4.027 |
| bare run | 3.975 | 3.686 |
| 10k JSON loop | 12.298 | 11.918 |
| supervised /bin/true | 4.804 | 4.695 |

Release binary: **15,102,752 -> 15,095,392 bytes** (-7,360).
Session startup allocation reference: **1,823,011 -> 1,824,426 bytes**
(+1,415). These are tracked Rust allocation requests, not RSS; the full
`:memory` outputs and current-live samples are in conditions.json.

## Existing behavior observed while writing the fixture

Top-level `?` on the refused exit in a session produces the existing
`Expected type Tuple but found Result` wrapper error. Old and new binaries
produce identical diagnostic bytes (`exit-propagation-observation.json`).
The notebook fixture catches the refusal using `.is_err()` and proves the
next cell works. This migration does not repair propagation of session errors
or claim Jupyter input_request support for io::stdin.

## Reproduction

Build the accepted `4652830` root in a separate checkout with
`cargo build --release --locked`, retain its binary, then build the current
root the same way. Build the independent kernel package release binary and
its transport-probe examples. Prepare the pinned notebook environment as in
probes/jupyter-notebook/README.md, then run:

```
probes/namespaces/run.sh /absolute/before/rnx /absolute/after/rnx
```

The ordinary root target/release/rnx must be AFTER for the installed notebook
fixtures. Use a fresh output copy if preserving this run. The before binary
was copied to /tmp for this measurement and is not committed; the accepted
source revision and recorded hash identify it independently of that path.
