#!/usr/bin/env python3
"""Attribute iter/ops trait registration to each trait, in fresh processes."""
import csv
import os
from pathlib import Path
import statistics
import subprocess

root = Path(__file__).resolve().parent
out = root / "results/traits"
out.mkdir(exist_ok=True)
env = dict(os.environ, RNX_PROFILE_STAGES="1", RNX_PROFILE_TRAITS="1")
env.pop("RNX_PROFILE_MODULES", None)
command = ["taskset", "-c", "4", str(root / "target/release/rnx-context-profile"), "time"]

def run():
    return subprocess.check_output(command, env=env, text=True).splitlines()

for _ in range(10):
    run()
rows = []
totals = []
for sample in range(100):
    lines = run()
    totals.append((sample, int(lines[-1])))
    traits = [line for line in lines[:-1] if line.startswith("trait,")]
    assert len(traits) == 78, len(traits)
    for line in traits:
        tag, module, index, typ, trait, ns, functions, meta = line.split(",")
        rows.append((sample, module, int(index), typ, trait, int(ns), int(functions), int(meta)))
with (out / "traits.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "module", "index", "type", "trait", "ns", "functions_added", "metadata_added"))
    w.writerows(rows)
with (out / "context.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "context_ns"))
    w.writerows(totals)
with (out / "summary.md").open("w") as f:
    f.write("| Module | Trait | Implementations | Mean ms | Stddev ms | Functions added | Metadata added |\n|---|---|---:|---:|---:|---:|---:|\n")
    for module, trait in dict.fromkeys((r[1], r[4]) for r in rows):
        groups = [[r for r in rows if r[0] == sample and r[1] == module and r[4] == trait] for sample in range(100)]
        counts = {(len(g), sum(r[6] for r in g), sum(r[7] for r in g)) for g in groups}
        assert len(counts) == 1, counts
        count, functions, meta = counts.pop()
        times = [sum(r[5] for r in g) / 1e6 for g in groups]
        f.write(f"| {module} | {trait} | {count} | {statistics.mean(times):.4f} | {statistics.stdev(times):.4f} | {functions} | {meta} |\n")
print((out / "summary.md").read_text())
