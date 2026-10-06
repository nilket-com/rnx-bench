# 0180 Step 0 checkpoint: generated code differs; cycle cause unresolved

This is a retained-file diagnostic checkpoint for review, not a performance
WIN or an accepted explanation of all native cycles. No subject, compiler,
perf or Valgrind process has executed in this record. The 0179 STOP stands.

## Provenance, attempt and role correction

Plan 3cf1e7a folds Claude's correction into 6125811. Both deciding PMU and wall
samples in 0179 use the primary binaries: stage() copies artifact(subject,
"primary"), and compare()/wall() use that stage. The counter role is used by
historical-reproduction fifo(), not deciding PMU. Counter disassembly below
is a secondary cross-check, never a substitute for the primary's identity.

Tooling 2d42ef3b was committed before static1. Its 19 synthetic controls passed,
but extraction stopped at the required Vm::run guard: nm's v0 demangling is
`<rune::runtime::vm::Vm>::run`, while the filter expected `Vm::run`. Arithmetic
and base-primary binutils outputs remain in static1; its asm is losslessly
xz-packed, with its uncompressed hash in the original ledger. The failure is
a tooling STOP, not absence of a VM function. Partial receipt db62d9ce is kept.

Claude approved a spelling-only repair before replay. Tooling 038f27fb admits
both spellings and adds positive spelling controls plus a wrong-type rejection;
22 controls pass. Two additional file-level provenance controls (wrong manifest and swapped primary role) both refuse before any binutils command or arithmetic output. One fresh static2 then completed, exit 0. The hashes,
normalization, fixed subjects and arithmetic did not change. Commands ran under
/tmp/rnx-runtime-bench.lock with a 600 s outer deadline and five-second kill
grace; binutils subprocesses own groups, 120 s deadlines and kill/reap handling.
The tool ledger records explicit safe environment, executable hashes, argv,
status and output hashes. No inherited environment is recorded.

All six binary hashes and the manifest/raw hashes are checked first. Full
nm, demangled nm, readelf and objdump outputs are retained. Full executable
section disassembly is the authority. Static2 asm and region JSON files are
losslessly xz-packed after completion; hashes in the ledger/completed report
refer to original decompressed contents. Four separate stock-objdump excerpts
independently reproduce the primary pop_call_frame and its identified Value
drop target extents; spot-ledger.json binds those commands and their outputs.
No instruction sequence was regenerated from another build.

## First: aggregation and script counts

Arithmetic is independently reconstructed from the 20 raw PMU rows per
workload: five ABBA repetitions, ten samples per side, all primary-role hashes,
status/reap, event values, running percentage and saved medians checked.
run-empty's instruction delta is -1,946,002. Subtract it diagnostically from
each script run's whole-process delta. This is a difference of medians, not a
measured loop phase or exact claim of common setup cost. Compilation and
script-dependent setup may leave residuals.

| Script | Source-bound operations | Adjusted instruction delta | Prediction per operation | Residue |
| --- | ---: | ---: | ---: | ---: |
| numeric | 1,000,000 for iterations (1..1000001) | -11,999,746.5 | -12 | +253.5 |
| signed range | 1,000,000 for iterations (0..1000000) | -10,001,787 | -10 | -1,787 |
| negative range | 1,000,000 for iterations (-500000..500000) | -10,001,855 | -10 | -1,855 |
| while | 1,000,000 iterations (1 through 1000000) | -6,999,812 | -7 | +188 |
| range-while | 1,000,000 iterations (0 through 999999) | -4,999,658.5 | -5 | +341.5 |
| overwrite_inline | 1,000,000 iterations | -38,002,245 | -38 | -2,245 |
| calls | 1,000,000 invocations of inc | +10,000,563.5 | +10 | +563.5 |

Hashes and full source text accompany every binding in arithmetic.json. Counts
are interpreted from those frozen sources, not inferred from the counter
result. The range fixtures differ in their interval constants but share their
for-range/sum shape. Their residues differ by 68 instructions. A shared setup
cost is compatible with that resemblance; this contrast cannot identify its
source. No forced startup correction or rounded-away remainder follows.

fib(27) invokes fib 635,621 times: C(0)=C(1)=1 and
C(n)=1+C(n-1)+C(n-2). Of these, 317,810 are nonleaf invocations; main is not
included. Adjusted delta +20,975,687.5 equals +33.000306 per invocation, with
+194.5 residue against +33 x 635,621. Leaf/nonleaf paths differ, so that is not
proof every call executes exactly 33 extra instructions. Claude withdrew the
earlier approximate +21 per-call prediction based on an incorrect call count.

These contrasts strongly support fewer instructions beyond startup in the
range runs, not startup savings hiding increased loop work. They support a
repeatable operation-related generated-code difference. Whole-process totals
alone do not establish its exact dynamic basic block or explain its cycle cost.

## Machine identities and concrete differences

The requested primary functions each have a unique named symbol extent. ELF
addresses are virtual addresses; runtime PIE bias was not measured. Addresses
modulo 16/32/64 and static branch/block candidates are retained in each region
report. They are not measured hot addresses or uop-cache occupancy.

| Primary function | Base address / bytes / decoded instructions | Candidate address / bytes / decoded instructions |
| --- | --- | --- |
| Vm::run | 0x3e1ff0 / 102,615 / 19,697 | 0x4e3e20 / 102,741 / 19,744 |
| Vm::pop_call_frame | 0x3deb10 / 772 / 186 | 0x4e0920 / 804 / 192 |
| Vm::op_call | 0x3fb0d0 / 2,908 / 622 | 0x4fcf80 / 2,908 / 622 |

Those instruction counts are all decoded instructions in the symbol extent,
including cold/unwind paths and padding, not retired instruction counts.
Equal op_call sizes/counts are not an equivalence certificate. Full raw
mangled identities and bytes hashes are in selected-identities.json and the
region reports; alias sets and ambiguous demangled clones remain explicit.

Vm::run has an immediate difference at offset +0xa: base reserves 0x538 bytes
of stack, candidate 0x518. Diagnostics/environment spill offsets differ too:
base +0x2f writes at rsp+0x4e0, candidate at rsp+0x4c0. pop_call_frame goes the
opposite way at +0xa: stack reservation 0x58 -> 0x68, with different registers
and spills. Its main cleanup loop has additional payload preservation and
reconstruction in candidate. These are changed generated instructions, not
just relocated equal bytes, and they are on possible execution paths of the
unaltered VM methods. Their source in vm.rs is unchanged by 0179.

A precise primary caller/callee identity can also be followed without guessing
among same-demangled drop clones. pop_call_frame's cleanup loop directly calls:

| Edge | Base | Candidate |
| --- | --- | --- |
| First identified cleanup-loop call | caller +0xcf -> 0x4c2300 | caller +0xe7 -> 0x379980 |
| Second identified cleanup-loop call | caller +0x181 -> 0x4c2300 | caller +0x19b -> 0x379980 |
| The called Value drop extent | 204 bytes / 42 decoded instructions | 1,327 bytes / 349 decoded instructions |

The raw target name includes a local ThinLTO suffix, retained unchanged in the
reports. It is the exact target address in each binary that binds the edge,
not a guessed demangled match. The called drop routine starts with two saved
registers in base, six in candidate; both reserve 0xb8 bytes and test the tag
against 0xa, but their instruction streams then differ substantially. More
static instructions in a cold path do not establish more executed work in fib.
No 0179 dynamic edge profile exists to count that path or allocate the full
+33-per-invocation contrast to it. The 0176 call counts are not imported.

Source control flow explains possible reachability: Vm::run dispatches decoded
instructions in its loop; Call invokes op_call; pop_call_frame calls
stack.pop_stack_top(frame.top, worklist), updates ip and returns the saved
output/isolation. Source-level for/return behavior does not by itself identify
every native branch or indirect target taken by each script.

The counter pair has the same selected function sizes and decoded instruction
counts as its corresponding primary, at different addresses; this is only a
static cross-check. No claim of complete role equivalence follows.

## What the automatic comparison does and does not prove

All selected region extents are checked for contiguous decoded bytes. Raw
instructions and function-relative boundary candidates are retained. Registers,
widths, immediates, memory operands and padding are not discarded. Direct
branch/call normalization resolves exact raw target identities or stays
unresolved; duplicate demangled names are not matched to a guessed clone.

Both roles' comparison tables include unresolved normalization for the main VM
methods (external/PLT targets without a defined text-symbol binding). Those
methods are therefore NOT certified equivalent or exhaustively different by
the automated comparison. The concrete register/immediate/call examples above
are independently readable in full objdump and the spot excerpts. The broad
surface includes aliases, metadata and cold paths, so its aggregate count of
"changed inspected sequence" is not a count of hot functions. Address/residue
changes cannot certify a frontend cause. No narrowed normalization was added
after seeing these results to force equivalence.

## Questions and next measurement boundary

Q1: retained arithmetic supports a reduction beyond startup, while native
cycles and wall worsen. The binary evidence demonstrates changed generated
VM code as well as placement. Pure placement of identical code is not the
whole description. It does NOT locate the exact -12/-10 sequence on the executed
for-range path or establish which mechanism costs extra cycles.

Q2: fib's +2.283% whole-process instructions, adjusted +33.000306 per invocation,
coexists with changed dispatch/return/drop code. Those changes are plausible
places to seek the extra work, but no dynamic path count proves their share of
that increase. This is a located code difference, not a complete attribution.

Status of alternatives: changed code/dependencies is supported as a code fact;
placement/frontend, instruction/data cache and branch behavior remain untested
mechanisms; effective frequency/host effects remain untested; startup hiding
loop growth is weakened by the bound arithmetic. These mechanisms can coexist.
No physical CPU/frontend claim is made without the planned primary-source
check and a reviewed counter protocol.

Checkpoint recommendation: preserve this result and review whether one native
paired event study can distinguish host/frequency variation from changed
frontend/backend cost on these SAME primary binaries. CPU/event discovery,
exact groups, reference cycles, workload selection, predictions, running
percentages, sample order and reproduction/noise rules must be an accepted
plan amendment before discovery or execution. It cannot by itself prove that
one stack spill, alignment boundary or uop-cache effect caused the regression.
If no feasible event set discriminates these alternatives, close INCONCLUSIVE
instead of inventing a source/profile variant. No such discovery or measurement
has been performed or approved by this checkpoint.
