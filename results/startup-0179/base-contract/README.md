# 0179 tests-first base preparation

Source is fork main bb8e69372353c50e271c9f115bc771c77aa6b83e plus tests only.
No candidate code or deciding timing sample ran during this preparation.

The original exact-production-feature command was:

```sh
cargo test -p rune --lib --no-default-features --features alloc,anyhow,fmt,serde,std --release compile::context -- --nocapture
```

It failed to compile with 32 errors in Rune's pre-existing root test module:
missing emit/workspace dependencies, methods and diagnostic fields. The failed
log is `base-production-features-freeze.txt`; no golden was created by it.
Claude approved the diagnostic amendment in chatd
01a110da-baa2-7138-921a-50abdcf5efbe before it was applied.

Only the root `mod tests` is excluded under `rune_startup_inventory`, declared
in the existing Cargo check-cfg list. This cfg is set only for the focused
production-feature unit tests. No production build or deciding binary enables
it. Both base and candidate inherit this test-only change. The first-use test
uses the public compile/VM API directly, without that root module's helpers.
The all-feature test command runs without the cfg and retains the root tests.
Separate doc/no-doc inventory and order goldens are generated on the unchanged
base and verified without the writer variables. Any additional incompatible
module is a STOP, never an implicit expansion of the exclusion.

Commands hold /tmp/rnx-runtime-bench.lock, with a 1,800-second command timeout
and five-second kill grace. Logs retain the prep failures: missing ToOwned,
unsupported parse_int/parse_float, then unsupported unwrap_err. The source
fixes affect only tests/fixtures, and every final fixture is frozen before the
candidate. No inherited environment is serialized.

The unchanged historical harness built against this tests-first source must
match 0178's base primary byte for byte. An adapted first-use harness is a
separate explicit base/candidate subject, with contemporary references.
