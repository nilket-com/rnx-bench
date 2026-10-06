# 0179 complete first-use fixtures

Both scripts finish with integer 42. The stdio variant additionally calls the
native print function with an empty string, so script output stays empty.
The no-stdio variant imports the namespace, whose printer functions are
intentionally absent. Both are validated on the unmodified base.

Reviewed new harness mode `first-use <true|false> <script>`, using the existing
source compilation and async execution paths, with `Context::with_config(true)`
/ `false`. Pass `()` as main's argument, retain the existing 1e9 budget, require
returned i64 == 42, then print `FIRST-USE 42\n` from Rust. This validates the return
instead of silently black-boxing it. Both whole cold paths are deciding workloads.
The driver owner reviews/freezes the adaptation before measurements.

manifest.json maps all 34 constructor factories to concrete probes. Some factories
expose namespace/reexports or native types with no public constructor; these have
explicit compilation/type-reference probes rather than invented runtime calls.
This is coverage of factory capabilities, not of every standard-library method.

Copies in Rune's tests and bench must have identical bytes/hashes; no formatter or
fixture edit after freezing without prior review. The base preparation corrected
`.parse_int`/`.parse_float` to generic `.parse` and replaced unsupported
`Result.unwrap_err` with an Err match. Failed preparation logs are retained;
no performance samples or candidate code ran during that preparation.

The in-crate base tests use futures_executor::block_on and async_complete with
main argument `((),)`, default Options and Diagnostics. They do not impose a VM
budget; the deciding harness explicitly applies the existing 1e9 budget. Both
variants emit no script bytes; the host emits exactly `FIRST-USE 42\n`.
