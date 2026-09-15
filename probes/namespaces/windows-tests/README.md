# Windows integration-test compilation only

This package references the actual migrated rnx integration tests. Its binary
is an intentionally unusable placeholder to supply Cargo's executable-path
variable. Never run these tests here. This checks Rust expressions, format
strings, Windows API types and test source compilation, not generated Rune
programs, the real supervisor, or any Windows runtime behavior.

```
cargo check --locked --tests --features test-support,count-allocations --target x86_64-pc-windows-msvc
```

The independent lockfile is preserved; it does not assert dependency identity
with rnx. The root check still stops at ring's missing MSVC `lib.exe` tool.

The standalone harness explicitly enables `Win32_Security`, required by
`CreateProcessW` in the existing console fixture. This is not a check of
rnx's full resolved Windows feature graph.
