# 0180 static analysis

No subject execution, compilation, perf or Valgrind. The tool reconstructs
retained PMU medians first, then runs stock binutils against the four retained
primary/counter executables. Primary is the deciding role; counter is a
secondary feature-set cross-check. Allocation binaries are hash-checked only.

Run controls before static analysis. Hold /tmp/rnx-runtime-bench.lock for the
analysis, with an external 600 s timeout and 5 s kill grace. Individual binutils
commands own process groups and have 120 s deadlines and kill/reap handling.
Outputs must be a new directory; partial failures remain retained.

```sh
python3 probes/execution-cost-0180/controls.py
python3 probes/execution-cost-0180/static.py REPO RETAINED_BIN OUTPUT
```

The instruction normalizer resolves only direct call/branch target addresses.
It retains registers, immediates, memory operands, opcodes and target identities.
Unresolved direct targets produce an explicitly unresolved classification.
Duplicate demangled names are not paired. Full raw disassembly and ELF tables
remain the authority; normalized equality is limited to the inspected sequences
and is not an executed-path, dependency, CFG or performance proof.

Reports retain complete selected regions and boundary candidates. A human
source/path and control-flow audit must precede an explanation checkpoint.
The automatic surface is deliberately broad (VM run/call/return, Value/Repr and
range/iterator conversion). Named direct callees outside it remain in the full
disassembly for explicit follow-up, with expansions justified in the report.

Arithmetic uses whole-process medians minus run-empty, without modifying any
0179 result. Script hashes and source texts bind loop counts; fib's recurrence
counts all leaf and nonleaf invocations separately. Small integer residues
are reported, not discarded or treated as causal proof.

## Native-event attempt and closure audit

The reviewed events.py driver made exactly one official attempt. It stopped
on the frozen group-B validity check after R and A completed. See
results/execution-cost-0180/OFFICIAL.md for the retained partial findings and
disclosures. No subsequent measurement is authorized by these files.

Reconstruct the raw-row ordering, sample validity, R/A summaries and printed
tables without executing a subject or opening a counter:

```sh
python3 probes/execution-cost-0180/audit.py
```

The closure audit pins the official raw hash and stops on any discrepancy.
Its receipt is results/execution-cost-0180/audit.json.
