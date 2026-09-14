# Record 0040 numbering

Before is rnx `15289db`. Preserve its release binary before rebuilding.
The measurement runner records exact run/eval/version/help/workload equality,
hashes, tool versions and allocation samples, then runs hyperfine on CPU 4
(10 warmups, 100 samples). Run from the bench root:

```
python probes/numbering/measure.py /path/to/before ../rnx/target/release/rnx
python probes/numbering/terminal.py ../rnx/target/release/rnx results/numbering_0040
```

The terminal harness reuses `colour/terminal.py`'s Linux PTY/emulator and image
renderer (its pinned requirements apply). It compares numbered screens and
cursor positions under never/always, exercises old code after renumbering,
consecutive renumberings, reset, and stdout redirection. Captures are raw ANSI
and escaped bytes; both image backgrounds represent the same terminal screen.
This is Linux evidence, not Windows console execution.

The regular Rust suite separately gates admission, rejection, cancellation,
result markers and retained origins. The test totals and commands are preserved
with the results. Memory snapshots deliberately are observations, not equality
assertions: history and presentation can allocate.
