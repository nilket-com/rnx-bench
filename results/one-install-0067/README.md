# 0067 gate 4 — observed one-install journeys

Product: accepted and published rnx `7ae886305aea33312a061cbafbebbb49ff8bc8c4`.
No product changes were needed. The second, explicitly labelled fixture revision
is `47f3b7f2769d79209afd7b2f3081e8eb0c2cf2c0`; its repository-URL-only delta is
preserved in `fixture.bundle`. Both installs use Cargo's Git acquisition and
install only `rnx`. Their logs and SHA-256 evidence hashes are beside this file.
The fixture working checkout was renamed before the adapter journeys; Cargo
fetches from the bare origin. No `rnx-project` is on either controlled PATH.

| Control | Published origin | Fixture origin |
|---|---|---|
| Git install; acquired notice at the selected revision | pass | pass |
| Decline creates no scratch/cache/runtime store | pass | pass |
| First Polars assembly from empty consumer Git/assembly caches | pass | pass |
| Same PID, input 1, lost bindings, retained history, unchanged cwd | pass | pass |
| CSV, filter/group/sum/sort, preview, Parquet round trip, error recovery | pass | pass |
| Mixed request adds only PostgreSQL, retains Polars, typed SQL | pass | pass |
| No-op request, interrupt, reset, quit | pass | pass |
| Second scratch: offline, network namespace, positive compilation traps | pass | pass |
| No runtime store created; second-session trace has no store access | pass | pass |
| Exact shell-quoted reopen command; EOF | pass | pass |
| Session and private PostgreSQL processes reaped | pass | pass |

The stale-selection and explicit-override control uses the published executable.
A real runtime is installed from the renamed fixture tree; `current.json` then
names a missing ID and `runtime show` refuses. Stock `:dep --offline polars` still
uses the published Git revision, attaches with compilation trapped, makes no
network access and never opens that store. The stale selection remains byte
identical. Explicit `RNX_DEP_RUNTIME` to the retained source creates a path-native
scratch and really builds/starts its Polars assembly. This separate developer
control intentionally uses the runtime store; the default path does not.

The published combined Git artifact runs as a notebook worker with an isolated
kernelspec. A failing query leaves its frame usable; preview works; a bare frame
is opaque; restart loses a saved binding and a fresh frame works afterwards.
`notebook/polars.ipynb` validates, and all recorded kernel/worker PIDs were reaped.

`documents/` under each origin archives declarations, lock pairs and receipts.
`*.pty` records the notices, streamed Cargo output and prompts. `*.trace.gz` is a
lossless file/connect trace, not a reconstructed summary. `commands.jsonl`
records setup/check commands; the complete install logs are retained separately.
`checks.json` records the source checkpoint and consumer documents.

Root and tool formatting pass. Tool strict all-target clippy passes in ordinary
and test-support configurations. Serial tool suites pass at 51 and 52 tests,
respectively, with two ignored integration tests in each. The root product is
unchanged from Gate 3; Gate 5 retains responsibility for the full root regression
and matched startup/launch measurements.

Durations in the journals are **not performance results**. Both origin journeys
ran concurrently; their first and combined preparations took about 199 and 206
seconds, and traced second attachments about 9.5 seconds. Installation reused a
build target and pre-existing registry sources. The proof of no second-consumer
compilation is the invocation trap with positive controls, not those times.
For a replay, see `probes/one-install/README.md`; start with the whole target and
results directory absent, not just an individual project's cache.
