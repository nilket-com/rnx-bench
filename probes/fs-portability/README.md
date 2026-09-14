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

Record 0037 adds the actual path-helper module and its registration unit gate.
The path integration tests, including Windows-specific semantic expectations,
remain in rnx; this check does not execute them.

Record 0038 adds the actual time module and its timestamp/registration unit
gates with the specified Jiff Windows features. This remains only a type
check; no Windows execution or whole-application build is claimed.

Record 0044 adds the actual process facade and path/registration unit gates.
Its call into the supervisor is a type-check-only stub; this checks Windows
launch-setting code, not the supervisor or Windows process execution.
