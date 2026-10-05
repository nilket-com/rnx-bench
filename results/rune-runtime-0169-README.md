# 0169 retained observations

The deciding data is attempt5b. Read its REPORT.md with CLOCK-AUDIT.md and
rnx plans/0169_complete_startup_attribution_evidence.md. The original run.sh
exited1 after its main analysis passed, because the mutation-control hard-link
clone crossed filesystems. The approved unchanged read-only replay passed17
controls; COMPLETE-AFTER-CONTROL-REPLAY records that qualification.

All deciding observations, failed attempts, raw ledgers, plan receipts,
diagnostics and original failure logs are preserved byte-for-byte in
rune-runtime-0169-raw.tar.xz. Selected summaries also remain plain files.
From the repository root:

```sh
tar -xJf results/rune-runtime-0169-raw.tar.xz
sha256sum -c results/rune-runtime-0169-SHA256SUMS
```

Do not extract over deliberately edited evidence. Full reanalysis uses the
pinned producer source2f58d0b and rebuilt hash-matched binaries at their recorded
locations. Serial-integration maps retain equivalent rebased probe sources.
Run final controls with TMPDIR on the results filesystem; the source is unchanged.
Copied historical executable diagnostics are local build artifacts, not committed
binaries; their hashes are in the archived rustc-42/binary-hashes.json.

Archive SHA256: 5fe0e42027b16def49e1a8683efb86fb9cb46bb04ffdd37df03d42de1bb4d7a2
