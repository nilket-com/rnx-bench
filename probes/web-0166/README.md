# Bounded web helper probe

The sources port the unchanged 0165 skeleton from manual helpers to built-in
web helpers. Run with stock rnx; no adapter or production deployment is involved.
Before load, all 26 retained 0162 wire fixtures and three keep-alive responses
must pass. The single new binary serves both sources, pinned to CPUs 2,4;
oha uses 8,10,12,14. Source hashes, binary hashes and complete raw evidence are retained.

Copy the reviewed release binary to target/stock and b4cc0a6 to target/baseline.
Run from this repository:

```
python3 probes/web-0166/handler_controls.py probes/web-0166/target/stock
python3 probes/web-0165/host_controls.py probes/web-0166/target/stock
python3 probes/web-0164/host_controls.py probes/web-0166/target/stock
python3 probes/web-0166/run.py NEW_DIRECTORY
python3 probes/web-0166/validate_saved.py NEW_DIRECTORY
python3 probes/web-0166/saved_controls.py NEW_DIRECTORY
python3 probes/web-0166/count.py
python3 probes/web-0166/preflight_controls.py /path/to/exclusively-owned/rnx-checkout NEW_CONTROL_DIRECTORY
RNX_STARTUP_OUT=NEW_STARTUP_DIRECTORY python3 probes/web-0166/startup.py
```

The census uses Rune 0.14.2's AST spans and lexer, including `?` tokens inside
template expressions. It counts declarations by category; content includes
rendering calls whose helper spellings change, and constants and routes remain
identical. Character counts include whitespace and literal data, not an assertion
about human readability. Neither the Rust host boilerplate nor file formatting
is credited to helper removal. This record does not format `.rn` sources.

Round 0 evidence is preserved under results/web-0166/round0; the revised
String escape/type-preserving response evidence is under round1.
