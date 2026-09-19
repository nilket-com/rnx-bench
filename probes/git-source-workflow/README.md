# 0067 gate 3: product Git-source workflow

These drivers exercise the product commands and raw verifier. Tiny Rust fixtures
make fault matrices affordable; `real_setup.py`, `real_journey.py`, `combined.py`
and `path_combined.py` compile the real runner and adapters. The private fixture
origin changes only the package repository URL, so an actual `cargo install
--git ... --rev ...` records acquired coordinates. It is not the published-origin
fresh-user gate (gate 4), and debug checks are not startup measurements (gate 5).

Run from the bench root with Cargo, Git, Rust, strace and bubblewrap installed.
The second real consumer uses bubblewrap's network namespace and real compiler
traps with positive controls. No private PostgreSQL cluster is needed here: the
combined build checks registration and the shipped Polars CSV/Parquet pipeline;
typed SQL journeys remain gate 4.

Use a fresh **whole** `probes/git-source-workflow/target` and a fresh results
directory. Move previous evidence aside first; do not overwrite a previous
journal or resume part of a matrix. The ignored target is disposable and contains
all scratch projects, Cargo homes, fixtures and stores. Registry sources are
shared through a symlink to the user's existing registry cache. Builds can use
several GB and take minutes. Nothing below targets is a user project or store.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/git-source-workflow/prepare.py
python3 probes/git-source-workflow/vectors.py
python3 probes/git-source-workflow/contracts.py
python3 probes/git-source-workflow/acquisition.py
python3 probes/git-source-workflow/verification.py
python3 probes/git-source-workflow/publication.py
python3 probes/git-source-workflow/publication_replay.py
python3 probes/git-source-workflow/concurrency.py
python3 probes/git-source-workflow/mixed.py
python3 probes/git-source-workflow/legacy.py
python3 probes/git-source-workflow/legacy_resume.py
python3 probes/git-source-workflow/storage_replay.py migration
python3 probes/git-source-workflow/storage_replay.py removal
python3 probes/git-source-workflow/real_setup.py
python3 probes/git-source-workflow/real_journey.py
python3 probes/git-source-workflow/launch_trace.py
python3 probes/git-source-workflow/annotations.py
python3 probes/git-source-workflow/combined.py
python3 probes/git-source-workflow/path_combined.py
for frontend in stock compat; do
  for matrix in preparation startup commit; do
    python3 probes/git-source-workflow/replay.py "$frontend" "$matrix"
  done
done
python3 probes/git-source-workflow/checks.py
python3 probes/git-source-workflow/collect.py
```

`prepare.py` freezes actual product frontends, saves the source patch against its
base and builds a standalone BLAKE3 helper. `real_setup.py` archives the private
origin as a Git bundle relative to that same published base. Thus source bytes
are recoverable, not merely identified by hashes. Drivers which adapt an older
fixture retain both the effective script and its original digest. No assertions
are dropped: the runtime migration replay changes only locations and the recovery
command's already-accepted absolute executable spelling.

The retained `development/` results precede the explicit acquisition decision.
`development/repair-stop-driver.py` is the original four-control reproducer
(saved with its original paths and source patch); it is historical evidence,
not part of the final clean sequence.
Cargo's ordinary metadata acquisition restores an edited checkout with a missing
`.cargo-ok`, but leaves an edited checkout it considers fresh. The accepted rule
is now implemented by `acquisition.py`: report reset, verify after Cargo, refuse
post-reset mismatch, and never repair in build/attachment/verify. The original
stop and source patch remain evidence of why this policy was decided.

Corrections during fixture development: disable Git's host colour when saving
patches; restore the marker rather than accidentally triggering acquisition in a
verification case; allow rustc's version/target queries in the compile trap;
match the verifier's changed-blob refusal for a length-changing mutation; and
expect the actual quoted executable in migrated runtime recovery; and add the
existing count-allocations feature to the old publication stub. Those fixes
do not weaken the bytes/no-publication/no-compilation assertions. An initial
cold PTY transcript in development was overwritten by a warm rerun, so it is not
claimed as retained cold evidence; the final fresh-target transcript is separate.
