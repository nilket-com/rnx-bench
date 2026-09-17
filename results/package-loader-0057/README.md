# Record 0057 gate 1

Submitted for review. This checkpoint implements internal mapped loading and
source-graph expansion. It does not implement the project command, manifest
parsing, lock/build/run, fingerprinting or the CLI handoff.

| Check | Result |
| --- | --- |
| Default root suite | 375 passed |
| test-support root suite | 418 passed |
| test-support + server-runtime + project-sources | 431 passed |
| Private graph core | 6 passed |
| Tool clippy, warnings denied | pass |
| Root and tool formatting | pass |
| Root notices | current |
| Tool Windows check | type-check only, pass |
| Root all-target clippy | inherited failure, status 101 |

The clippy baseline is 73fd306, the accepted plan before implementation. It and
the implementation emit the same sorted diagnostic headlines: the two denied
non-octal-permissions lints and existing warnings. Neither root clippy run is
claimed clean. No new-file diagnostic. Baseline worktree was removed afterwards.

`conditions.json` records code identities, compiler and check totals. Logs are
retained in this directory. Root evidence describes the fixture observations;
reproduction commands are in `probes/package-loader/README.md`. No release-binary
mapped run, Windows execution or performance measurement is claimed at gate 1.
