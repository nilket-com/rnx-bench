# rnx 0184: Rune native tier versus LuaJIT, FUEL session results

One sealed session, 2026-10-12 (start 01:20 -05:00), on `nano`: Intel Core
i7-14700, Linux 7.0.0-31-generic, timed children pinned to logical CPU 4
(`taskset -c 4`), governor powersave, turbo on, SMT on. Subjects:

- `fuel-on`: Rune fork commit 346623b6 (local branch `fuel/guarded-fold`), built
  with the experimental native tier (`rune/fresh-core-native` + `rune/fresh-core`);
- `fuel-off`: the same source, lock and profile without the native tier (the
  fresh-core interpreter);
- `luajit`: LuaJIT 2.1.1788856981 with its defaults (the primary comparator);
- `luajit-joff`: the same LuaJIT with `-joff` (the secondary comparator).

Session status COMPLETE: 200/200 blocks, **all 400 samples valid**, no invalid
native exit. Eight blocks (calls round 9 and while round 3, all four subjects of
each) were flagged by the pre-registered readiness rule (load1 above 1.5 at block
start). Flagged blocks are **retained in the primary**; the sensitivity result
(only rounds in which every block of the cell is unflagged) is shown beside it,
never instead.

All figures below are copied from the analyzer output (`RESULTS.json`, sha256
`081552ac2c7994f5e71c56571bfc021f939d26a20fdd334019f971b710bf8d6d`). Ratios are
fuel-on time / comparator time, so **below 1 is faster for Rune**. Intervals are
marginal 95% percentile intervals from a joint paired-round bootstrap (B = 10,000),
each read on its own. No aggregate score is formed across kernels.

## Primary: calls versus LuaJIT

calls R_jit = fuel-on / luajit = **1.0190385456939974
[0.964384529758831, 1.0281535805098763]**, 10 rounds.

The pre-registered target was upper bound ≤ 1.25 (fuel-on at ≥ 80% of LuaJIT's
speed). **Target met** for these binaries in this session. The point estimate
corresponds to about 98% of LuaJIT's speed; that is a point estimate only. The
interval contains 1, so this result does not show Rune faster than LuaJIT on
calls, and none is claimed.

Sensitivity (9 unflagged rounds): 1.021822741013671
[0.9196612085628826, 1.0307276160145233], category met.

## Screens and comparators, each kernel separately

| kernel | R_jit (vs luajit) | R_joff (vs luajit -joff) | S = fuel-off / fuel-on |
|---|---|---|---|
| calls | 1.0190385456939974 [0.964384529758831, 1.0281535805098763] met | 0.07355673751856692 [0.07296123714527217, 0.07415770969589565] faster | 84.26519784465982 [83.57572203670199, 84.76407283310982] |
| while | 1.0171509290801066 [1.0142158739566205, 1.0256253674074831] met | 0.15675044792553244 [0.15562655247093438, 0.15785841962111885] faster | 31.31051956066137 [31.081622235071336, 33.013613048427075] |
| numeric | 0.445703161505773 [0.44527785202633163, 0.446160035061043] met | 0.24800744459688104 [0.24761292672562046, 0.24830698213877694] faster | 20.940710521813973 [20.91668310460603, 20.96217524202091] |

Sensitivity (unflagged rounds only):

| kernel | rounds | R_jit | R_joff | S |
|---|---|---|---|---|
| calls | 9 | 1.021822741013671 [0.9196612085628826, 1.0307276160145233] | 0.07373568704538878 [0.0731756321546555, 0.07446402371345053] | 84.01832616496124 [83.16216019916573, 84.81747093555177] |
| while | 9 | 1.0174380208147966 [1.0136712947340438, 1.0284747530917895] | 0.15680460551836142 [0.15645658663722817, 0.1580490497949474] | 31.330041225371236 [31.056533278345437, 34.66907719023473] |
| numeric | 10 | 0.445703161505773 [0.44527785202633163, 0.44615880792969936] | 0.24800744459688104 [0.24761719920000952, 0.24826812255676425] | 20.940710521813973 [20.916719857340656, 20.96217524202091] |

Rounded readings:

- calls R_jit 1.0190: target met, about 98% of LuaJIT's speed (point only).
- while R_jit 1.0172: target met (screen met), about 98% (point only).
- numeric R_jit 0.4457: target met; the whole interval is below 1, so fuel-on
  ran numeric faster than bare LuaJIT in this session (about 2.24× by point
  estimate). LuaJIT runs this kernel on doubles; see the caveats.
- R_joff: fuel-on is established faster than the LuaJIT interpreter (`-joff`) on
  all three kernels.
- S: the native tier ran calls 84.27×, while 31.31× and numeric 20.94× faster
  than Rune's own interpreter (point estimates).

## Derived per-iteration time (descriptive)

Median warmed slope per invocation divided by the mean loop-body iterations per
tail invocation; ns per loop iteration. Descriptive only, no intervals.

| kernel | luajit | luajit -joff | fuel-on (native) | fuel-off (interpreter) |
|---|---|---|---|---|
| calls | 0.5169 | 7.160 | 0.5267 | 44.38 |
| while | 0.5140 | 3.335 | 0.5228 | 16.37 |
| numeric | 3.057 | 5.493 | 1.362 | 28.53 |

The slope differences two separate child runtimes, so common first-invocation
work is intended to cancel; startup and first-invocation differences can remain.
Literal first-invocation medians are reported separately
(n = 20, µs; on fuel-on this includes the native tier's analysis, compile and
load): calls 784.2 fuel-on, 457.8 fuel-off, 17.8 luajit; while 539.3, 160.1,
14.9; numeric 738.7, 280.6, 42.4. Derived break-even (report only; a descriptive
extrapolation, not measured amortization, and a value below one does not mean
the native tier wins the first invocation): calls 0.84, while 2.25, numeric
1.61 invocations.

## Controls: feature-on cost where the native tier does not apply

fuel-on / fuel-off on kernels the native tier does not load (fib: no
candidate region; shared_rows: one candidate, not admitted at analysis). Pre-registered margin:
upper ≤ 1.01, else STOP.

| control | ratio [95%] | category |
|---|---|---|
| fib | 1.0093283880749 [1.007250244760702, 1.0107424608643187] | UNRESOLVED relative to 1.01 (interval straddles 1.01) |
| shared_rows | 0.994325557297197 [0.9645319170072482, 1.0100519049798637] | UNRESOLVED relative to 1.01 (straddles 1.01; contains 1, direction also unresolved) |

Neither control established a slowdown of more than 1%, and neither certified
the ≤ 1% margin. Both STOPs stand as recorded.

**Status.** FUEL is accepted as the next *experimental* checkpoint by an explicit
user exception: a risk-based engineering decision that accepts the unresolved
control margin. It is **not** a statistical pass, the control gate is not
relabelled as passed, and the gate stays in force for future artifacts. The
exception does not extend to unsafe-code correctness, memory or resource
requirements, other platforms, other workloads or later artifacts.

## Scope and caveats

Quoted from the analyzer's scope, lightly trimmed:

- "LuaJIT performs no overflow or fuel checks; Rune performs both (for calls: one
  guard covering the header and callee charges, their folded decrement, and the
  Add's overflow branch per iteration)."
- LuaJIT runs these kernels on doubles; Rune runs checked i64. The inputs keep
  every intermediate within ±2^31 so results agree exactly (asserted by the
  input generator).
- "LuaJIT uses host CPU features; the Cranelift target is baseline x86-64."
- "Harness overhead (process start, input reading, stdout and the MAPS line) is
  included in every wall time, including the tiny diagnostic, and differs between
  subjects; it is not claimed to be identical process work."
- "The calls region enters its slow copy only with fuel 0 or 1 at the guard and
  Replays only at a callee fuel exhaustion or fault, which this probe's fuel and
  inputs never reach: slow-copy and Replay cost are not measured."
- "every statement holds for these binaries in this session only." One machine
  (nano, i7-14700, Linux 7.0.0-31), CPU 4 pinned. Nothing about fib or shared_rows
  versus LuaJIT.
- x86-64 Linux only. The native tier is an experimental feature
  (`fresh-core-native`), not on by default.
- Multiplicity: 8 verdict-bearing marginal intervals (calls, while, numeric R_jit
  and R_joff; two controls); no joint or family-wise coverage is claimed.

## Earlier sealed sessions (descriptive history only)

Same probe family, same machine, earlier engine commits, each its own sealed
session on 2026-10-11. **Descriptive only.** No binary from one session is a
subject in another, so no interval spans sessions and no cross-session causal
claim is made: this table does not show that FUEL improved on any earlier
commit. The paired inference above stands on its own. Values rounded to 4
places from each session's analyzer output; the session receipts are local and
not distributed.

| session | engine commit | calls R_jit | while R_jit | numeric R_jit |
|---|---|---|---|---|
| P2 | 672a4eaa | — (calls was a control) | 1.2530 [1.2514, 1.2541] | 0.4568 [0.4563, 0.4595] |
| B1 | 7b1e2b0a | 1.5123 [1.5020, 1.5257] | 1.2559 [1.2544, 1.2583] | 0.4566 [0.4544, 0.4568] |
| W13 | 0765cce6 | 1.5071 [1.4924, 1.5227] | 1.0230 [1.0188, 1.0466] | 0.4473 [0.4459, 0.4488] |
| R1 | e1e1f30b | 1.2708 [1.2669, 1.2774] | 1.0333 [1.0260, 1.0463] | 0.4458 [0.4449, 0.4462] |
| R2 | 74ee506e | 1.2647 [1.2578, 1.2756] | 1.0134 [1.0092, 1.0167] | 0.4450 [0.4444, 0.4451] |
| R3 | 088d8245 | 1.2606 [1.2520, 1.2740] | 1.0132 [1.0100, 1.0216] | 0.4449 [0.4444, 0.4470] |
| FUEL | 346623b6 | 1.0190 [0.9644, 1.0282] | 1.0172 [1.0142, 1.0256] | 0.4457 [0.4453, 0.4462] |

RESULTS.json sha256 per session:

- P2: 85cc1761c8a9d40a2ef666c987b2d180154c0035720beb94074b47d68e65ae0a
- B1: 81f511a1cd8fa45db1ed6fb99fc7445cc36f0a2722b7122f80c918626a4c21ad
- W13: 1fe16b9d6f2c90991119be5c7cf569c6123121fedf534e5611a2f88908a19ed7
- R1: 3bfd3f2d82d17e80a9d1ea3346d7646d64ed0a7a0052c53a9b7e528187482336
- R2: 60fdc82f35eb0f2a5a6305cb6e97f95947c25f0edfe67d2417049ae8edc8b62f
- R3: e8bfb071e05c7f6338b7047e66aace24ee5252d6fc183779c5c18e0e89f5b2b0
- FUEL: 081552ac2c7994f5e71c56571bfc021f939d26a20fdd334019f971b710bf8d6d

None of these engine commits is public yet.

## Provenance

| item | sha256 |
|---|---|
| RESULTS.json (analyzer output) | 081552ac2c7994f5e71c56571bfc021f939d26a20fdd334019f971b710bf8d6d |
| raw.jsonl (controller output, 202 records) | a8cd7f84d6b80a7e4ebe746e5b17e93c644dbb7e457d5a8b4c5665bfc1c073c1 |
| session SHA256SUMS | 2c6c85ef1d4f1427850839151f584a39f2b7633ad3d36336be1aba45bd2e0c77 |
| sealed probe package SHA256SUMS | 8018823cf74526588eca0957347e1f5a7ab91e335ccc1a2a11578bf1a7c20aac |
| PINS.json (not distributed; summarised in README.md) | 4b3bee21ae5c0d2672000cd70f25c11da5aab14daf0b2b9b9b19ac12283ce3e3 |
| inputs/MANIFEST.json | 516720926a7b4a860e28bd3052e5217ba56e2e518cfe4e786aec281be839490f |
| fuel-on binary | 1bf2751753d291bb42090275ee994a133380a4b7d2576d82db736906b53ec971 |
| fuel-off binary | 7eeb0bf23cff195c5a5b0c00a7e83311f95c45fb240a7e1a2f40ce88b75b939d |
| luajit binary | a1ff02fbce1ed98f3e384e560158a456ffc26d43badac7a31e424af616c68320 |

Bootstrap seed (BOOT-SEED.txt) 12259218818769717712; session schedule seed
(SESSION-SEED.txt) 16553042724352686932; input seed 3028974873822931333.

Not distributed: raw.jsonl, RESULTS.json, the per-block phase files, the
session's pre-launch and diagnostic captures, the generated inputs, PINS.json
and the binaries. The exact engine source is not yet publicly available, so
public end-to-end reproduction is pending.
