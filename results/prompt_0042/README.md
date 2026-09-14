# Record 0042 evidence

Measured on nano, Linux x86_64, 2026-09-14, Rust 1.98.1, Rune 0.14.2.
Hyperfine 1.20.0, CPU 4, 10 warmups, 100 samples. Means ± sample standard
deviation; raw exports, binary hashes and allocation observations are alongside.

| Command | Before ms | After ms |
| --- | --- | --- |
| version | 0.556 ± 0.017 | 0.540 ± 0.016 |
| help | 0.548 ± 0.015 | 0.537 ± 0.014 |
| eval | 4.061 ± 0.012 | 4.024 ± 0.056 |
| run | 3.733 ± 0.065 | 3.679 ± 0.019 |
| json | 11.625 ± 0.123 | 11.607 ± 0.100 |

Binary bytes: 14879080 → 14916704.
Outliers were reported; these samples are not an attributed speedup.

Both final suites pass: 313 default, 351 test-support, TERM=xterm-256color.
The terminal probe asserts row-zero clear, retained bindings, screen/cursor
equality with colour on/off, and title push/set/pop protocol. The emulator does
not implement title stacks, so no restoration of an actual emulator title is
claimed. Regular PTY tests cover quit, EOF, prompt Ctrl-C, run completion, error
and host::exit. Windows execution remains unverified.
