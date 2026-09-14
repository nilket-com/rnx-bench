# Terminal presentation, record 0039

The application adds no resolved package: unicode-ident, now a direct dependency,
was already brought in by Rune. This probe uses pyte to interpret
actual Linux PTY output into a screen/cursor, and Pillow to render the captured
specimen with Tango's normal ANSI colours on light and dark backgrounds.
The specimen's CJK glyph uses Droid Sans Fallback; other glyphs use DejaVu Sans
Mono. These are illustrative terminal palettes, not colours hardcoded in rnx.

Install `requirements.txt` in a Python venv. From the bench root:

```
python probes/colour/terminal.py ../rnx/target/release/rnx results/colour_0039
python probes/colour/measure.py /path/to/before ../rnx/target/release/rnx
cargo run --release --locked --manifest-path probes/colour/portability/Cargo.toml > results/colour_0039/highlight.csv
cargo check --locked --manifest-path probes/colour/portability/Cargo.toml --target x86_64-pc-windows-msvc
```

The measurement command pins hyperfine and its children to CPU 4. Pin the
highlighter probe to CPU 4 too when reproducing the committed CSV. Before is
rnx f9440eb; rebuild it into a separate target directory. The before binary's
hash matches record 0038's after hash. Conditions record hashes, sizes, versions,
commands, output equality, and session allocation samples. No review notes live
here.

`portability` imports the actual presentation source. Its Windows check excludes
unrelated reqwest/ring compilation, so it establishes only type correctness of
that module, not a full Windows rnx build or console execution.

Terminal gates compare each screen and cursor after the same editing operations
in always/never modes, check token colours during keyword formation/removal and
quote deletion, preserve a 10,000-character bracketed paste, check idle/default
attributes, and exercise mixed stdout/stderr redirection. Raw traffic is retained;
redraw byte sequences are not compared. The elapsed wait for an edit to settle
is a fixture wait, not the highlighting benchmark. The terminal harness is Linux
only; Windows screen/cursor execution remains unverified.
