#!/usr/bin/env python3
"""Measure install stages in iter/ops, retaining raw samples and registry counts."""
import csv
import os
from pathlib import Path
import random
import statistics
import subprocess

root = Path(__file__).resolve().parent
out = root / "results/stages"
out.mkdir(exist_ok=True)
binary = root / "target/release/rnx-context-profile"
base_env = dict(os.environ)
for key in ("RNX_PROFILE_MODULES", "RNX_PROFILE_STAGES"):
    base_env.pop(key, None)

def run(profile):
    env = dict(base_env)
    if profile:
        env["RNX_PROFILE_STAGES"] = "1"
    return subprocess.check_output(
        ["taskset", "-c", "4", str(binary), "time"], env=env, text=True).splitlines()

for _ in range(10):
    run(False)
    run(True)
order = [False, True] * 100
random.Random(20260913).shuffle(order)
rows, totals = [], []
for sample, profile in enumerate(order):
    lines = run(profile)
    totals.append((sample, int(profile), int(lines[-1])))
    assert len(lines) == (19 if profile else 1), lines
    for line in lines[:-1]:
        tag, module, stage, count, ns, functions, meta = line.split(",")
        assert tag == "stage"
        rows.append((sample, module, stage, int(count), int(ns), int(functions), int(meta)))
with (out / "stages.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "module", "stage", "entries", "ns", "functions_added", "metadata_added"))
    w.writerows(rows)
with (out / "context.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "instrumented", "context_ns"))
    w.writerows(totals)
with (out / "summary.md").open("w") as f:
    f.write("| Module | Stage | Entries | Mean ms | Stddev ms | Functions added | Metadata added |\n|---|---|---:|---:|---:|---:|---:|\n")
    for module, stage in dict.fromkeys((r[1], r[2]) for r in rows):
        entries = [r for r in rows if (r[1], r[2]) == (module, stage)]
        counts = {(r[3], r[5], r[6]) for r in entries}
        assert len(counts) == 1, counts
        count, functions, meta = counts.pop()
        times = [r[4] / 1e6 for r in entries]
        f.write(f"| {module} | {stage} | {count} | {statistics.mean(times):.4f} | {statistics.stdev(times):.4f} | {functions} | {meta} |\n")
    f.write("\nWhole context construction, including stage reporting when enabled:\n\n")
    for flag in (0, 1):
        times = [r[2] / 1e6 for r in totals if r[1] == flag]
        f.write(f"- Instrumented={flag}: {statistics.mean(times):.4f} ± {statistics.stdev(times):.4f} ms\n")
print((out / "summary.md").read_text())
