# Record 0045: input, output and frame

Using the pinned dependencies in `../colour/requirements.txt`:

```
python probes/number-colours/terminal.py /absolute/before/rnx /absolute/after/rnx
```

Captures a real Linux pty session, compares plain before/after output and
never/always screen text and cursor positions, and writes raw captures plus
PNG specimens to `results/number_colours_0045`.

The specimens use Tango's normal ANSI palette, DejaVu Sans Mono, and dark
`#202428` / white backgrounds. Pyte 0.8.2 does not track faint intensity;
this probe extends its cells to track SGR 2/22/0, with a self-check that RGB
channels are not misread as attributes. The renderer illustrates faint with
a 50% foreground/background blend. That blend is an explicit visual model,
not a claim about what a physical terminal does. The raw bytes prove the
faint request. Bright/bold colour substitution by real terminals may differ.

Default blue is ANSI blue, not bright-blue. The captured normal blue was
readable on these two specimen backgrounds; no universal contrast claim or
Windows execution evidence is implied.
