Record 0034 registration measurement. Imports ../rnx/src/http.rs (the
implementation worktree) to measure installation of its four functions.
It never creates a reqwest client and never uses the network. Runtime and
host metadata types are stubbed only for unused interfaces.

CARGO_TARGET_DIR=../rnx/target cargo build --release --locked --manifest-path probes/http-registration/Cargo.toml
taskset -c 4 ../rnx/target/release/http-registration

Output: results/http_0034_registration.txt; mean of 100 in-process
constructions, destruction excluded. This probe has its own lockfile and
is not a matched whole-rnx startup measurement; see http_0034_startup.json
for the latter.
