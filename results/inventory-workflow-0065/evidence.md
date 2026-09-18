# 0065 gate 2: current-format workflows and format-only timing

Product checkpoint: rnx `a7c3f7db4db8e0a00c7de59a1129d9f531577ae0`.
Full review narrative and tables:
`rnx/plans/0065_a_launch_checks_each_native_file_once_workflow_evidence.md`.
Reproduction: `probes/inventory-workflow/README.md`.

- 16 current-format command groups and 37 publication cases pass.
- Genuine old shared lock 2/receipt 3 and override lock 1/receipt 2 refuse with
  exact quoted recovery commands and unchanged old payloads.
- Real Polars shared and override run/eval/session journeys pass. Second
  consumers attach to the same key with compilation trapped and a positive
  control.
- Tool fmt, strict clippy and 46 tests in each configuration pass; notices
  unchanged/current. Root code and all dependency files unchanged from gate 1.
- 3,000 matched launch samples, plus 120 full-verification attachment samples.
  Each artifact has its own direct control. Cargo lock bytes match exactly.
- Eval overhead over direct at zero/one/two/three adapters is approximately
  12.2/16.2/20.0/23.7 ms versus 17.6/22.4/26.5/30.6 ms before. The runtime
  floor is 443 files / 6,988,177 bytes and constant across the roster.
- One-native full verify is about 58.6 ms versus 95.4 ms; attachment about
  192 ms versus 264 ms. Those are separate from ordinary launch.
- No nested-root reuse has landed; its slope gate stays open.

`source.json` pins the signed source checkpoint and binaries; `tool.patch`
preserves the difference from 22b9386. `completion.json` validates all cells,
input equality and observed improvements. Raw commands, journals, generated
replay scripts and traces are retained alongside their summaries.

The 3,000 preliminary samples under `graph-drift-preliminary/` are retained but
excluded from the matched claim. Fresh resolution selected two newer cached
build dependencies. The corrected setup seeds the accepted Cargo bytes and
reruns all builds and samples. Neither the user’s scratch projects nor runtime
installation store was used. Installation migration is gate 3.
