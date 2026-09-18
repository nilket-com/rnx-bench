# 0065 gate 4: nested-native equivalence before product reuse

Linux, rnx alongside rnx-bench. The product change in this checkpoint is F1's
absolute recovery executable only. The candidate and workflow integration live
in an isolated tool copy. Gate 5 ports the reviewed candidate and measures the
uninstrumented product; no product speedup is claimed by this gate.

Prerequisites: the accepted native-inventory fixture (`target/s`, its frozen old
tool and constant copied third adapter), inventory-workflow's built two-native
project and environment, and the current tool's release build. Preserve saved
results before rerunning. `target/tool`, `target/matrix`, `target/extra`,
`target/recovery` and `target/migration` must be absent for their respective setup
or driver. Do not remove the earlier accepted fixtures: launch.py temporarily
edits one byte in their PostgreSQL source and restores bytes and timestamps in a
finally block. Do not run another user of those fixtures concurrently.

```sh
cargo build --release --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --bin rnx-project
python3 probes/nested-inventory/prepare.py
python3 probes/nested-inventory/check.py
python3 probes/nested-inventory/extra.py
python3 probes/nested-inventory/launch.py
python3 probes/nested-inventory/recovery.py
python3 probes/nested-inventory/replay.py
python3 probes/nested-inventory/checks.py
python3 probes/nested-inventory/collect.py
```

The oracle invokes the unchanged `native`/`native_using` reader from 7b0bb65. The
copy adds counters plus disabled-by-default observation hooks to that reader.
Only `candidate::many` enables observation hooks, scoped to the call. It still
uses the same parsing, refusals, bounded reads and tree format for each independent
root. The candidate module, trace module, probe entry and effective copied sources
are archived; no dependency or lockfile edit is needed for the isolated binary.

For eligible roots one combined rev-parse obtains the parent's --show-toplevel,
Git directory, index path and superproject result. Same child discovery is proved
from the enclosing top plus checked absence of intervening .git entries; the
fixture separately invokes --show-toplevel at each real roster root. Parent stage
parsing already refuses every gitlink, conflict or unsupported mode. Descendants
of a proposed child are also checked for .git boundaries, including ignored
subtrees. This discovery is bounded at 4096 entries per child; exhaustion or
unusual entries falls back instead of changing the source allowance or refusal.
No ignored file's content is hashed for this eligibility scan.

Linked worktrees, separate Git directories, nested repositories, external roots,
missing/ambiguous topology replies and inherited GIT_* settings take independent
paths. A newline path can need one extra discovery call before fallback. Counts
are tool-issued Git calls; they do not count helper processes Git itself starts.
The eligibility scan cost remains to be measured at gate 5.

Before reuse, directory/boundary, Git/index and relevant file metadata are checked.
Stamps include device, inode, mode, size and nanosecond mtime, not ctime. Files are
charged again per represented root even when their content is reused. State is
local to an inventory call; a two-call same-process case reads everything twice.

The timed matrix records the intentional observation-window difference: an
in-place same-size restored-mtime write after the parent's read is invisible to
the candidate until the next invocation, while the independent child reread sees
it. Ordinary mtime/index/boundary changes refuse in the candidate. The isolated
real workflow also refuses pre-launch restored-mtime source changes in both default
and --verify modes, leaving the lock pair and receipt unchanged.

Fixture corrections are named in the root evidence: staged deletion needed force,
gitlink insertion needed removal of existing child index entries, and inherited
GIT_DIR can make the oracle refuse before its sixth command. The first candidate
watched ancestors above the worktree, causing the pause marker to look like a
boundary mutation; discovery is now scoped to the worktree. None is hidden as a
measurement outlier or used to loosen quiescent equality.
