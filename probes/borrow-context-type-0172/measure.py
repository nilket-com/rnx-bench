"""rnx 0172: borrow the container type during associated installation. Base fork main bb8e6937 vs candidate.

	TMPDIR=<results filesystem> flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 measure.py OUT_DIR

Pre-registered order (plan 0172, sections 3 and 4, with amendments):
	1. correctness: 0169 corpus (28) + 8 added fixtures, base vs candidate, keys qualified by origin; allocation direction
	2. calibration: resident driver (0169 plan_clock.rs) vs hyperfine -N --output=pipe, |median difference| <= 0.15 ms
	3. base reproduction (instructions only): 0169 FIFO counter rows on the counter build; 0171 whole-process rows
	4. 5 interleaved whole-process PMU repetitions (ABBA)
	5. resident-driver wall clock, 3 rounds x 10 per subject per workload (ABBA blocks of 5), plan receipts checked
	6. the frozen decision
"""
import hashlib, json, math, os, pathlib, re, select, signal, statistics, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = {v: {k: HERE / v / "target/release" / k for k in ("primary", "counter", "allocation")} for v in ("base", "cand")}
CLOCK = HERE / "target/plan-clock"
CORPUS = HERE / "corpus"
FIX = HERE / "fixtures"
# Historical references come from this repository's committed copies: 0169's counters.json from its raw archive
# (fb56b1d), verified against rune-runtime-0169-SHA256SUMS; 0171's measure.json (54e1a77).
REPO = HERE.parents[1]
R0169_ARCHIVE = REPO / "results/rune-runtime-0169-raw.tar.xz"
R0169_MEMBER = "results/rune-runtime-0169-attempt5b/counters.json"
R0169_SHA256 = "5e09153b85afbb9b2b464039527cada2b11ee2886afa70cdc1b7bbb689279734"
R0171 = REPO / "results/store-fast-path-0171/run1/measure.json"
R0171_SHA256 = "a653251c613b68d0b2e92bcb0f6f6f57a855bc5946a2a91593fd417e6f89b986"
REPRO_0169 = [("floor", None), ("empty-context", None), ("context", None), ("runtime", None), ("compile", "answer"),
	("run", "answer"), ("run", "empty"), ("run", "numeric"), ("run", "fib"), ("run", "strings")]
REPRO_0171 = ["while", "compare", "calls", "vector", "overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias"]


def read_0169():
	import tarfile
	data = tarfile.open(R0169_ARCHIVE).extractfile(R0169_MEMBER).read()
	assert hashlib.sha256(data).hexdigest() == R0169_SHA256, "0169 reference hash"
	sums = (REPO / "results/rune-runtime-0169-SHA256SUMS").read_text()
	assert f"{R0169_SHA256}  {R0169_MEMBER}" in sums, "0169 reference not in SHA256SUMS"
	rows = json.loads(data)
	ref = {}
	for r in rows:
		if r["base"] == "new":
			ref.setdefault((r["mode"], r["work"]), []).append(r["counts"]["instructions"])
	for key in REPRO_0169:
		assert len(ref.get(key, [])) >= 3 and all(isinstance(v, (int, float)) and v > 0 for v in ref[key]), ("0169 reference rows", key)
	return ref


def read_0171():
	data = R0171.read_bytes()
	assert hashlib.sha256(data).hexdigest() == R0171_SHA256, "0171 reference hash"
	pmu = json.loads(data)["pmu"]
	for w in REPRO_0171:
		v = pmu[f"base-{w}"]["instructions"]
		assert len(v) == 5 and all(isinstance(x, (int, float)) and x > 0 for x in v), ("0171 reference rows", w)
	return pmu

_t = [f"item:{i}" for i in range(1, 20001)]
_s = "|".join(_t)
EXPECT = {"empty": "", "answer": "42\n", "numeric": "3\n", "fib": "196418\n", "strings": f"{len(_s)}\n{_s[0:19]}\n{_s[len(_s) - 21:]}\n"}
EXPECT.update({k: f"{v}\n" for k, v in EXPECTED.items()})


def path_for(work):
	return CORPUS / f"{work}.rn" if (CORPUS / f"{work}.rn").exists() else FIX / f"{work}.rn"


# (label, argv tail, expected stdout); modes without a file print nothing.
WORKLOADS = [("floor", ["floor"], ""), ("empty-context", ["empty-context"], ""), ("context", ["context"], ""),
	("runtime", ["runtime"], ""), ("compile-answer", ["compile", str(path_for("answer"))], "")]
WORKLOADS += [(f"run-{w}", ["run", str(path_for(w))], EXPECT[w]) for w in
	["answer", "empty", "numeric", "fib", "strings", "while", "compare", "calls", "vector",
	"overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias"]]
GATE = "context"
NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]


def norm(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


def sha(p):
	return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def perf_whole(v, tail, expect):
	r = subprocess.run(["taskset", "-c", "4", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--",
		str(BIN[v]["primary"]), *tail], capture_output=True, text=True, timeout=300)
	assert r.returncode == 0 and r.stdout == expect, (v, tail, r.stdout[:80], r.stderr[-300:])
	return parse(r.stderr)


def parse(text):
	out = {}
	for line in text.splitlines():
		if line.startswith("{"):
			row = json.loads(line)
			name = next((n for n in ("instructions", "cycles") if row.get("event") in (n + ":u", f"cpu_core/{n}/u")), None)
			if name:
				assert float(row["pcnt-running"]) >= 99, row
				val = float(row["counter-value"])
				assert math.isfinite(val) and val > 0, row
				out[name] = val
	assert set(out) == {"instructions", "cycles"}, text[-300:]
	return out


def fifo(v, mode, work, tmp):
	"""0169's counter method (FIFO-bracketed go/DONE window on the counter build), for base reproduction only."""
	ctl, ack, raw = tmp / "c.ctl", tmp / "c.ack", tmp / "c.jsonl"
	for p in (ctl, ack, raw):
		if p.exists():
			p.unlink()
	os.mkfifo(ctl)
	os.mkfifo(ack)
	cf, af = os.open(ctl, os.O_RDWR | os.O_NONBLOCK), os.open(ack, os.O_RDWR | os.O_NONBLOCK)
	child = perf = None
	try:
		argv = [str(BIN[v]["counter"]), mode, *([str(path_for(work))] if work else [])]
		child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
		assert select.select([child.stderr], [], [], 10)[0] and child.stderr.readline() == "READY\n"
		assert os.sched_getaffinity(child.pid) == {4}, ("counter target affinity", os.sched_getaffinity(child.pid))
		perf = subprocess.Popen(["taskset", "-c", "0", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "-p", str(child.pid),
			"-D", "-1", "--control", f"fifo:{ctl},{ack}", "-o", str(raw)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

		def control(m):
			os.write(cf, (m + "\n").encode())
			assert select.select([af], [], [], 10)[0], m
			assert os.read(af, 1024).rstrip(b"\0") == b"ack\n"
		control("enable")
		child.stdin.write("go\n")
		child.stdin.flush()
		deadline = time.monotonic() + 120
		while True:
			assert time.monotonic() < deadline
			line = child.stderr.readline()
			assert line, "counter child exited early"
			if line == "DONE\n":
				break
		control("disable")
		child.stdin.write("stop\n")
		child.stdin.flush()
		child.communicate(timeout=10)
		assert child.returncode == 0
		perf.send_signal(signal.SIGINT)
		perf.communicate(timeout=10)
		text = raw.read_text()
		return parse(text)["instructions"], text, argv
	finally:
		for p in (child, perf):
			if p is not None and p.poll() is None:
				p.kill()
				p.wait()
		os.close(cf)
		os.close(af)
		ctl.unlink()
		ack.unlink()


def resident(entries, tmp, label):
	"""Run one resident block; entries are (key, argv, expected stdout). Returns ms per entry, with order receipts checked."""
	plan = tmp / f"{label}.plan"
	lines = [str(len(entries))]
	for _, argv, _ in entries:
		lines.append(str(len(argv)))
		lines += [a.encode().hex() for a in argv]
	plan.write_text("\n".join(lines) + "\n")
	r = subprocess.run(["taskset", "-c", "4", str(CLOCK), str(plan)], capture_output=True, text=True, timeout=1800)
	assert r.returncode == 0, r.stderr[-300:]
	rec = r.stdout.splitlines()
	assert len(rec) == 6 * len(entries), (label, len(rec), len(entries))
	out = []
	for i, (key, argv, expect) in enumerate(entries):
		block = rec[6 * i: 6 * i + 6]
		assert block[0] == f"EXEC {i}", block[0]
		assert block[1] == " ".join(a.encode().hex() for a in argv), (label, i, "argv receipt")
		ns, status = int(block[2]), int(block[3])
		stdout = bytes.fromhex(block[4]).decode()
		assert status == 0 and stdout == expect and ns > 0, (label, key, status, stdout[:80])
		out.append((key, ns / 1e6))
	(tmp / f"{label}.receipt.sha256").write_text(hashlib.sha256("\n".join(lines).encode()).hexdigest() + "\n")
	return out


def hf_median(argv):
	r = subprocess.run(["taskset", "-c", "4", "hyperfine", "-N", "--output=pipe", "-w", "5", "-r", "50", "--export-json", "/dev/stdout", " ".join(argv)],
		capture_output=True, text=True, timeout=300)
	assert r.returncode == 0, r.stderr[-300:]
	j = json.loads(r.stdout[r.stdout.index("{"):])
	return j["results"][0]["median"] * 1000


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	# Every subject runs on logical P-core 4, as in 0169 (its runner pinned itself). An unpinned child can land on an
	# E-core, where cpu_core events read <not counted> (attempt run1's failure).
	os.sched_setaffinity(0, {4})
	assert os.sched_getaffinity(0) == {4}
	assert os.stat(tmp).st_dev == os.stat(out).st_dev
	# Refuse before any work if a historical reference is missing or altered (run2 failed on a wrong path after calibration).
	ref69, r71 = read_0169(), read_0171()
	res = {"binaries": {v: {k: sha(p) for k, p in b.items()} for v, b in BIN.items()}, "clock": sha(CLOCK),
		"ledger": {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0],
			"controller_affinity": sorted(os.sched_getaffinity(0)), "cwd": os.getcwd(), "environment": dict(os.environ),
			"subjects": {v: {k: str(p) for k, p in b.items()} for v, b in BIN.items()}}}
	# 1. Correctness, origin-qualified.
	corr = {}
	for origin, d in (("corpus", CORPUS), ("fixtures", FIX)):
		for fx in sorted(d.glob("*.rn")):
			mode = "async" if fx.stem == "async" else "run"
			extra = ["2000000"] if fx.stem == "budget" else []
			a = subprocess.run([str(BIN["base"]["primary"]), mode, str(fx), *extra], capture_output=True, text=True, timeout=300)
			b = subprocess.run([str(BIN["cand"]["primary"]), mode, str(fx), *extra], capture_output=True, text=True, timeout=300)
			ra, rb = (a.returncode, a.stdout, a.stderr), (b.returncode, b.stdout, b.stderr)
			key = f"{origin}/{fx.stem}"
			assert key not in corr
			corr[key] = {"same": norm(ra) == norm(rb), "raw_identical": ra == rb, "base": list(ra), "cand": list(rb)}
			assert corr[key]["same"], (key, ra[:2], rb[:2])
			if origin == "fixtures":
				assert ra == (0, EXPECT[fx.stem], ""), (key, ra)
	res["correctness"] = corr
	alloc = {}
	for v in ("base", "cand"):
		for label, tail, expect in WORKLOADS[:5]:
			r = subprocess.run([str(BIN[v]["allocation"]), *tail], capture_output=True, text=True, timeout=300)
			assert r.returncode == 0 and r.stderr.splitlines()[-1].startswith("ALLOC "), (v, label, r.stderr[-200:])
			alloc[f"{v}-{label}"] = json.loads(r.stderr.splitlines()[-1][6:].replace("(", "[").replace(")", "]"))
	res["allocation"] = alloc
	assert alloc["cand-context"][0] <= alloc["base-context"][0], ("allocation calls rose", alloc)
	print("correctness:", len(corr), "identical; allocation context calls base/cand", alloc["base-context"][0], alloc["cand-context"][0], flush=True)
	# 2. Calibration of the resident driver against hyperfine --output=pipe.
	cal = {}
	for name, argv in (("true", ["/bin/true"]), ("floor", [str(BIN["base"]["primary"]), "floor"])):
		resident([("w", argv, "")] * 5, tmp, f"cal-warm-{name}")
		rows = resident([("x", argv, "")] * 50, tmp, f"cal-{name}")
		nat = statistics.median(ms for _, ms in rows)
		hf = hf_median(argv)
		cal[name] = {"native_ms": nat, "hyperfine_pipe_ms": hf, "difference_ms": nat - hf}
		assert abs(nat - hf) <= 0.15, ("calibration", cal)
	res["calibration"] = cal
	print("calibration:", {k: round(v["difference_ms"], 3) for k, v in cal.items()}, flush=True)
	# 3. Base reproduction (instructions only).
	repro = {}
	persist = out / "reproduction-samples.jsonl"
	DESCRIPTIVE = {("floor", None), ("empty-context", None)}  # amendment 7: historical tiny FIFO windows, report only
	for mode, work in REPRO_0169:
		vals = []
		for i in range(3):
			v, text, argv = fifo("base", mode, work, tmp)
			vals.append(v)
			with persist.open("a") as f:
				f.write(json.dumps({"reference": "0169", "mode": mode, "work": work, "index": i, "instructions": v, "raw": text, "argv": argv,
					"cwd": os.getcwd(), "affinity": [4]}) + "\n")
		got, want = statistics.median(vals), statistics.median(ref69[(mode, work)])
		repro[f"0169 fifo {mode} {work}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want, "ratio": got / want,
			"gated": (mode, work) not in DESCRIPTIVE, "source": f"{R0169_ARCHIVE}:{R0169_MEMBER}", "source_sha256": R0169_SHA256}
	for w in REPRO_0171:
		vals = []
		for i in range(3):
			c = perf_whole("base", ["run", str(path_for(w))], EXPECT[w])
			vals.append(c["instructions"])
			with persist.open("a") as f:
				f.write(json.dumps({"reference": "0171", "work": w, "index": i, "instructions": c["instructions"]}) + "\n")
		got, want = statistics.median(vals), statistics.median(r71[f"base-{w}"]["instructions"])
		repro[f"0171 whole-process run {w}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want, "ratio": got / want,
			"gated": True, "source": str(R0171), "source_sha256": R0171_SHA256}
	res["base_reproduction"] = repro
	(out / "base-reproduction.json").write_text(json.dumps(repro, indent=1) + "\n")
	bad = {k: v["ratio"] for k, v in repro.items() if v["gated"] and abs(v["ratio"] - 1) > 0.02}
	assert not bad, ("base reproduction", bad)
	print("base reproduction: all gated rows within 2%; descriptive:", {k: round(v["difference"]) for k, v in repro.items() if not v["gated"]}, flush=True)
	# 4. PMU, 5 repetitions, ABBA.
	pmu = {f"{v}-{l}": {"instructions": [], "cycles": []} for v in ("base", "cand") for l, _, _ in WORKLOADS}
	for rep in range(5):
		order = ("base", "cand") if rep % 2 == 0 else ("cand", "base")
		for label, tail, expect in WORKLOADS:
			for v in order:
				c = perf_whole(v, tail, expect)
				pmu[f"{v}-{label}"]["instructions"].append(c["instructions"])
				pmu[f"{v}-{label}"]["cycles"].append(c["cycles"])
	res["pmu"] = pmu
	print("pmu done", flush=True)
	# 5. Wall: warmup block, then 3 resident rounds; per round and workload ABBA (even) / BAAB (odd), blocks of 5.
	entries = [(f"{v}-{l}", [str(BIN[v]["primary"]), *t], e) for l, t, e in WORKLOADS for v in ("base", "cand")]
	resident(entries, tmp, "wall-warmup")
	walls = {f"{v}-{l}": [] for v in ("base", "cand") for l, _, _ in WORKLOADS}
	for rnd in range(3):
		plan = []
		for label, tail, expect in WORKLOADS:
			order = ("base", "cand", "cand", "base") if rnd % 2 == 0 else ("cand", "base", "base", "cand")
			for v in order:
				plan += [(f"{v}-{label}", [str(BIN[v]["primary"]), *tail], expect)] * 5
		for key, ms in resident(plan, tmp, f"wall-round-{rnd}"):
			walls[key].append(ms)
	assert all(len(x) == 30 for x in walls.values())
	res["wall_ms"] = walls
	print("wall done", flush=True)
	# 6. Decision.
	rows, regress, disagree = {}, [], []
	for label, _, _ in WORKLOADS:
		bi, ci = statistics.median(pmu[f"base-{label}"]["instructions"]), statistics.median(pmu[f"cand-{label}"]["instructions"])
		bw, cw = statistics.median(walls[f"base-{label}"]), statistics.median(walls[f"cand-{label}"])
		q = statistics.quantiles(walls[f"base-{label}"], n=10)
		band = q[-1] - q[0]
		di, dw = ci / bi - 1, cw / bw - 1
		rows[label] = {"base_instr": bi, "cand_instr": ci, "instr_change": di, "base_wall_ms": bw, "cand_wall_ms": cw, "wall_change": dw, "base_wall_p10_p90_ms": band}
		if di > 0.005:
			regress.append((label, "instructions", di))
		if cw - bw > band:
			regress.append((label, "wall", dw))
		if not (abs(di) <= 0.005 or abs(cw - bw) <= band) and di * dw < 0 and abs(di) > 0.03 and abs(dw) > 0.03:
			disagree.append((label, di, dw))
	if regress or disagree:
		decision = "STOP"
	elif rows[GATE]["instr_change"] <= -0.01:
		decision = "WIN"
	else:
		decision = "NO-WIN"
	res["decision"] = {"decision": decision, "rows": rows, "regressions": regress, "disagreements": disagree}
	res["ledger"].update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	(out / "measure.json").write_text(json.dumps(res, indent=1) + "\n")
	print(json.dumps({k: v for k, v in res["decision"].items() if k != "rows"}, indent=1))


if __name__ == "__main__":
	main(sys.argv[1])
