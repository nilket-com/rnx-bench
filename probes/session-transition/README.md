# 0063 gate 1 — session ownership and handover prototype

This is an isolated mechanism probe, **not product :dep**. `build.py` archives
rnx `bb3477e`, patches its real entry/REPL stack, and copies the project tool.
The two lockfiles remain identical. It adds no public library API or dependency.
`imports.json` asserts every imported Rust file is unchanged except the three
named root files in `root-integration.patch`; prototype modules are checked in
beside the driver. Build output lives in ignored `target/`.

```sh
python3 probes/session-transition/build.py
python3 probes/session-transition/check.py
python3 probes/session-transition/baseline.py
cargo test --locked --offline \
  --manifest-path probes/session-transition/target/tool/Cargo.toml \
  --bin rnx-transition-tool-probe protocol::tests::framing
```

Tool strict Clippy passes. Root strict Clippy has 13 existing diagnostics;
`build.py` checks the exact diagnostic code, text, primary path and line against
the unmodified root, requiring no new diagnostics. It does not silently suppress
those warnings or modify their sources. The initial scaffold's misplaced module
declarations and the corrected new-code chunk-iteration lint are not product
findings. The inner-doc failure output is retained.

## What is real

- The tool uses the real bounded reader, manifest parser, catalogue selector and
  authoring candidate. Describe does not open the product writer or run Cargo.
- Control is a Unix socket pair, sealed close-on-exec at reception, with a
  network-order u32 frame length, byte version/kind, and unique byte tags followed
  by u32 UTF-8 lengths. Maximum payload is 64 KiB. Message-specific fields are
  checked. Association is a version-1/kind-7 frame hex-encoded in private
  `RNX_INTERNAL_SESSION_V1` (16 KiB binary cap), not a public flag.
- Association carries canonical manifest/tool paths, a runtime/native declaration
  digest, receipt bytes digest, executable content digest and lock bytes digest.
  Root contributes its actual executable path and installed extension names.
  The carrier is advisory local routing metadata, not authentication.
- Describe supplies additions, existing names, owning/proposed manifest, offline
  mode and selected cost facts. Prepare revalidates the description token and
  association. Decline does not allocate scratch or mutate the manifest.
- A started future comes from an external-style 0053 scope registration and is
  polled by a Rune select. Real Session::close and normal Rust drops dispose it,
  a retained native value and the context before main_inner returns. The private
  pending exec is consumed outside that stack, preserving main_with's public
  return type. Failed close does not exec; failed exec does not reopen a prompt.
- Seven ordinary entry comparisons remain byte-identical to the stock executable.

## What is substituted and remains for gates 2–6

- Native roots are metadata-only layout fixtures. The association's lock and
  receipt bytes are **explicit opaque sentinels**, not product format validation
  or proof of a real shared build. The probe isolates staleness classification;
  integration must bind through existing validated lock/receipt/artifact paths.
- Test-only `RNX_PROBE_CONSENT` supplies consent, including the decline case.
  Rustyline consent, nonterminal refusal, interruption and bounded output from
  real Cargo/probe process groups are not claimed here.
- Scratch uses an exclusively created fixed `gate1-session` name to force the
  reservation-race case, an explicit XDG_STATE_HOME, and a marker manifest. Unique
  selection, HOME fallback and a usable scratch application are integration work.
- Prepared output is a fixture-supplied absolute executable. There is no build,
  artifact validation, real startup probe or replacement Rune context yet.
  The successful replacement is a small executable that records its PID; the
  missing executable intentionally exercises the irreversible exec-failure path.
- The protocol's five-second socket timeout is only a probe bound. It does not
  stand in for the plan's 30-minute preparation supervisor or five-second native
  startup deadline. Root kills/reaps the direct helper on a protocol error; full
  subprocess-group cancellation belongs to later gates.

`check.py` retains event sequences and PTY bytes. The 11 groups cover association
staleness, describe/prepare revalidation, read-only scratch description, exclusive
allocation, safe path boundaries, framing refusals, helper descriptor closure
with an inherited-fd positive control, polled-resource preservation on decline
and failed preparation, successful same-PID exec after teardown, cleanup/exec
failures, and missing/incompatible/PATH helper discovery. Temporary fixture
projects are removed after processes exit; the ignored build copies are retained.
