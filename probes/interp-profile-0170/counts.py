"""rnx 0170 step A: validation, the 0168 baseline gate, profiling-build representativeness, whole-process counts.

Run under the shared lock (it refuses otherwise):
	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 counts.py OUT_DIR
"""
import fcntl, hashlib, json, os, pathlib, select, signal, statistics, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
BENCH0168 = pathlib.Path("/home/me/work/rnx-bench/probes/rune-base-0168")
KERNELS = HERE / "kernels"
WORKS = ["empty", "answer", "numeric", "fib", "strings", "while", "compare", "calls", "vector"]
COMPUTE = ["numeric", "fib", "strings", "while", "compare", "calls", "vector"]
# Expected stdout: kernels from oracle.py, the 0168 fixtures from their Python oracles in lua-rust-0001.
sys.path.insert(0, str(HERE))
from oracle import EXPECTED
EXPECT = {
	"empty": "", "answer": "42\n", "numeric": "3\n", "fib": "196418\n",
	"while": f"{EXPECTED['while']}\n", "compare": f"{EXPECTED['compare']}\n",
	"calls": f"{EXPECTED['calls']}\n", "vector": f"{EXPECTED['vector']}\n",
}
# The strings fixture prints three lines; computed independently here.
_t = [f"item:{i}" for i in range(1, 20001)]
_s = "|".join(_t)
EXPECT["strings"] = f"{len(_s)}\n{_s[0:19]}\n{_s[len(_s) - 21:]}\n"
# Recorded in results/rune-base-0168/conditions.json.
HASHES = {
	("old", "primary"): "dc7d458dd0450ac805e9abb749c19203b52417f28710822cb22199a7b98b8b41",
	("old", "counter"): "88ef3d0d7bc891cc",
	("new", "primary"): "0ee1f4fdcfdae587",
	("new", "counter"): "00c5b480830464c2",
}
BASELINE = {  # 0168 counters.json medians (instructions:u, FIFO-bracketed run windows)
	("old", "numeric"): 1378164363.0, ("old", "fib"): 679040402.0,
	("new", "numeric"): 1756638881.0, ("new", "fib"): 830599527.0,
}


def binary(base, kind):
	if kind == "symbolized":
		return HERE / base / "target/profiling/symbolized"
	if kind == "s2":
		return HERE / base / "target/profiling2/s2"
	return BENCH0168 / base / "target/release" / kind


def sha(p):
	return hashlib.sha256(p.read_bytes()).hexdigest()


def kernel(work):
	return KERNELS / f"{work}.rn"


def held_lock():
	"""True only when another holder has the shared lock (i.e. our flock wrapper)."""
	fd = os.open("/tmp/rnx-runtime-bench.lock", os.O_RDONLY | os.O_CREAT, 0o666)
	try:
		fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except BlockingIOError:
		return True
	fcntl.flock(fd, fcntl.LOCK_UN)
	return False
	# (the fd is closed by process exit)


def perf_stat(argv):
	r = subprocess.run(["taskset", "-c", "4", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--", *argv],
		capture_output=True, text=True, timeout=120)
	return r


def parse_stat(stderr):
	out = {}
	for line in stderr.splitlines():
		if not line.startswith("{"):
			continue
		row = json.loads(line)
		name = next((n for n in ["instructions", "cycles"] if row.get("event") in (n + ":u", f"cpu_core/{n}/u")), None)
		if name is None:
			continue
		assert name not in out and float(row["pcnt-running"]) >= 99, row
		out[name] = float(row["counter-value"])
	assert set(out) == {"instructions", "cycles"}, stderr[-400:]
	return out


def fifo_counts(base, work):
	"""The 0168 counter method, unchanged: FIFO-enabled perf around go/DONE on the counter binary."""
	tmp = pathlib.Path(os.environ["TMPDIR_0170"])
	ctl, ack, raw = tmp / "c.ctl", tmp / "c.ack", tmp / "c.jsonl"
	for p in (ctl, ack, raw):
		if p.exists():
			p.unlink()
	os.mkfifo(ctl)
	os.mkfifo(ack)
	cf = os.open(ctl, os.O_RDWR | os.O_NONBLOCK)
	af = os.open(ack, os.O_RDWR | os.O_NONBLOCK)
	child = perf = None
	try:
		argv = [str(binary(base, "counter")), "run", str(kernel(work))]
		child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
		assert select.select([child.stderr], [], [], 10)[0] and child.stderr.readline() == "READY\n"
		pcmd = ["taskset", "-c", "0", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "-p", str(child.pid), "-D", "-1", "--control", f"fifo:{ctl},{ack}", "-o", str(raw)]
		perf = subprocess.Popen(pcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

		def control(message):
			os.write(cf, (message + "\n").encode())
			assert select.select([af], [], [], 10)[0], message
			assert os.read(af, 1024).rstrip(b"\0") == b"ack\n"
		control("enable")
		child.stdin.write("go\n")
		child.stdin.flush()
		deadline = time.monotonic() + 60
		while True:
			assert time.monotonic() < deadline, "counter child timeout"
			line = child.stderr.readline()
			assert line, "counter child exited early"
			if line == "DONE\n":
				break
		control("disable")
		child.stdin.write("stop\n")
		child.stdin.flush()
		stdout, stderr = child.communicate(timeout=10)
		assert child.returncode == 0 and not stderr and stdout == EXPECT[work], (stdout, stderr)
		perf.send_signal(signal.SIGINT)
		perf.communicate(timeout=10)
		return parse_stat(raw.read_text())
	finally:
		for p in (child, perf):
			if p is not None and p.poll() is None:
				p.kill()
				p.wait()
		os.close(cf)
		os.close(af)
		for p in (ctl, ack):
			p.unlink()


CANDIDATE = sys.argv[2] if len(sys.argv) > 2 else "symbolized"


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under: flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 counts.py OUT"
	os.environ["TMPDIR_0170"] = str(out)
	ledger = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	# Identity of every subject.
	subjects = {}
	for base in ("old", "new"):
		for kind in ("primary", "counter", CANDIDATE):
			h = sha(binary(base, kind))
			if (base, kind) in HASHES:
				assert h.startswith(HASHES[(base, kind)]), (base, kind, h)
			subjects[f"{base}-{kind}"] = {"path": str(binary(base, kind)), "sha256": h}
	kernels = {w: sha(kernel(w)) for w in WORKS}
	# 1. Validation: every workload, every runnable binary, exact stdout, before any counting.
	for base in ("old", "new"):
		for kind in ("primary", CANDIDATE):
			for w in WORKS:
				r = subprocess.run([str(binary(base, kind)), "run", str(kernel(w))], capture_output=True, text=True, timeout=60)
				assert r.returncode == 0 and r.stdout == EXPECT[w] and not r.stderr, (base, kind, w, r.stdout[:200], r.stderr[:200])
	print("validation: all 9 workloads x 2 engines x 2 builds exact", flush=True)
	# 2. Baseline gate: the 0168 FIFO method on the 0168 counter binaries, 3 repeats, within 2% of 0168.
	baseline = {}
	for (base, w), want in BASELINE.items():
		vals = [fifo_counts(base, w)["instructions"] for _ in range(3)]
		med = statistics.median(vals)
		baseline[f"{base}-{w}"] = {"values": vals, "median": med, "baseline": want, "ratio": med / want}
		print(f"baseline {base} {w}: {med:.0f} vs {want:.0f} ({med / want:.4f})", flush=True)
	gate_baseline = all(abs(v["ratio"] - 1) <= 0.02 for v in baseline.values())
	# 3. Whole-process counts, primary vs symbolized, 5 repeats each (representativeness gate: within 3%).
	counts = {}
	for base in ("old", "new"):
		for kind in ("primary", CANDIDATE):
			for w in WORKS:
				reps = []
				for _ in range(5):
					r = perf_stat([str(binary(base, kind)), "run", str(kernel(w))])
					assert r.returncode == 0 and r.stdout == EXPECT[w], (base, kind, w, r.stdout[:100], r.stderr[-300:])
					reps.append(parse_stat(r.stderr))
				counts[f"{base}-{kind}-{w}"] = {
					"instructions": [x["instructions"] for x in reps], "cycles": [x["cycles"] for x in reps],
					"instructions_median": statistics.median(x["instructions"] for x in reps),
					"cycles_median": statistics.median(x["cycles"] for x in reps)}
		print(f"counts {base} done", flush=True)
	repr_rows = {}
	for base in ("old", "new"):
		for w in WORKS:
			p = counts[f"{base}-primary-{w}"]["instructions_median"]
			s = counts[f"{base}-{CANDIDATE}-{w}"]["instructions_median"]
			repr_rows[f"{base}-{w}"] = s / p
	gate_repr = all(abs(v - 1) <= 0.03 for k, v in repr_rows.items() if k.split("-", 1)[1] in COMPUTE)
	ledger.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	result = {"subjects": subjects, "kernels": kernels, "expected": EXPECT, "baseline": baseline, "gate_baseline_2pct": gate_baseline,
		"counts": counts, "candidate": CANDIDATE, "candidate_over_primary": repr_rows, "gate_representative_3pct": gate_repr, "ledger": ledger}
	(out / "counts.json").write_text(json.dumps(result, indent=2) + "\n")
	print(json.dumps({"gate_baseline_2pct": gate_baseline, "gate_representative_3pct": gate_repr, "candidate": CANDIDATE, "candidate_over_primary": repr_rows}, indent=1))


if __name__ == "__main__":
	main(sys.argv[1])  # usage: counts.py OUT [symbolized|s2]
