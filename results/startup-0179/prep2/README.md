# 0179 prep2: stopped by a driver guard (retained)

Second S1 run, after the reviewed neutrality repairs. Suites passed on both sources (base 601 / 6, candidate 602 / 7,
no-std clean) and the repaired neutrality control accepted the rebuilt control binary (retained at
`probes/startup-0179/neutrality-bin/prep2-p0-base-primary`, sha256 619d30c3..., the same three enumerated differences).

It then stopped on the first deciding build (`s1.status` = exit 1): the guard "no measured build may carry the
diagnostic cfg" searched the whole verbose log for the cfg's name, and Cargo passes the crate's check-cfg DECLARATION
(`--check-cfg 'cfg(rune_nightly, rune_docsrs, rune_byte_code, rune_startup_inventory)'`) to rustc on every build. The
cfg was not set: the log has no `--cfg rune_startup_inventory` and no RUSTFLAGS. The build itself succeeded; its log is
retained here. No binary from this run is used: the next run rebuilds everything from the start.

Repair (driver only): `build.diagnostic_cfg_uses` ignores `--check-cfg '...'` arguments and rejects any other mention;
control `B1-diagnostic-cfg-guard`.
