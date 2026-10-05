"""rnx 0170 step B: self-sampling (no unwinding) on the S2 builds, retired instructions and cycles in separate passes.

Run under the shared lock:
	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 sample.py STEP_A_S2_DIR OUT_DIR
Invocations per repeat are fixed BEFORE sampling from the untimed step-A S2 counts, targeting ~20k samples per
event x engine x workload across 3 repeats (gate >= 10k). Every invocation's stdout is validated.
"""
import json, math, os, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import EXPECT, WORKS, binary, kernel, held_lock, sha

PERIOD = 1000000  # 1e5 was throttled (perf_event_max_sample_rate 32000); see step-b-attempt1-throttled
TARGET = 20000
REPEATS = 3
EVENTS = {"instructions": "cpu_core/instructions/u", "cycles": "cpu_core/cycles/u"}


def plan(step_a):
	counts = json.loads((pathlib.Path(step_a) / "counts.json").read_text())
	assert counts["candidate"] == "s2" and counts["gate_representative_3pct"] and counts["gate_baseline_2pct"]
	n = {}
	for base in ("old", "new"):
		for w in WORKS:
			c = counts["counts"][f"{base}-s2-{w}"]
			for ev in EVENTS:
				per_run = c[f"{ev}_median"]
				n[f"{base}-{w}-{ev}"] = max(1, math.ceil(TARGET / REPEATS * PERIOD / per_run))
	return n


def record(out, label, event, argv, invocations, work):
	data = out / f"{label}.data"
	outfile = out / f"{label}.stdout"
	# One perf session over a fixed loop of identical invocations; the loop's own shell is sampled too and kept.
	loop = f'for i in $(seq {invocations}); do "$0" run "$1"; done > "$2"'
	cmd = ["taskset", "-c", "4", "perf", "record", "-q", "-e", event, "-c", str(PERIOD), "-o", str(data), "--",
		"bash", "-c", loop, argv, str(kernel(work)), str(outfile)]
	r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
	assert r.returncode == 0, (label, r.stderr[-500:])
	got = outfile.read_text()
	assert got == EXPECT[work] * invocations, (label, got[:200])
	outfile.unlink()
	return data, r.stderr


def report(data):
	"""Self samples per (dso, symbol), plus perf's own LOST/THROTTLE statistics."""
	r = subprocess.run(["perf", "report", "-i", str(data), "--stdio", "--no-children", "-n", "-q", "-g", "none",
		"--sort", "dso,sym", "--percent-limit", "0"], capture_output=True, text=True, timeout=300)
	assert r.returncode == 0, r.stderr[-500:]
	rows = []
	for line in r.stdout.splitlines():
		m = re.match(r"\s*([\d.]+)%\s+(\d+)\s+(\S+)\s+\[(.)\]\s+(.*?)\s*$", line)
		if m:
			rows.append({"samples": int(m.group(2)), "dso": m.group(3), "space": m.group(4), "symbol": m.group(5)})
	stats = subprocess.run(["perf", "report", "-i", str(data), "--stats"], capture_output=True, text=True, timeout=300).stdout
	lost = sum(int(x) for x in re.findall(r"LOST(?:_SAMPLES)? events:\s+(\d+)", stats))
	throttle = sum(int(x) for x in re.findall(r"THROTTLE events:\s+(\d+)", stats))
	return rows, lost, throttle, stats


def main(step_a, out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under the shared lock"
	n = plan(step_a)
	(out / "plan.json").write_text(json.dumps({"period": PERIOD, "target": TARGET, "repeats": REPEATS, "invocations_per_repeat": n}, indent=2) + "\n")
	ledger = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	profiles = {}
	for base in ("old", "new"):
		exe = str(binary(base, "s2"))
		for w in WORKS:
			for ev, event in EVENTS.items():
				key = f"{base}-{w}-{ev}"
				reps = []
				for rep in range(REPEATS):
					data, err = record(out, f"{key}-{rep}", event, exe, n[key], w)
					rows, lost, throttle, stats = report(data)
					total = sum(x["samples"] for x in rows)
					reps.append({"rows": rows, "total": total, "lost": lost, "throttle": throttle, "perf_stderr": err})
					(out / f"{key}-{rep}.stats.txt").write_text(stats)
				profiles[key] = {"invocations_per_repeat": n[key], "repeats": reps,
					"total_samples": sum(r["total"] for r in reps), "lost": sum(r["lost"] for r in reps),
					"throttle": sum(r["throttle"] for r in reps)}
				print(key, profiles[key]["total_samples"], "lost", profiles[key]["lost"], "throttle", profiles[key]["throttle"], flush=True)
	ledger.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	subjects = {b: sha(binary(b, "s2")) for b in ("old", "new")}
	(out / "samples.json").write_text(json.dumps({"subjects": subjects, "profiles": profiles, "ledger": ledger}, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])
