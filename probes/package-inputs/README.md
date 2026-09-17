# Record 0057 gate 2: input contracts and runner handoff

The root's real feature-gated runner accepts a bounded version-one source map.
The separate tool has internal manifest/lock/map parsing, graph expansion, wrapper
generation and capability probing; its product lock/build/run commands are not
implemented yet. Hash strings in a decoded lock are syntax, not verified inputs.

Run from rnx, sequentially:

```sh
cargo test --locked --manifest-path tools/project/Cargo.toml
cargo test --locked --features project-sources,test-support --test project_sources -- --test-threads=1
RNX_GATE2_BINARY="$PWD/target/debug/rnx" cargo test --locked --manifest-path tools/project/Cargo.toml manifest_to_runner_handoff -- --ignored --test-threads=1
cargo clippy --locked --manifest-path tools/project/Cargo.toml --all-targets -- -D warnings
python3 tools/project/scripts/notices.py --check
TERM=xterm cargo test --locked -- --test-threads=1
TERM=xterm cargo test --locked --features test-support -- --test-threads=1
TERM=xterm cargo test --locked --features test-support,server-runtime,project-sources -- --test-threads=1
```

From rnx-bench, `python3 probes/package-inputs/capability.py` builds a tiny
public-API extension app, checks that its version handshake opens no config and
invokes no builder, then runs eval as the builder-positive control. Set
RNX_GATE2_OLD_BINARY to a saved executable without project-sources; the original
run used the accepted pre-feature release binary whose hash is in capability.json.
The script refuses if that control unexpectedly supports the handshake. This is
a source-only fixture using rnx's existing dependency graph and license notices.
The native-generation tests compare exact Cargo/main strings and parse the Cargo
TOML. Building a project through the generated workflow remains a later gate.

Results are in results/package-inputs-0057. Full suite counts include root tests
and doc tests; the tool's explicit ignored integration test is run separately,
never counted as a vacuous pass. Tool Windows checking is not Windows execution.
No startup or bit-reproducibility claim is made.
