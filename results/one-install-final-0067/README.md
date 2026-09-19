# 0067 gate 5: costs and regression

Product code: rnx `1b894e0`, unchanged since accepted Gate 3 `7ae8863`.
Stock baseline: `94f5f3f`. Gate 5 edits only the READMEs and plan/evidence.
See `probes/one-install-final/README.md` for replay order and fresh-directory
requirements. All measured source is preserved by those commits, the fixture
bundles and the isolated profiling patch.

## Everyday launch

Compact medians over run/eval/first-prompt and both repeats, in milliseconds
**over the same artifact launched directly**:

| Declared adapters | Git | Path |
|---:|---:|---:|
| 0 | 1.89 | 13.87 |
| 1 | 2.19 | 14.87 |
| 2 | 2.35 | 15.22 |
| 3 | 2.53 | 15.56 |

Every individual Git cell beats its matched path cell. The hypothesis of 1–2 ms
is not universal: two/three-adapter launches cost more than that. The gate is
improvement, not that prediction. The runtime is the zero-adapter floor; the
fixture runtime has 481 tracked files / 7,488,049 bytes. Polars is 23 files /
984,868 bytes, PostgreSQL 21 / 517,390 and its renamed complete copy 21 / 517,384.
These adapter files also occur in the runtime tree. `native-trees.json` reports
the overlap rather than summing it as independent data.

The six path first-adapter increments (run/eval/prompt, repeats 0/1) are
1.015/0.991/0.904 and 1.065/1.053/0.864 ms. They are reported, with 0065's
qualification unchanged; this record does not reopen that threshold. The roster
is this record's larger frozen source snapshot, not the old 443-file fixture.

`launch-samples.jsonl` retains all 3,360 samples. `launch-summary.json` has each
cell, its medians and p10/p90 spread; `launch-gate.json` keeps the comparison and
all six increments. Fixed seeds, two repeats of 30 per cell, one pinned core,
one Polars thread, two warmups and verified outputs. No builds ran alongside it.

## Stock behavior

Two interleaved repeats against the stock baseline, 100 samples per process
cell and 200 per persistent-cell pair, all 2,400 samples retained:

| Workload | Median delta, repeat 0 / 1 | Percent, repeat 0 / 1 |
|---|---:|---:|
| version | +0.033 / +0.020 ms | +1.79 / +1.08% |
| eval 42 | +0.097 / +0.092 ms | +1.83 / +1.73% |
| JSON 10k | +0.026 / +0.025 ms | +0.20 / +0.19% |
| first prompt | +0.057 / +0.037 ms | +1.38 / +0.89% |
| ordinary cell | +0.009 / +0.003 ms | +2.54 / +0.74% |

The 5% stop does not trigger. This harness includes Python spawn/capture/wait or
PTY creation, rather than measuring only time in rnx. Absolute values and spreads
are in `stock-summary.json`; persistent cells exclude process startup. The stock
binary grows from 15,288,760 to 18,670,080 bytes; size is not used as a proxy for
startup time.

## Explicit costs and ownership

One-adapter medians (both repeats agree closely):

| Full command | Git | Path |
|---|---:|---:|
| `eval --verify` | 320 ms | 57 ms |
| offline lock | 1,303 ms | 433 ms |
| attach/build on ready entry | 2,025 ms | 178 ms |
| startup-probe child | 6.57 ms | 6.54 ms |

Full Git authentication is expensive; everyday trust does not make preparation
free. Attachment invokes no compilation, proved separately with positive-tested
Cargo/rustc traps at every roster size. The isolated one-native full-verification
profile attributes about 272 ms to input verification, 40 ms to artifact checking
and 0.56 ms to lock decoding. That diagnostic sample set is separate from the
ordinary product matrix.

Default Git profiling uses an isolated patched standalone manager, an unchanged
standalone control and stock rnx: 720 separate samples. Lock/pair decoding costs
about 0.42–0.63 ms, input/context checking 0.56–0.88 ms, receipt/ready/artifact
checking 0.14–0.19 ms, command construction around 0.001 ms. Total within
`git_launch` is 1.1–1.7 ms; CLI/project opening/envelope detection and process/exec
costs lie outside it. Intervals are disjoint; medians need not add. The full
product/control/profiler clocks are retained, rather than subtracting presumed
zero instrumentation overhead.

An isolated cold Polars target builds offline in 114.6 seconds with Git and
registry sources cached and no competing build. The roster setup build times
are retained separately, some concurrent with checks, and are not that cold-build
observation. A real public-origin Cargo fetch takes 4.73 seconds untraced into a
fresh Git home. A separate traced acquisition receives 2,226,360 TCP bytes and
retains a 2,176,658-byte Git pack. Transport includes protocol overhead; registry
sources were already cached. Trace time is not substituted for untraced time.

The fixture Cargo Git DB/checkout retains about 11.30 MB allocated / 10.12 MB
logical. Each zero-adapter assembly retains about 0.56 GB allocated; Polars 1.58 GB;
two/three adapters 1.61 GB. `storage.json` gives exact bytes/inodes per owner.
Shared registry storage and benchmark build targets are excluded. No default
runtime store is created. Removal continues to be explicit; Git source storage
belongs to Cargo, not the assembly-removal command.

## Regression, traces and qualifications

Root suites: 376 default, 419 test-support, 389 runner-only. Management: 51/52,
with two ignored integration tests in each. Formatting, tool strict all-target
clippy in both configurations, combined notices, selfcheck and the final
packaged-manifest tests pass. Feature graphs and real generated artifacts omit
management where required. The external embedding fixture passes assembly,
failures, reset and worker cases; the ordinary server commits/rolls back against
a private PostgreSQL cluster and shuts down with no pooled backends.

Root strict clippy still reports the same 13 production and two test-only
findings as the baseline; no additions. PostgreSQL's all-target clippy reports
one test-module placement lint in source byte-identical to the baseline. Polars
and server strict all-target clippy pass. These are retained qualifications, not
claimed clean checks. Native tests and all three notice checks pass.

Every ordinary Git launch trace at zero through three adapters has exactly two
successful execs (manager and artifact), zero native-source opens and zero
Internet connections. Compressed traces retain the actual observations.

`fixture-corrections.json` names three harness corrections: a copied help
namespace, a notices-script path, and attachment success wording during warm-up.
The failed initial roster bundle/logs and observed refusal/success text are
preserved. No headline samples were discarded. No product correction was needed.
The temporary baseline worktree is removed; historical fixture worktrees remain
untouched. No fixture processes remain. Windows execution is not claimed.
