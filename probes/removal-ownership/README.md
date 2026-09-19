# 0066 gate 1: guarded removal and explicit ownership

This is an isolated candidate, not a product command. Root baseline `1ab9732`
contains only the plan and the accepted mount-prerequisite stop. The preceding
bench stop at `1f0b85d` remains intact. Product source is unchanged.

`build.py` copies the real tool into `target/tool`, adds the standalone
`rnx-removal-probe` target and verifies that every original Rust file and the
Cargo lockfile stayed identical. The candidate uses the already-pinned libc and
the original tool's signal handling. Its pause, forced-error and exec-control
hooks are prototype instrumentation, not production behavior.

The guarded open uses Linux `openat2` with `RESOLVE_BENEATH`,
`RESOLVE_NO_SYMLINKS` and `RESOLVE_NO_XDEV`. Unsupported or refused calls have no
path-based fallback. Directory and regular-leaf opens use that guard; internal
symlinks are unlinked as leaves. `renameat2(RENAME_NOREPLACE)` hides a whole entry
before directory-relative deletion. Parent syncs precede child deletion. This
does not protect against a same-user adversary moving open directories elsewhere;
the plan's trusted-store and explicit-quiescence contract applies.

## Run

Linux prerequisites: working unprivileged bubblewrap, Git, Cargo/Rust, strace,
the cached tool/Polars crates, built root `rnx` and `rnx-jupyter`, and the existing
`probes/jupyter-notebook/.venv`. No sudo or sysctl change is used. The disposable
outside sentinel belongs to this fixture, not to a user store.

`setup.py` defaults to the retained genuine SHA-256 product tool at
`probes/native-inventory/target/stock/tools/project/target/release/rnx-project`.
Its original product sources and lock are checked against `7cd3205` in the saved
`old-tool-source.json`; the added historical probe target did not change that
product's modules. To use an independently built old tool, build
`tools/project/Cargo.toml` at rnx `7cd3205` in a separate checkout and set
`RNX_REMOVAL_OLD_TOOL` to its absolute executable path. The current tool comes from
the sibling root's `tools/project/target/release/rnx-project`.
`finish.py` derives the old tool's source directory above target/release; if the
binary was copied elsewhere, name that directory with
`RNX_REMOVAL_OLD_TOOL_SOURCE`.

Run from the bench root with `target/real` and `target/cases` absent:

```sh
export PYTHONDONTWRITEBYTECODE=1
export RNX_REMOVAL_RESULTS="$(mktemp -d /tmp/rnx-0066-results.XXXXXX)"
python3 probes/removal-ownership/bootstrap.py
python3 probes/removal-ownership/build.py
python3 probes/removal-ownership/matrix.py
python3 probes/removal-ownership/setup.py
probes/jupyter-notebook/.venv/bin/python probes/removal-ownership/journey.py
python3 probes/removal-ownership/checks.py
python3 probes/removal-ownership/finish.py
```

Unset `RNX_REMOVAL_RESULTS` only when intentionally regenerating the checked-in
results. The bootstrap refuses an existing bootstrap result, setup refuses an
existing `target/real`, the matrix refuses an existing `target/cases`, and the
journey refuses an existing journey result. For a complete rerun, after all
fixture consumers have stopped, move this probe's whole `target/` aside to a
fresh `target.previous-*` name and select a new empty results directory. That move
invalidates retained fixture artifact paths; do not use them afterwards. No
other probe target, registry, user cache or user kernelspec needs removal.

## What the drivers prove

- `bootstrap.py`: user-mapped bubblewrap sets up a same-device bind and a tmpfs.
  An intentionally unguarded unlink reaches the disposable outside sentinel.
  The parent namespace has no mounts afterwards.
- `matrix.py`: 44 cases including busy cache/install locks, both selection
  formats (visible and pending), invalid selection, self-target refusal,
  zero-write inspection with a writer lock held, close-on-exec lock descriptors,
  leaf symlinks, hardlinks, read-only files, FIFOs/sockets, control-path symlinks,
  an allowed symlink spelling of the root, bounds and precommit replacement.
  SIGINT, SIGTERM and SIGKILL run before rename, after rename and during deletion.
  Resume removes only pending data and preserves a separately created visible
  entry. Its quoted recovery command executes through `/bin/sh`.
- Six real mount cases refuse before rename: same-device directory bind, nested
  tmpfs, bind at the entry, entries and locks boundaries, and regular-file bind.
  `mountinfo` and device numbers are retained, with outside sentinels unchanged.
  ENOSYS/EINVAL are injected syscall failures; this is not a run on an old kernel.
- The process trace shows inspection starting no children: no Git, compiler,
  Cargo, builder or artifact is invoked.
- `setup.py` installs a genuine format-1 runtime from `7cd3205`, renames its
  original checkout away and builds an old-key Polars plus retained-output
  adapter in a fresh private cache. The adapter's build script writes a file at
  its real retained OUT_DIR, and its function reads that absolute path later.
- `journey.py` authenticates/migrates that runtime with the current product and
  independently builds a current-format Polars assembly. A live old session and
  old-key kernel read new retained-output values before and after inspection.
  The fixture can take the writer locks while both are alive, and inspection
  also completes while those locks are held. Both consumers are explicitly
  stopped and reaped before removing the old entries. The kept current assembly
  still runs. Runtime and project bytes, selection and kernelspec are checked;
  cache snapshots compare inode, mode, size and mtime (not atime or every data
  byte). The private kernelspec is removed by its fixture owner afterwards.

The current and old Polars builds each took about 100 seconds with cached
registry sources. These are setup observations, not performance measurements.
The old assembly removal covered 3,771 descendant nodes and about 1.56 GB logical
data. Accounting is preliminary: it counts descendants, deduplicates inodes per
entry and does not promise reclaimed space or count the entry directory itself.
Gate 4 owns the final accounting and cost reports.

## Limits and remaining gates

The candidate deliberately requires an explicit absolute root and emits JSON.
It does not implement the product CLI, root precedence, full metadata labels,
missing-root behavior, manifest annotations, or all listing/output allowances.
Those are gate 2. The rebuilt-visible entry in interruption cases is synthetic;
an old-tool rebuild under the same key, per-parent-sync injections and the full
publication failure matrix remain gate 2. Combined PostgreSQL journeys,
Polars-sized interruption/resume, annotations and full byte checks of all kept
cache data remain gate 3. This gate adds no lifetime reference claim and no
launch work.

Three initial development corrections are recorded: two clippy issues in the
new candidate, the invalid O_PATH/O_NONBLOCK combination (corrected without
changing resolve flags), and the fixture's overlong Unix socket path (bound by a
relative name instead). The final 44-case run and live journey pass. The earlier
unshare stop is preserved rather than rewritten as a passing run.
