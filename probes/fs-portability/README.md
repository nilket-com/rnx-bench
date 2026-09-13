# Filesystem portability type check

Record 0035, Codex, nano, 2026-09-13. This crate includes the actual fs and
fs_platform source from the sibling rnx checkout, with just the host-registration
record and error alias supplied here. It isolates the new filesystem code from
reqwest/ring, whose MSVC cross-build requires tools absent on nano.

```
cargo check --locked --manifest-path probes/fs-portability/Cargo.toml --tests --target x86_64-pc-windows-msvc --features test-support
```

This checks Windows filesystem types. It neither executes Windows tests nor
checks the entire application. The independent lockfile is preserved; this is
not an assertion that every dependency matches rnx's lockfile.

Record 0036 adds the actual environment module to the same isolated check.
The environment and filesystem unit gates are type-checked on Windows;
no Windows execution or whole-application build is claimed.
