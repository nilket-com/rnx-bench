# 0065 gate 3: authenticated retained-runtime migration

Root implementation: `7b0bb65`; baseline: `a7c3f7d`. Old product/runtime snapshot:
`7cd3205`. Full narrative is in rnx's
`plans/0065_a_launch_checks_each_native_file_once_migration_evidence.md`.

Reproduction: `probes/runtime-migration/README.md`. All stores, caches, projects,
clusters and kernelspecs used here are fixture-owned. No user installation store
was read or changed.

- `matrix.json`: 30 migration, corruption, publication, interruption and recovery
  cases through actual old/current products.
- `precommit.json`: an old-selection refusal preserves a started HTTP future and
  its binding without consent, scratch creation or runtime drain.
- `publication/matrix.json`: 90 accepted installer regression cases. The effective
  driver and adaptation are retained beside the results.
- `checks.json`: fmt, strict all-target clippy, 46 passing tests in both feature
  configurations (two ignored in each), and notices.
- `journey.json`: full-source migration after the fixture checkout was physically
  renamed; old live session and prewritten old-key kernelspec still read retained
  build output; new default passes four real Polars/PostgreSQL journeys, including
  two compilation-trapped attachments and private-cluster queries.
- `scratch.json`: a genuine old scratch reopens after default migration, and an
  explicit new-tool relock keeps its declared old runtime path.
- `index-independence.json`: migrated Git administration has no alternates or
  worktree links; equal loose objects occupy independent inodes.
- `conditions.json`: exact root source/binary provenance. `implementation.patch`
  preserves the tool change; the signed root commit preserves its source tree.

The full migration took 2.33 s in one observation. Both runtime entries remain:
8,475,023 old logical bytes and 8,475,143 newly added bytes including Git objects.
Whole old/new assembly directories remain too. No pruning, eviction or new
launcher/runtime compatibility guarantee is claimed. Gates 4–6 remain open.
