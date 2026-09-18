# 0065 gate 6: final slopes, installed use and regression

This gate uses the accepted F5 product source at rnx 4855dbd, with no production
code change. Gate 5's 1.016205 ms first-adapter result stays in its original journal
and gate file; acceptance with that qualification does not change the threshold.

Run from rnx-bench with rnx alongside it. Prerequisites are the retained
native-inventory and inventory-workflow fixtures, cached Cargo dependencies and
private PostgreSQL cluster tools. All targets/stores here are fixture-owned.
Never run builds or other fixtures during the measurement commands.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/checks.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/scope.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/setup.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/installed.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/replay.py contracts
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/supplement.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/roster.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/headline.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/measure.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/attachment.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/inventory-final/collect.py
```

Setup compiles b3.rs into target/b3 using rustc and the existing product release
BLAKE3 rlib. This tiny fixture helper checks installation tool digests and adapts
the old protocol driver's key calculation; it introduces no product dependency.
Cargo configurations must be built serially. The product private assembly probe
requires test-support; build it before roster.py and measure.py if absent:

```sh
cargo build --locked --offline --manifest-path ../rnx/tools/project/Cargo.toml --features test-support --bin rnx-project-assembly-probe
```

Preserve prior results before a rerun. Setup refuses an existing target/tool or
project/source directories. Installed requires target/installed absent. Contract
replay requires its preparation, startup, commitment, discovery, publication and
repair targets absent. Supplemental fixtures require their isolated subtargets
absent. Headline requires target/baseline, target/format, target/reuse and its
journal absent. Topology and attachment refuse existing journals; attachment
also requires target/attachment absent. No command evicts an older shared entry.

The headline driver repeats exactly the 4500-sample matrix: SHA-256 baseline,
format-only BLAKE3 and final reuse, each with matched direct launch, zero through
three adapters, run/eval/first prompt, two repeats and 30 samples per cell. The six
first-adapter cells and strict gate result are reported again, not substituted
for the accepted earlier journal.

Topology measurement uses the ordinary final product and matched artifacts. The
constant runtime still contains 443 files / 6,988,177 bytes at every roster count.
External copies retain each adapter's entire tracked set and change only its
Cargo runtime path to the fixed canonical root; those bytes/counts are recorded.
Their assemblies are genuinely built. Deep and equally long shallow controls
use the accepted byte-identical native trees and also build real artifacts.

For the nested-repository control, the driver temporarily gives each of the
three already tracked adapter subtrees its own Git administration. Native source
bytes and accepted input identities stay unchanged, so existing artifacts are
valid; no receipt is forged. Private counters prove independent fallback. The
nested topology is one separate block because changing those shared Git roots
between unrelated processes would invalidate the control. The driver removes
only Git directories it created and checks all locks and receipts unchanged.
Other shapes, including GIT_EDITOR fallback, are interleaved within each repeat.

The 14000-file ignored target remains a separate eligibility control: three Git
calls and 443 physical reads throughout the eligible roster, with shared checks
once per parent. All clocks use one pinned CPU, one Polars thread and stable PTY
settings. Attachment is a separate full-hash row with real compiler traps and
positive controls, not a free cache-hit claim.

The installed journey copies source exactly from 4855dbd, uses the final ordinary
tool and launcher built from that same snapshot, installs it, then physically
renames the original before any engine build. It replays cold Polars and combined
Polars/PostgreSQL :dep, two compiler-trapped second consumers, scratch reopening,
absolute/relative project paths, retained frames after errors and typed SQL on a
private cluster. No original checkout path may route a consumer lock or generated
manifest. Sessions and the postmaster are explicitly reaped.

Regression adapters are archived beside their outputs. Historical digest fields
and the prospective assembly-key computation use BLAKE3; malformed current.json
controls use current format 2 and unknown format 99. Genuine old formats are tested
by the already adapted 0065 migration/workflow drivers. Historical interactive
implicit receipt creation becomes explicit build, and old/malformed receipts
refuse without publication. No refusal assertion is silently removed.

Root suites run serially in default, test-support and combined configurations;
notices, fresh release selfcheck, tool suites/clippy, the protected-source/default-
graph comparison and public API docs are checked. Windows is neither executed nor
newly type-checked in this Linux closing gate. All samples and failed fixture
attempts are preserved, with corrections identified in the evidence.

The first preparation setup attempt is retained under results/inventory-final-0065/failed-doc-edit.
A concurrent edit to the root plan and README changed fingerprinted inputs during
its build; the product correctly refused post-build validation. The edits were
restored, the unpublished target retained, and preparation restarted in a fresh
target. Keep the root checkout fixed until all build-dependent replays finish.
