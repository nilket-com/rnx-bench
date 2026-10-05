# Clock scope for the standing report

Read this with REPORT.md. Resident native clock: one measuring observer per
ordered block, each subject is a fresh process. The interval includes fresh
spawn, pipe capture and blocking wait. No overhead is subtracted.

| Calibration | Native median ms | Hyperfine pipe median ms | Difference ms |
|---|---:|---:|---:|
| true | 0.257468 | 0.282602 | −0.025134 |
| cached Rust 42 | 0.3536245 | 0.368636 | −0.0150115 |

Both pass the unchanged 0.15 ms agreement bound; this is not a precision claim
below that bound. In particular Lua54 answer 0.436 ms and LuaJIT answer 0.464 ms
are measured by this resident observer, not interchangeable with historical
Hyperfine or per-helper native rows without noting observer scope. Earlier
per-invocation diagnostics showed systematic +0.11–0.15 ms offsets (and failed
larger offsets). Those offsets are not corrections to subtract from any row.

The original run.sh exited 1 only after the main analysis passed, because its
corruption-control clone crossed filesystems. COMPLETE-AFTER-CONTROL-REPLAY
records the approved replay, not a successful original run.sh exit. The failed
control log and separate command/environment/status ledger are retained.
