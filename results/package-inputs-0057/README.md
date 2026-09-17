# Record 0057 gate 2

Submitted for review. Source-map CLI handoff and private tool input machinery
are implemented. Fingerprinting, content verification, product commands, Cargo
build orchestration, lock publication and receipts remain later gates.

| Check | Result |
| --- | --- |
| Root default | 375 passed |
| Root test-support | 418 passed |
| Root all three optional test/server/project features | 437 passed |
| Tool ordinary tests | 14 passed, 1 explicitly ignored integration |
| Explicit tool-to-runner integration | 1 passed separately |
| Targeted CLI rerun | 3 passed |
| Public-API capability fixture | pass, builder/config positive controls |
| Root/tool formatting | pass |
| Tool clippy with warnings denied | pass |
| Root clippy | same inherited status 101 and diagnostic headlines as gate 1 |
| Root/tool notices | current |
| Tool Windows | type-check only |
| Default dependency graph and features vs c8fb102 | identical |

The complete suites preceded a one-line, behavior-equivalent println cleanup
for clippy. The targeted CLI tests, capability fixture, explicit integration
and clippy were rerun after it. The earlier lib.rs SHA is recorded in
full-suite-lib-sha256.txt. No full rerun or timing measurement is implied.

The fixture verifies the early command does not invoke its extension builder
or read presentation config; eval provides the builder-positive control. It
also records an accepted older executable refusing the new command. Native
wrapper generation is string/TOML-tested here; the product native-build path
remains gate 4. Tool lock parsing checks schema and bounds, not digest truth.

Commands: probes/package-inputs/README.md. Full interpretation and limits:
rnx/plans/0057_a_project_declares_what_its_executable_contains_inputs_evidence.md.
