# Record 0039 measurements

Linux nano, i7-14700, Rust 1.98.1. Hyperfine 1.20.0, CPU 4, 10 warmups and 100 runs per command. Pipe output is byte-identical between before f9440eb and after; `conditions.json` retains the check, versions and hashes.

| command | before mean ± σ (ms) | after mean ± σ (ms) |
| --- | ---: | ---: |
| version | 0.554 ± 0.047 | 0.536 ± 0.014 |
| help | 0.541 ± 0.017 | 0.536 ± 0.015 |
| eval | 4.058 ± 0.019 | 4.005 ± 0.024 |
| run | 3.716 ± 0.018 | 3.660 ± 0.021 |
| json | 11.627 ± 0.079 | 11.668 ± 0.226 |

No detected regression; small differences do not establish a speedup.

10,000-character highlighting, 1,000 passes after 100 warmups on CPU 4: median 0.03123 ms, p95 0.03395 ms, maximum 0.56221 ms. The stated acceptance bound is 5 ms per pass; all measured passes satisfy it. Includes building and dropping the styled String.

Release binary: 14,865,000 → 14,875,688 bytes (+10,688). Session startup allocation samples: 1,823,054 → 1,823,053 bytes; the one-byte difference is not a meaningful saving.

The terminal harness preserves raw captures and asserts screens, cursor positions, default attributes, keyword formation/removal and quote deletion, bracketed paste and mixed streams. Specimen images show the same captured screen on two illustrative Tango palettes. Linux is measured; Windows source type-checks in the isolated probe, but the Windows screen/cursor gate remains unexecuted.

Palette chosen after viewing both images: magenta keywords, green strings, cyan numbers; bold keys and prompt; red/bold diagnostic message and red caret. Keys separate the structure of the HTTP object from its strings, punctuation and completion candidates remain foreground, and the error points to the same column in both views. Actual terminal palettes vary.

Final suites under TERM=xterm-256color: 293 default tests and 331 test-support tests, zero failures, run sequentially. Commands and counts are in tests.json.
