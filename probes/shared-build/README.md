# Shared compilation probe (toward record 0069)

Which compilation work between the launcher, an assembly and the next assembly
can Cargo actually reuse, and what would a shared build directory demand?
Product rnx `c6d8a1c` (0068 closed). Everything is driven by the exact
commands the tool runs (`cargo build --locked --release --target-dir`) on the
assemblies the tool generated, so no product change is needed to measure.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/shared-build/build.py      # assemblies, discriminated twins, the 0061 retained-output native; exact package overlap
python3 probes/shared-build/install.py    # cargo install --git: plain, and with the canonical shared directory retained
python3 probes/shared-build/reuse.py      # private vs shared (one canonical path, snapshots restored into it); wrong-binary control; discriminated wrappers both orders; seeded; install→Polars
python3 probes/shared-build/lifetime.py   # the retained-output consumer across later builds, a native change, and removal
python3 probes/shared-build/collect.py
```

Run alone: about ten cold Polars-class builds (~110 s each), several warm ones and two installs.
Everything lives under `probes/shared-build/target` (tens of GB while running)
and `results/shared-build-0069`.
