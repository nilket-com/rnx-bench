# 0063 gate 6: ordinary regression and user costs

Run from rnx-bench with the measured root source staged and unchanged until all
projects and timings finish. Generated targets are ignored. A fresh run needs
`probes/session-final/target/dogfood` absent; setup owns private cache/state roots.
Never run different root feature suites concurrently in one target directory.

1. `python3 probes/session-final/checks.py` runs the three root suites serially,
   both tool suites and strict clippy configurations, notices, release selfcheck,
   root Windows GNU and tool Windows MSVC type-checks. Install those Rust targets
   first. GNU root checking also needs a real MinGW C compiler and archiver named
   by `CC_x86_64_pc_windows_gnu` and `AR_x86_64_pc_windows_gnu`. The recorded run
   unpacked Ubuntu compiler packages into `/tmp/rnx-0063-cross`, without installing
   system packages. Its initial MSVC root attempt could not build ring without
   `lib.exe`; the complete GNU root check subsequently passed. No Windows
   execution is claimed. Root clippy's 13 existing production diagnostics are
   compared separately with the pre-transition `78c514d` checkout, not hidden.
2. Build an ordinary release project tool, then
   `python3 probes/session-final/ordinary.py`. This freezes the ordinary release
   CLI/tool and reuses the real gate-4 dogfood driver at a separate target and
   results directory. Four journeys include two cold targets and two attachments
   with positive-controlled compiler traps. Output-observed phase timestamps
   distinguish author/resolve, build/attach, startup, commitment and first prompt.
   Forwarding/polling can merge nearby markers; these are not internal profiler
   intervals. Cold observations here had other validation builds running.
3. Build the root default debug CLI and tool test-support debug binary. Run
   `python3 probes/session-final/replay.py`. It archives the preparation/startup
   replays and restores their published results, then runs `cache.py`: current
   cache commands, metadata/full-verification and interactive contracts, real
   Polars override PTY, publication failures, legacy workflow, and real mapped
   PostgreSQL workflow. The frozen pre-cache tool must exist; if absent,
   `python3 probes/cache-commands/build.py` creates it. Only legacy lock creation
   uses that tool; current code builds and launches. Generated replay sources and
   source hashes are archived. A raw 0057 driver cannot seed its own old format
   using the new lock command; the initially attempted raw replay is preserved
   as a fixture error, not a product failure.
4. Build a detached `78c514d` root release at `/tmp/rnx-0063-before`. With all
   other builds/fixtures complete, `python3 probes/session-final/measure.py`
   interleaves two repeats on one pinned CPU. It measures project/direct/verify
   eval and first prompt, baseline/current version and eval, persistent ordinary
   cells, and a real startup-probe child. Every output/status is checked. Warmups
   are explicit; every measured sample is retained, with the unchanged 25 ms
   project-over-direct bound. Remove the worktree with git worktree remove after
   archiving its binary hash and source identity.

The results also include the unchanged Jupyter supervision, extended and saved
notebook fixtures, opt-in real tool integrations, a normalized default dependency
graph comparison and a generated-doc public-surface check. All use private
fixture directories. Kernel/worker and database process cleanup are asserted.

The exact source patch against gate 4 (`b8ba8e6`) is archived before later status
and evidence edits. That preserves the input tree used by the builds; a digest
alone would not preserve it. Existing result directories are restored, while new
results stay under `results/session-final-0063`.
