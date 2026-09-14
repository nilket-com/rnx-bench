# Record 0040: numbered sessions

Measured by Codex on nano, Linux x86_64, 2026-09-14, Rust 1.98.1,
Rune 0.14.2, hyperfine 1.20.0. CPU 4, 10 warmups, 100 samples per command.
Before is rnx 15289db; after implements plan bdb64d6. Binary hashes, sizes,
exact commands, output-equivalence checks and allocation samples are in
conditions.json. These measurements precede formatting-only cleanup of new
Rust blocks and a test-only PTY wait optimization; the final suites follow both.

| Command | Before mean ± σ (ms) | After mean ± σ (ms) |
| --- | --- | --- |
| version | 0.557 ± 0.022 | 0.547 ± 0.019 |
| help | 0.560 ± 0.016 | 0.551 ± 0.017 |
| eval | 4.062 ± 0.027 | 4.036 ± 0.085 |
| run | 3.718 ± 0.016 | 3.670 ± 0.019 |
| json | 11.774 ± 0.118 | 11.568 ± 0.101 |

No startup regression detected in this run. The small decreases are observations,
not an attributed speedup. Whole-process times include startup and shutdown.
Binary size: 14,875,400 → 14,878,872 bytes (+3,472).
Session startup allocation reference: 1,823,054 → 1,823,086 bytes (+32).
The later :memory sample is 1,831,667 → 1,831,714 bytes; it includes presentation.
These are allocator request bytes, not resident memory.

Both final suites pass under TERM=xterm-256color: 304 default, 342 test-support.
Their commands and totals are in tests.json. Terminal captures and terminal.json
preserve 14 equal screen/cursor checkpoints under never/always and the redirected
stdout checks. specimen-dark.png and specimen-light.png show the same session.
This is Linux execution evidence; Windows remains unexecuted.

Reproduction commands and pinned terminal-harness dependencies are linked from
../../probes/numbering/README.md. The ordinary pipe transcript and all five
measured command outputs retain exact stdout/stderr and successful status.
