"""rnx 0173 build-perturbation diagnostic (plan rnx 0173, sections 2 and 5). Descriptive only: no tolerance, no gate.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 diag.py OUT_DIR

Order: identity table; correctness of every C edit (and A1/A2) against A0; then the comparisons, each 5 ABBA
repetitions (A B B A) per workload, whole-process instructions:u and cycles:u, the raw perf JSON retained per sample.
A and C binaries run from ONE staged path (stage/primary, atomically replaced, hash-verified before and after every
sample) with environment E0. B runs the A0 binary from the frozen launch paths (E0), or at B0 with E1/E2.
"""
import hashlib, json, os, pathlib, re, shutil, statistics, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = HERE / "bin"
SUBJECTS = ["a0", "a1", "a2", "c0", "c1", "c2", "c3", "c4"]
CORPUS, FIX = HERE / "corpus", HERE / "fixtures"
E0 = {"PATH": "/usr/bin:/bin", "HOME": "/home/me", "LANG": "C.UTF-8"}
E1 = {**E0, "RNX0173_PAD": "x" * 1024}

_t = [f"item:{i}" for i in range(1, 20001)]
_s = "|".join(_t)
EXPECT = {"empty": "", "answer": "42\n", "numeric": "3\n", "fib": "196418\n", "strings": f"{len(_s)}\n{_s[0:19]}\n{_s[len(_s) - 21:]}\n"}
EXPECT.update({k: f"{v}\n" for k, v in EXPECTED.items()})


def path_for(work):
	return CORPUS / f"{work}.rn" if (CORPUS / f"{work}.rn").exists() else FIX / f"{work}.rn"


WORKLOADS = [("floor", ["floor"], ""), ("empty-context", ["empty-context"], ""), ("context", ["context"], ""),
	("runtime", ["runtime"], ""), ("compile-answer", ["compile", str(path_for("answer"))], "")]
WORKLOADS += [(f"run-{w}", ["run", str(path_for(w))], EXPECT[w]) for w in
	["answer", "empty", "numeric", "fib", "strings", "while", "compare", "calls", "vector",
	"overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias"]]
NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]


def sha(p):
	return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def text_sha(p):
	r = subprocess.run(["objcopy", "-O", "binary", "--only-section=.text", str(p), "/dev/stdout"], capture_output=True, check=True)
	return hashlib.sha256(r.stdout).hexdigest()


def norm(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


STAGE = HERE / "stage/primary"


def stage(subject):
	"""Atomically place a subject's binary at the one fixed path; return its verified hash."""
	STAGE.parent.mkdir(exist_ok=True)
	tmp = STAGE.parent / f".staging-{subject}"
	shutil.copy2(BIN / subject, tmp)
	os.replace(tmp, STAGE)
	h = sha(STAGE)
	assert h == HASHES[subject], (subject, "staged hash")
	return h


def perf(exe, tail, expect, env):
	argv = [str(exe), *tail]
	r = subprocess.run(["perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--", *argv],
		capture_output=True, text=True, timeout=300, env=env)
	assert r.returncode == 0 and r.stdout == expect, (argv, r.stdout[:80], r.stderr[-300:])
	counts = {}
	for line in r.stderr.splitlines():
		if line.startswith("{"):
			row = json.loads(line)
			for n in ("instructions", "cycles"):
				if row.get("event") in (n + ":u", f"cpu_core/{n}/u"):
					assert float(row["pcnt-running"]) >= 99 and float(row["counter-value"]) > 0, row
					counts[n] = float(row["counter-value"])
	assert set(counts) == {"instructions", "cycles"}, r.stderr[-300:]
	return {"argv": argv, "env": env, "cwd": os.getcwd(), "affinity": sorted(os.sched_getaffinity(0)), "stdout": r.stdout,
		"raw_perf": r.stderr, **counts}


def compare(name, left, right, out):
	"""5 ABBA repetitions per workload. left/right: callables returning (exe_path, env, identity) after preparing."""
	samples = []
	for rep in range(5):
		for label, tail, expect in WORKLOADS:
			for side in ("L", "R", "R", "L"):
				exe, env, ident = (left if side == "L" else right)()
				s = perf(exe, tail, expect, env)
				if ident.get("staged"):
					after = sha(exe)
					assert after == ident["hash"], (name, "stage changed during sample")
					s["hash_after"] = after
				samples.append({"comparison": name, "rep": rep, "workload": label, "side": side, **ident, **s})
	with (out / f"{name}.jsonl").open("w") as f:
		for s in samples:
			f.write(json.dumps(s) + "\n")
	rows = {}
	for label, _, _ in WORKLOADS:
		l = [s["instructions"] for s in samples if s["workload"] == label and s["side"] == "L"]
		r = [s["instructions"] for s in samples if s["workload"] == label and s["side"] == "R"]
		assert len(l) == 10 and len(r) == 10
		rows[label] = {"left": l, "right": r, "left_median": statistics.median(l), "right_median": statistics.median(r),
			"change": statistics.median(r) / statistics.median(l) - 1}
	return rows


def staged(subject, env):
	def f():
		h = stage(subject)
		return STAGE, env, {"subject": subject, "staged": True, "hash": h}
	return f


def fixed(path, env, tag):
	def f():
		return path, env, {"subject": "a0", "launch": tag, "hash": HASHES["a0"]}
	return f


HASHES = {}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	os.sched_setaffinity(0, {4})
	assert os.sched_getaffinity(0) == {4}
	E2 = dict(os.environ)  # captured once, reused unchanged for every E2 sample
	for s in SUBJECTS:
		HASHES[s] = sha(BIN / s)
	identity = {s: {"sha256": HASHES[s], "text_sha256": text_sha(BIN / s)} for s in SUBJECTS}
	res = {"identity": identity, "E2": E2, "started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	# Correctness: every other subject against A0 on the corpus and fixtures (strict, origin-qualified).
	corr = {}
	for s in SUBJECTS[1:]:
		for origin, d in (("corpus", CORPUS), ("fixtures", FIX)):
			for fx in sorted(d.glob("*.rn")):
				mode = "async" if fx.stem == "async" else "run"
				extra = ["2000000"] if fx.stem == "budget" else []
				a = subprocess.run([str(BIN / "a0"), mode, str(fx), *extra], capture_output=True, text=True, timeout=300)
				b = subprocess.run([str(BIN / s), mode, str(fx), *extra], capture_output=True, text=True, timeout=300)
				ra, rb = (a.returncode, a.stdout, a.stderr), (b.returncode, b.stdout, b.stderr)
				key = f"{s}:{origin}/{fx.stem}"
				corr[key] = norm(ra) == norm(rb)
				assert corr[key], (key, ra[:2], rb[:2])
	res["correctness"] = {"checked": len(corr), "all_identical": all(corr.values())}
	print("identity:", {s: (v["sha256"][:12], v["text_sha256"][:12]) for s, v in identity.items()}, flush=True)
	print("correctness:", len(corr), "identical", flush=True)
	comparisons = {}
	# A: only rebuilds that differ from A0.
	for s in ("a1", "a2"):
		if HASHES[s] != HASHES["a0"]:
			comparisons[f"A-a0-vs-{s}"] = compare(f"A-a0-vs-{s}", staged("a0", E0), staged(s, E0), out)
	# B: launch paths (E0) and environments (at B0).
	lp = HERE / "launch"
	b0 = lp / "p00/primary"
	paths = {"B0": b0, "B1": lp / "p01/primary", "B2": lp / "p02/primary", "B3": HERE / "l/p00/primary",
		"B4": lp / "p00" / ("x" * 19) / "primary", "B5": lp / "p00" / ("x" * 59) / "primary"}
	want = {"B0": 0, "B1": 0, "B2": 0, "B3": -5, "B4": 20, "B5": 60}
	for k, p in paths.items():
		assert len(str(p).encode()) - len(str(b0).encode()) == want[k], (k, len(str(p)) - len(str(b0)))
		p.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(BIN / "a0", p)
		assert sha(p) == HASHES["a0"]
	res["launch_paths"] = {k: str(p) for k, p in paths.items()}
	for k in ("B1", "B2", "B3", "B4", "B5"):
		comparisons[f"B-path-B0-vs-{k}"] = compare(f"B-path-B0-vs-{k}", fixed(b0, E0, "B0"), fixed(paths[k], E0, k), out)
	comparisons["B-env-E0-vs-E1"] = compare("B-env-E0-vs-E1", fixed(b0, E0, "B0/E0"), fixed(b0, E1, "B0/E1"), out)
	comparisons["B-env-E0-vs-E2"] = compare("B-env-E0-vs-E2", fixed(b0, E0, "B0/E0"), fixed(b0, E2, "B0/E2"), out)
	# C: only edits whose binary differs from A0.
	for s in ("c0", "c1", "c2", "c3", "c4"):
		if HASHES[s] != HASHES["a0"]:
			comparisons[f"C-a0-vs-{s}"] = compare(f"C-a0-vs-{s}", staged("a0", E0), staged(s, E0), out)
	res["comparisons"] = comparisons
	res.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	(out / "diag.json").write_text(json.dumps(res, indent=1) + "\n")
	for name, rows in comparisons.items():
		print(name, " ".join(f"{k}:{v['change'] * 100:+.2f}%" for k, v in rows.items()), flush=True)



# HISTORICAL PRODUCER (0173 run1). It captures the raw inherited environment for condition E2, and its retained output
# was redacted after capture (results/build-perturbation-0173/REDACTION.md). Do not rerun as is: a new run must
# capture with redaction at source and include a fake-secret sentinel control.
if __name__ == "__main__" and not __import__("os").environ.get("RNX0173_ALLOW_HISTORICAL_RERUN"):
	raise SystemExit("diag.py is a historical producer; see the comment above")

if __name__ == "__main__":
	main(sys.argv[1])
