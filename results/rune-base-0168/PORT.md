# Scratch migration census

Baseline: rnx 4fbbd3b. Worktree /tmp/rnx-0168-port; only root and project
Cargo manifests and Cargo.lock changed (port-pin.patch). Main bb8e6937 has not
been modified. First correct command:

```
cargo check --all-targets --features test-support,server-runtime
```

It reports 23 lib errors and 30 lib-test errors (some duplicate diagnostics).
These are not 53 independent migrations. The earlier accidental check ran in
baseline rnx and passed; it is retained under setup, not called a main check.
No mechanical source repairs were attempted after the diagnostic capture:
resume semantics and ownership require an audited port, so the four-hour maximum
was not exhausted. No main rnx unit/integration/adapter/project/Jupyter tests ran.

| Change | Consumers reached by the first check | Work and gates before migration |
|---|---|---|
| std Arc versus rune::sync::Arc for Unit/RuntimeContext; fallible construction | config, lib, program, runner, session, server | Separate Rune-held arcs from host std arcs; audit failure propagation, cloning, retained units and reusable invocation slots. Shared ownership and close/retirement tests. |
| FatalDiagnosticKind / kind private | config, runner, program, server, session | Public as_compile_error/as_link_error exist; rewrite extraction without depending on private enum. Preserve spans, retained-input origins and method naming, malformed diagnostics and formatter/session behavior. |
| SourceLoader::load gains an arena parameter | program | Thread the correct arena through custom loader and delegated calls. Module/source origin tests. |
| resume returns VmResume (Future + complete), async_resume removed; VmResult becomes Result | execute and server, tests | Port sync complete and async polling separately. VmResume itself holds awaited state; audit suspension, TLS budgets, cancellation, drain, errors and instruction replenishment. Do not replace resumable execution by unlimited complete(). |
| Vm::without_runtime now Result; native VmResult::panic removed | server lookup, web helper | Propagate allocation/VM failures and convert native errors with preserved semantics; server startup rejection and malformed web-input gates. |
| derive/macro/API changes beyond first checked crate | adapters and generator | Not compiled; compatibility unknown, not assumed from the small harness. Rebuild generated bindings and all conditional configurations. |

consumer-census.json enumerates qualified `rune::` occurrences in production
source by crate (a source-search census, **not a callable count**): core 36 files;
project 1; Polars 57 including generated bindings; Candle 23; Postgres 2;
Polars generator 19. Jupyter has no direct `rune::` references and uses the
worker boundary, so it still needs integration validation after core migration.
Adapter Rune types are accessed through rnx's re-export; updating only direct
Cargo dependencies does not make those consumers compatible.

Estimated work, judgement rather than a measured duration: a dedicated core
migration record covering arcs/diagnostics/loader and budgeted sync/async runtime;
then an adapter/generator compatibility record and Jupyter/server integration
validation. The resume/await audit is the largest unknown; the first failed core
check cannot bound downstream compilation cost. Keep released 0.14.2 shipping
while optimizing the main fork in an isolated harness. Adoption requires the
same contracts and full suites, not a blanket rewrite of type names.

Baseline release test-support + server-runtime suite: 51 successful test-result
summaries, 523 passed, 0 failed, 3 ignored including doc tests. This record did
not separately rerun standalone project, Polars, Candle or Jupyter suites on old;
those current historical passes are not newly claimed here. Main all are
blocked/not run because the core cannot compile.
