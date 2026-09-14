# Record 0043 settings evidence (original scope)

This is historical evidence for the original run/eval/session config scope.
The session-only revision is measured in ../settings_0043_session_only/.
These raw results have not been rewritten to describe the new implementation.

Measured by Codex on nano, Linux x86_64, 2026-09-14, Rust 1.98.1,
Rune 0.14.2, hyperfine 1.20.0. CPU 4, 10 warmups, 100 samples per command.
Every command goes through `env RNX_CONFIG=...` to vary config in the same run;
that executable's launch overhead is included in ALL columns. Absolute times
are therefore not comparable to earlier bare-binary startup tables. Means ±
standard deviations below; commands, hashes, config and raw samples accompany it.
Before is the accepted 0042 release, 9e17aad; after implements plan b5cc08c.

| Command | Before, absent (ms) | After, absent (ms) | After, six colours (ms) |
| --- | --- | --- | --- |
| version | 1.575 ± 0.023 | 1.559 ± 0.017 | 1.562 ± 0.020 |
| help | 1.571 ± 0.021 | 1.573 ± 0.039 | 1.566 ± 0.019 |
| eval | 5.096 ± 0.026 | 5.017 ± 0.017 | 7.743 ± 0.035 |
| run | 4.759 ± 0.027 | 4.682 ± 0.029 | 7.417 ± 0.034 |
| json | 12.714 ± 0.164 | 12.504 ± 0.104 | 15.197 ± 0.100 |
| session | 4.803 ± 0.028 | 4.729 ± 0.029 | 7.506 ± 0.128 |

The six-colour config adds about 2.8 ms to the session mean. This passes the
preselected local gate: configured session <= absent session + 10 ms. That is a
measurement tolerance on this machine, not a universal startup promise. No
regression is detected without a config in this run; small decreases are not
attributed speedups. version/help timings are independent of whether the config
file exists, and the test-support open counter establishes zero config attempts.

Binary bytes: 14,916,704 → 14,980,152 (+63,448). Session allocation startup
reference: before 1,823,272; after absent 1,823,288; configured 1,823,662 bytes.
These are allocation request observations, not resident memory. Palette strings
remain; the config context, unit, VM and returned value are dropped.

Both final suites pass sequentially, 324 default and 363 test-support, under
TERM=xterm-256color and an isolated missing RNX_CONFIG override. Gates that test
config supply their own paths. tests.json preserves commands, environment and
counts. Screen/cursor equality under never/always and raw RGB prompt/keyword
checks are in terminal.json and the captures. The same configured RGB palette
is rendered on two example backgrounds. Light-background contrast is lower for
these chosen pastel values; choosing hex does not promise contrast on all themes.
Linux execution only; Windows gates are authored but unexecuted.
