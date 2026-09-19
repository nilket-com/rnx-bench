# 0067 gate 3 evidence

See [the driver instructions](../../probes/git-source-workflow/README.md).
All final correctness drivers passed. This is a private-origin integration gate,
not the published fresh-user or release-timing gate.

- `product.json` and `product.patch`: workflow-tested source against `1f7ca46`.
- `fixture.bundle` and `real-setup.json`: acquired one-binary fixture, real source
  revision recoverable from the bundle and the named base. Its repository URL is
  the only additional manifest change.
- `final-product.json` / `final-product.patch`: final annotation-reader correction;
  no launch/acquisition/publisher code changed after the workflow runs.
- `annotations.json`, `final-tool-checks.log`, `final-selfcheck.log` and
  `final-git-eval.log`: focused checks on that final tool.
- `projects/`: actual declarations, full Cargo/project lock pairs, receipts and
  application scripts for the real and mixed/legacy cases.
- `suite-counts.json`, `checks.json`, `commands.jsonl`: aggregate and raw evidence.
  Ordinary/support tool counts are 51/52; the support child test is not counted
  twice. Root default/support/runner counts are 376/419/389.
- `real-journeys.json` and PTY transcripts: fresh compilation then network-disabled,
  compiler-trapped attachment. The final cold journey took 561 s with four CPUs
  and concurrent correctness builds; this is not a timing claim or gate-5 sample.
- `publication-replay/`: all 37 original shared-publication assertions, with the
  stub declaring the count-allocations feature already required since gate 2.
  Product-specific Git publication, receipts and interruption are checked
  separately in `publication.json` and `concurrency.json`.
- `storage-removal/`: 42 filesystem cases, six real namespace mount shapes;
  `storage-migration/`: 30 authentic old-install migration cases;
  `legacy-resume/`: actual old-tool same-key rebuild survives resume.
- `stock-*` / `compat-*`: 44 preparation, 17 startup and eight commitment cases
  for each frontend. Source/effective scripts identify their retained assertions.
- `acquisition.json`: lock reports Cargo reset, authenticates after it, and rejects
  an injected post-Cargo edit without publishing. Build/verify refuse without repair.
- `real-everyday.trace`: actual Polars Git launch with no native content open,
  Git/Cargo/rustc exec or Internet connection. No source-read absence is inferred
  from timing.
- `cleanup.json`: no remaining fixture process. Namespace fixtures exited too.

`development/` preserves the initial source and Cargo-repair finding. The policy
was resolved explicitly by the user: acquisition belongs to lock; verification
never repairs. The initial migration replay's obsolete command-spelling assertion
and publication stub's missing feature are retained beside their corrected runs.
The annotation test initially omitted the empty store's required writer-lock file;
its fixture setup now includes it. No ownership or rejection assertion was relaxed.

Git working-tree trust on ordinary launch, ignored outputs, non-atomic checks,
and missing checkout refusal remain deliberate qualifications. The combined
Git/path assemblies exercise the Polars pipeline and PostgreSQL registration;
private-cluster SQL transactions and the published-origin install are gate 4.
