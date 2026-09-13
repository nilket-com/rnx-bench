#!/usr/bin/env python3
"""Fresh processes pinned to CPU 4; retain all observations in nanoseconds."""
import csv
import os
from pathlib import Path
import random
import statistics
import subprocess

root = Path(__file__).resolve().parent
binary = root / "target/release/rnx-context-profile"
env = dict(os.environ)
env.pop("RNX_PROFILE_MODULES", None)
profile_env = dict(env, RNX_PROFILE_MODULES="1")

def run(profile):
    return subprocess.check_output(
        ["taskset", "-c", "4", str(binary), "time"],
        env=profile_env if profile else env, text=True).splitlines()

for _ in range(10):
    run(False)
    run(True)
order = [False, True] * 100
random.Random(20260913).shuffle(order)
rows, totals = [], []
for sample, profile in enumerate(order):
    lines = run(profile)
    totals.append((sample, int(profile), int(lines[-1])))
    if profile:
        assert len(lines) == 34, lines
        for line in lines[:-1]:
            name, build, install, drop = line.split(",")
            rows.append((sample, name, int(build), int(install), int(drop)))
with (root / "results/modules.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "module", "build_ns", "install_ns", "drop_ns"))
    w.writerows(rows)
with (root / "results/context.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("sample", "instrumented", "context_ns"))
    w.writerows(totals)
table = []
for name in dict.fromkeys(r[1] for r in rows):
    entries = [r[2:] for r in rows if r[1] == name]
    means = [statistics.mean(e[i] for e in entries) / 1e6 for i in range(3)]
    table.append((name, *means, sum(means)))
with (root / "results/modules.md").open("w") as f:
    f.write("| Module | Build ms | Install ms | Drop ms | Total ms |\n|---|---:|---:|---:|---:|\n")
    for name, *values in sorted(table, key=lambda r: -r[-1]):
        f.write("| " + name + " | " + " | ".join(f"{v:.4f}" for v in values) + " |\n")
print((root / "results/modules.md").read_text())
print("Aggregate build/install/drop ms:", [sum(r[i] for r in table) for i in range(1,4)])
for flag in (0, 1):
    values = [t[2] / 1e6 for t in totals if t[1] == flag]
    print("instrumented", flag, "context ms mean/stdev/median:", statistics.mean(values), statistics.stdev(values), statistics.median(values))

def lifecycle():
    return tuple(map(int, subprocess.check_output(
        ["taskset", "-c", "4", str(binary), "lifecycle"],
        env=env, text=True).strip().split(",")))

for _ in range(10):
    lifecycle()
values = [lifecycle() for _ in range(100)]
with (root / "results/lifecycle.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(("build_ns", "context_drop_ns"))
    w.writerows(values)
print("Lifecycle build/drop means ms:", [statistics.mean(v[i] for v in values) / 1e6 for i in (0, 1)])
