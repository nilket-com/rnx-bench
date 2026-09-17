# 0058 gate 4: generated Polars application

Prerequisites: the accepted product rnx-project, stock rnx, rnx-jupyter and the
private `probes/jupyter-notebook/.venv` from 0047. No new Python packages are
required. Build the adapter configurations serially, preserving the marked test
binary before restoring the ordinary binary:

```sh
mkdir -p probes/polars-assembly/target
cargo build --release --locked --features test-support --manifest-path ../rnx/adapters/polars/Cargo.toml
cp ../rnx/adapters/polars/target/release/rnx-polars probes/polars-assembly/target/rnx-polars-test
cargo build --release --locked --manifest-path ../rnx/adapters/polars/Cargo.toml
probes/jupyter-notebook/.venv/bin/python probes/polars-assembly/check.py
```

The native inventories require tracked working-tree files. Stage any new adapter
files before running; do not edit rnx inputs during lock/build/run. The fixture
copies the checked-in example to a temporary project outside the native roots,
substitutes absolute native paths, seeds compilation objects only, and uses the
real product commands. No lock or receipt is seeded. The resolved Polars feature
node must match gate 2's accepted graph, including implied upstream features.
Generated sources, locks, receipt and outputs are archived for review. Locks
contain temporary absolute paths; they are evidence, not reusable project locks.

The ordinary and generated executables run eval, async-promoted eval and a piped
session with failure/recovery/reset. A test-support-only marker observes zero
builder calls for version/help/selfcheck and one for a resetting session whose
config cannot resolve Polars. Ordinary builds ignore that marker variable. Stock
rnx refuses Polars.

The generated artifact is installed through rnx-jupyter into a private kernelspec
directory using the existing Environment fixture. Real jupyter_client cells show
failure recovery, native opacity, preview and restart: the saved binding is gone,
while a fresh frame can be read and previewed. The notebook is saved and validated.
Kernel/worker PIDs are sampled and must be gone after normal shutdown; private
installation and project directories are removed. User Jupyter directories are
not touched. There is no browser or performance claim at this gate.

Run reruns with care: the driver replaces `results/polars-assembly-0058/` evidence.
Restore tracked results afterwards. It creates no working files beside the
checked-in example. The ignored `target/` holds only the copied test binary.
