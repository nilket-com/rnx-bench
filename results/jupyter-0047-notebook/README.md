# Record 0047: Linux installation and JupyterLab, 2026-09-15

The accepted supervision commits (`7bb612e` in rnx, `4eefd66` in rnx-bench) were
pushed before this implementation. This directory records the next Linux step.
Source/binary SHA-256, commands, package versions and all fixture exit codes are
preserved. Source was uncommitted while measured; the adjacent implementation
commit contains the hashed files. Reproduction: `probes/jupyter-notebook/README.md`.

## Acceptance

Installer, status, installed-nbclient and actual JupyterLab fixtures pass twice.
The four prior supervision fixtures and both 0048 wire fixtures pass against the
new package into this directory, without replacing their historical outputs.
Kernel tests pass 23 in each feature configuration. Clippy with warnings denied,
root/kernel formatting and notices checks pass. Root suites pass sequentially
under TERM=xterm-256color: 344 default, 385 test-support. Root production source,
manifest, lockfile and notices are byte-identical to 7bb612e. No serving fixture
kernel or worker remains after the run.

`cells-and-error.png`, `reconnected-while-busy.png`, `interrupted.png` and
`saved-and-reopened.png` are genuine Chromium captures of JupyterLab. `Journey.ipynb`
is the notebook saved by the browser, strictly nbformat-validated and reopened.
`nbclient.ipynb` independently exercises the installed spec. Both use temporary
Jupyter data/config/runtime directories, including executable paths with spaces;
no personal kernelspec is modified. The frontend is JupyterLab 4.6.3, Server
2.21.0 and Chromium 151.0.7922.34 through Playwright 1.62.0.

The original environment's Tornado 6.5.9 fails static asset delivery because
FileFindHandler does not initialize its newly required allowed_symlink_directory.
`browser-initial-dependency-failure.txt` preserves that pre-notebook failure.
A separate browser environment pins Tornado 6.5.8; the original protocol
environment is unchanged. No third-party source patch is shipped.

The browser selects Rune, runs persistent values and a named error, reloads
during a pending cell without seeing a false idle, interrupts, then restarts.
A new execution refuses the pre-restart binding. It re-executes the example,
saves, validates and reopens it. Reload does not recreate the old page's cell
future; visible interruption is tested on a new request from the reloaded page.
An early fixture incorrectly required an unsolicited idle immediately after
restart. The final gate waits for the actual restart command then proves fresh
execution; it does not manually set frontend state or infer readiness from sleep.

## Implementation findings closed here

F1: shell kernel-info waits behind active execution, retaining the transport
receive credit rather than growing a separate queue. An ordering lock protects
its complete busy/reply/idle sequence against the next cell beginning. Control
info is immediate; during active execution it does not emit a status pair. The
fixture checks that no premature shell reply or idle appears and that control
still answers, then interrupts and checks the deferred reply and a fresh cell.
This is scoped to kernel-info; admission-refusal status behavior is unchanged.

A delayed-subscriber gate confirms that an idle shell-info request waits for an
observed matching status subscription before publishing, with a two-second cap.
This reduces startup loss for the chosen client, not a delivery guarantee to any
particular frontend. A shell-only caller eventually receives its reply anyway.
No arbitrary delay is used as proof of subscription readiness.

Actual notebook saving caught reply-only fields leaking into IOPub errors.
`status` and `execution_count` are now excluded from the IOPub error payload,
which contains only ename/evalue/traceback. Execute replies keep their fields.
A component test pins the separation; strict saved-notebook validation gates the
frontend path. This was not exposed by nbclient's normalized output construction.

The installer delegates installation to Jupyter, checks its listing and reported
user destination first, and refuses existing or invalid specs unless --replace
is explicit. The pinned CLI itself ignores --replace and always replaces. The
preflight is not atomic against another installer. CLI calls are trusted,
synchronous installation work, outside the serving shutdown deadline. Missing
CLI, malformed existing spec, replacement, Unicode refusals and spaces are gated.

## Measurements and their limits

Core 4, Rust 1.98.1. Twenty launches, one first cell and thirty warm cells each:

| Client-observed interval | median | range |
| --- | ---: | ---: |
| spawn through wait_for_ready | 393.35 ms | 344.89–407.06 ms |
| first `1 + 1` | 3.38 ms | 3.11–3.86 ms |
| warm `1 + 1` (600 cells) | 0.87 ms | 0.82–2.87 ms |

Ready includes Python channel construction and its readiness polling; it is not
the binary's raw startup time. Cell times include message exchange and client
observation of reply/idle. These are measurements of this environment, not a
comparison with Claude's unpinned observations or another kernel.

Ordinary rnx remains the exact accepted binary. Five command cases compare exit
status and complete stdout/stderr byte-for-byte. Hyperfine uses 10 warmups and
100 runs on an accepted copy versus that identical current binary:

| command | accepted copy | current |
| --- | ---: | ---: |
| version | 0.870 ms | 0.877 ms |
| eval 42 | 4.451 ms | 4.337 ms |
| run bare file | 4.055 ms | 3.983 ms |

The commands are identical code. Differences, including the reported outliers,
are variation/path effects, not a startup improvement or regression from this
package. Hash identity and the separate root graph establish build isolation.
Raw samples and warnings remain in the exports.

The default serving binary is 2,432,024 bytes and links libc/libm/libgcc_s and the
ELF loader, not libzmq. A build in an empty temporary target directory took
6.78 seconds with dependency downloads already cached; its binary hash matches
the measured serving binary. The acceptance examples are built with their test
feature, followed by a default-feature serving build, so their telemetry is not
part of these kernel measurements.

Windows type checking passes for portable code and an explicitly unsupported
supervisor, not Windows notebook execution. Windows job ownership and macOS/BSD
supervision remain unfinished. The separate rnx parent-death change is not made.
The async CPU-loop interruption limit and hard-killed Linux-kernel descendant
limit remain as recorded in 0047. Linux browser acceptance does not close those.
