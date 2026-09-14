# Record 0043: session-only revision

Measured on nano, Linux x86_64, 2026-09-14, Rust 1.98.1, Rune 0.14.2,
hyperfine 1.20.0. CPU 4, 10 warmups, 100 runs per command. All columns include
an `env RNX_CONFIG=...` executable; do not compare these absolute times with
bare-binary tables. Means ± standard deviations. Before is ba74e00 with no
config selected; after narrows loading to bare rnx/repl, including piped sessions.

| Command | Before, absent (ms) | After, absent (ms) | After, configured (ms) |
| --- | --- | --- | --- |
| version | 1.577 ± 0.028 | 1.573 ± 0.018 | 1.564 ± 0.019 |
| help | 1.570 ± 0.015 | 1.567 ± 0.023 | 1.560 ± 0.021 |
| eval | 5.088 ± 0.058 | 5.021 ± 0.038 | 5.014 ± 0.022 |
| run | 4.756 ± 0.038 | 4.679 ± 0.059 | 4.745 ± 0.349 |
| json | 12.557 ± 0.118 | 12.549 ± 0.088 | 12.584 ± 0.142 |
| session | 4.802 ± 0.099 | 4.724 ± 0.027 | 7.487 ± 0.042 |

No config-related one-shot overhead detected. Outliers were reported, including
the configured run samples; these are observations, not proof of zero CPU cost.
The structural evidence is the zero open-attempt counter for run/eval/version/help.
The configured session mean is about 2.8 ms above absent and meets the preselected
local gate of absent + 10 ms. This is not a universal latency guarantee.

Binary bytes: 14980152 → 14980216.
Session startup allocation reference, before: 1823272 bytes.
Session startup allocation reference, after: 1823288 bytes.
Session startup allocation reference, configured: 1823662 bytes.
These are allocator-request observations, not resident memory.

All six measured command outputs and exit statuses are checked before timing.
The full suites pass sequentially: 324 default and 363 test-support. tests.json
records commands and isolated environment. Config tests assert zero opens for
run/eval/version/help and one for bare rnx/repl; valid, malformed and looping
configs leave one-shot output/status identical under all three colour flags.
Palette equality tests now exercise sessions. Existing terminal palette behaviour
is unchanged; its specimens remain in ../settings_0043/. Original raw timing
exports are preserved there, explicitly labelled as the old scope.
Windows execution remains unverified.
