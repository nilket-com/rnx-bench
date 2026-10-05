"""rnx 0175 measurement (plan rnx 7699309 section 4, frozen before candidate timing). Run under the shared lock:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 measure.py OUT_DIR

Order: sentinel rehearsal; affinity controls; identity; (1) correctness and allocation controls; (2) historical
reproduction; (3) PMU, 5 true ABBA repetitions per workload; (4) resident-driver calibration then wall clock, 3 rounds
ABBA/BAAB/ABBA in blocks of 5; (5) Lua references (not gates); end controls; the frozen decision; the final sentinel
scan. Every phase writes its evidence to disk BEFORE asserting its gate. Subjects run from one staged path with
environment E0 exactly, inside their own process group with a deadline; the controller is pinned to CPU 4 and
children inherit it (per-sample fields are controller affinity; 10 representative grep controls observe a child).
"""
import io, json, lzma, math, os, pathlib, re, select, shutil, signal, statistics, subprocess, sys, tarfile, time
from common import HERE, E0, SOURCES, sha, text_sha, run_bounded, new_sentinel, count, scan, Ledger

sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = HERE / "bin"
CLOCK = HERE / "clock/plan_clock"
STAGE = HERE / "stage/primary"
CORPUS, FIX, RANGE, LUA = HERE / "corpus", HERE / "fixtures", HERE / "range", HERE / "lua"
CONTROL = ["perf", "stat", "--", "/usr/bin/grep", "Cpus_allowed_list", "/proc/self/status"]
LUA_BINS = {"lua54": pathlib.Path("/home/me/.local/bin/lua54"), "luajit": pathlib.Path("/home/me/.local/bin/luajit")}

# Historical references: this repository's committed copies, hash-verified before any work (0172's reviewed method).
REPO = HERE.parents[1]
R0169_ARCHIVE = REPO / "results/rune-runtime-0169-raw.tar.xz"
R0169_MEMBER = "results/rune-runtime-0169-attempt5b/counters.json"
R0169_SHA256 = "5e09153b85afbb9b2b464039527cada2b11ee2886afa70cdc1b7bbb689279734"
R0171 = REPO / "results/store-fast-path-0171/run1/measure.json"
R0171_SHA256 = "a653251c613b68d0b2e92bcb0f6f6f57a855bc5946a2a91593fd417e6f89b986"
REPRO_0169 = [("floor", None), ("empty-context", None), ("context", None), ("runtime", None), ("compile", "answer"),
	("run", "answer"), ("run", "empty"), ("run", "numeric"), ("run", "fib"), ("run", "strings")]
REPRO_0171 = ["while", "compare", "calls", "vector", "overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias"]
DESCRIPTIVE = {("floor", None), ("empty-context", None)}  # tiny FIFO windows: report only (0172 amendment 7)

_t = [f"item:{i}" for i in range(1, 20001)]
_s = "|".join(_t)
EXPECT = {"empty": "", "answer": "42\n", "numeric": "3\n", "fib": "196418\n", "strings": f"{len(_s)}\n{_s[0:19]}\n{_s[len(_s) - 21:]}\n"}
EXPECT.update({k: f"{v}\n" for k, v in EXPECTED.items()})


def path_for(work):
	for d in (CORPUS, FIX, RANGE):
		if (d / f"{work}.rn").exists():
			return d / f"{work}.rn"
	raise KeyError(work)


# The 0172 18-workload matrix plus the three frozen range controls.
WORKLOADS = [("floor", ["floor"], ""), ("empty-context", ["empty-context"], ""), ("context", ["context"], ""),
	("runtime", ["runtime"], ""), ("compile-answer", ["compile", str(path_for("answer"))], "")]
WORKLOADS += [(f"run-{w}", ["run", str(path_for(w))], EXPECT[w]) for w in
	["answer", "empty", "numeric", "fib", "strings", "while", "compare", "calls", "vector",
	"overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias",
	"range_signed", "range_negative", "range_while"]]
WIN_INSTR = ["run-numeric", "run-range_signed", "run-range_negative"]
WIN_ALLOC = "run-numeric"
RANGE_ALLOC = {"run-numeric", "run-range_signed", "run-range_negative"}
NO_STD_CONTEXT = {"floor", "empty-context"}  # Context::new() or nothing: no ops module, no tagged registration
NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]
HASHES = {}
REHEARSAL = False


def persist(out, name, obj):
	(out / name).write_text(json.dumps(obj, indent=1) + "\n")


def pinned():
	got = sorted(os.sched_getaffinity(0))
	assert got == [4], ("controller affinity", got)
	return got


def norm(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


def stage(subject):
	STAGE.parent.mkdir(exist_ok=True)
	tmp = STAGE.parent / f".staging-{subject}"
	shutil.copy2(BIN / f"{subject}-primary", tmp)
	os.replace(tmp, STAGE)
	assert sha(STAGE) == HASHES[subject], (subject, "staged hash")
	return STAGE


def controls(label):
	rows = []
	for i in range(5):
		pinned()
		r = run_bounded(CONTROL, 30, E0)
		rows.append({"argv": CONTROL, "env": E0, "status": r.returncode, "stdout": r.stdout})
		assert r.returncode == 0 and r.stdout == "Cpus_allowed_list:\t4\n", (label, i, r.returncode, r.stdout)
	return rows


def parse(text):
	got = {}
	for line in text.splitlines():
		if line.startswith("{"):
			row = json.loads(line)
			name = next((n for n in ("instructions", "cycles") if row.get("event") in (n + ":u", f"cpu_core/{n}/u")), None)
			if name:
				assert float(row["pcnt-running"]) >= 99, row
				val = float(row["counter-value"])
				assert math.isfinite(val) and val > 0, row
				got[name] = val
	assert set(got) == {"instructions", "cycles"}, text[-300:]
	return got


def perf(exe, tail, expect):
	argv = [str(exe), *tail]
	aff = pinned()
	r = run_bounded(["perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--", *argv], 300, E0)
	sample = {"argv": argv, "env": E0, "cwd": os.getcwd(), "controller_affinity": aff, "status": r.returncode, "stdout": r.stdout,
		"raw_perf": r.stderr}
	assert r.returncode == 0 and r.stdout == expect, (argv, r.stdout[:80], r.stderr[-300:])
	return {**sample, **parse(r.stderr)}


def fifo(mode, work, tmp):
	"""0169's counter method (FIFO-bracketed go/DONE window on the base counter build), for reproduction only."""
	ctl, ack, raw = tmp / "c.ctl", tmp / "c.ack", tmp / "c.jsonl"
	for p in (ctl, ack, raw):
		if p.exists():
			p.unlink()
	os.mkfifo(ctl)
	os.mkfifo(ack)
	cf, af = os.open(ctl, os.O_RDWR | os.O_NONBLOCK), os.open(ack, os.O_RDWR | os.O_NONBLOCK)
	child = counter = None
	try:
		argv = [str(BIN / "base-counter"), mode, *([str(path_for(work))] if work else [])]
		pinned()
		child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=E0,
			start_new_session=True)
		assert select.select([child.stderr], [], [], 10)[0] and child.stderr.readline() == "READY\n"
		assert os.sched_getaffinity(child.pid) == {4}, ("counter target affinity", os.sched_getaffinity(child.pid))
		counter = subprocess.Popen(["taskset", "-c", "0", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u",
			"-p", str(child.pid), "-D", "-1", "--control", f"fifo:{ctl},{ack}", "-o", str(raw)], stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, text=True, env=E0, start_new_session=True)

		def control(m):
			os.write(cf, (m + "\n").encode())
			assert select.select([af], [], [], 10)[0], m
			assert os.read(af, 1024).rstrip(b"\0") == b"ack\n"
		control("enable")
		child.stdin.write("go\n")
		child.stdin.flush()
		deadline = time.monotonic() + 120
		while True:
			left = deadline - time.monotonic()
			assert left > 0 and select.select([child.stderr], [], [], left)[0], "counter child: no DONE before deadline"
			line = child.stderr.readline()
			assert line, "counter child exited early"
			if line == "DONE\n":
				break
		control("disable")
		child.stdin.write("stop\n")
		child.stdin.flush()
		child.communicate(timeout=10)
		assert child.returncode == 0
		counter.send_signal(signal.SIGINT)
		counter.communicate(timeout=10)
		text = raw.read_text()
		return parse(text)["instructions"], text, argv
	finally:
		for p in (child, counter):
			if p is not None and p.poll() is None:
				os.killpg(p.pid, signal.SIGKILL)
				p.wait()
		os.close(cf)
		os.close(af)
		ctl.unlink()
		ack.unlink()


def read_0169():
	data = tarfile.open(R0169_ARCHIVE).extractfile(R0169_MEMBER).read()
	assert __import__("hashlib").sha256(data).hexdigest() == R0169_SHA256, "0169 reference hash"
	sums = (REPO / "results/rune-runtime-0169-SHA256SUMS").read_text()
	assert f"{R0169_SHA256}  {R0169_MEMBER}" in sums, "0169 reference not in SHA256SUMS"
	ref = {}
	for r in json.loads(data):
		if r["base"] == "new":
			ref.setdefault((r["mode"], r["work"]), []).append(r["counts"]["instructions"])
	for key in REPRO_0169:
		assert len(ref.get(key, [])) >= 3 and all(isinstance(v, (int, float)) and v > 0 for v in ref[key]), ("0169 reference rows", key)
	return ref


def read_0171():
	data = R0171.read_bytes()
	assert __import__("hashlib").sha256(data).hexdigest() == R0171_SHA256, "0171 reference hash"
	pmu = json.loads(data)["pmu"]
	for w in REPRO_0171:
		v = pmu[f"base-{w}"]["instructions"]
		assert len(v) == 5 and all(isinstance(x, (int, float)) and x > 0 for x in v), ("0171 reference rows", w)
	return pmu


def compare(left, right, workloads, out, name):
	"""5 true ABBA repetitions (L R R L) per workload; raw perf JSON retained per sample, written before any summary."""
	samples = []
	path = out / f"pmu-{name}.jsonl"
	with path.open("w") as f:
		for rep in range(5):
			for label, tail, expect in workloads:
				for side in ("L", "R", "R", "L"):
					subject = left if side == "L" else right
					exe = stage(subject)
					s = perf(exe, tail, expect)
					after = sha(exe)
					row = {"rep": rep, "workload": label, "side": side, "subject": subject, "hash": HASHES[subject], "hash_after": after, **s}
					f.write(json.dumps(row) + "\n")
					f.flush()
					assert after == HASHES[subject], (name, "stage changed during sample")
					samples.append(row)
	rows = {}
	for label, _, _ in workloads:
		row = {}
		for n in ("instructions", "cycles"):
			l = [s[n] for s in samples if s["workload"] == label and s["side"] == "L"]
			r = [s[n] for s in samples if s["workload"] == label and s["side"] == "R"]
			assert len(l) == 10 and len(r) == 10
			row[n] = {"base": l, "cand": r, "base_median": statistics.median(l), "cand_median": statistics.median(r),
				"change": statistics.median(r) / statistics.median(l) - 1}
		rows[label] = row
	return rows


def resident(argv, expect, n, tmp, label, subject=None):
	"""One resident-driver process running n samples of one command; ms per sample, receipts checked."""
	if subject is not None:
		exe = stage(subject)
		argv = [str(exe), *argv]
	lines = [str(n)]
	for _ in range(n):
		lines.append(str(len(argv)))
		lines += [a.encode().hex() for a in argv]
	plan = tmp / "block.plan"
	plan.write_text("\n".join(lines) + "\n")
	pinned()
	r = run_bounded([str(CLOCK), str(plan)], 1800, E0)
	assert r.returncode == 0, (label, r.stderr[-300:])
	if subject is not None:
		assert sha(STAGE) == HASHES[subject], (label, "stage changed during block")
	rec = r.stdout.splitlines()
	assert len(rec) == 6 * n, (label, len(rec), n)
	got = []
	for i in range(n):
		block = rec[6 * i: 6 * i + 6]
		assert block[0] == f"EXEC {i}" and block[1] == " ".join(a.encode().hex() for a in argv), (label, i, "receipt")
		ns, status = int(block[2]), int(block[3])
		assert status == 0 and bytes.fromhex(block[4]).decode() == expect and ns > 0, (label, i, status)
		got.append(ns / 1e6)
	return got


def wall(workloads, tmp, out):
	"""3 rounds: ABBA (rounds 1 and 3) / BAAB (round 2), blocks of 5, 30 samples per side per workload."""
	rows = {}
	with (out / "wall-blocks.jsonl").open("w") as f:
		for label, tail, expect in workloads:
			got = {"base": [], "cand": []}
			for rnd in range(3):
				order = ("base", "cand", "cand", "base") if rnd % 2 == 0 else ("cand", "base", "base", "cand")
				for subject in order:
					ms = resident(tail, expect, 5, tmp, f"wall-{label}-{rnd}-{subject}", subject)
					f.write(json.dumps({"workload": label, "round": rnd, "subject": subject, "hash": HASHES[subject], "ms": ms}) + "\n")
					f.flush()
					got[subject] += ms
			assert len(got["base"]) == 30 and len(got["cand"]) == 30
			q = statistics.quantiles(got["base"], n=10)
			rows[label] = {"base": got["base"], "cand": got["cand"], "base_median_ms": statistics.median(got["base"]),
				"cand_median_ms": statistics.median(got["cand"]), "base_p10_p90_ms": q[-1] - q[0],
				"change": statistics.median(got["cand"]) / statistics.median(got["base"]) - 1}
	return rows


def hf_median(argv):
	pinned()
	r = run_bounded(["hyperfine", "-N", "--output=pipe", "-w", "5", "-r", "50", "--export-json", "/dev/stdout", " ".join(argv)], 300, E0)
	assert r.returncode == 0, r.stderr[-300:]
	return json.loads(r.stdout[r.stdout.index("{"):])["results"][0]["median"] * 1000


def rehearse(out, sentinel):
	"""Sentinel rehearsal: results, a failing command (exception text and argv), the ledger, an archive, a command log."""
	assert count(b"x" + sentinel.encode(), "", [sentinel]) == 1, "scanner positive control (plain)"
	packed = lzma.compress(b"x" + sentinel.encode())
	assert count(packed, ".xz", [sentinel]) == count(packed, "", [sentinel]) + 1, "scanner positive control (.xz)"
	r = out / "rehearsal"
	r.mkdir()
	ledger = Ledger(r / "commands.jsonl")
	s = perf(BIN / "base-primary", ["floor"], "")
	(r / "result.json").write_text(json.dumps(s, indent=1) + "\n")
	ledger.write(kind="sample", argv=s["argv"], env=E0)
	failing = [str(BIN / "base-primary"), "run", str(r / "missing.rn")]
	f = run_bounded(failing, 60, E0)
	assert f.returncode != 0
	try:
		raise subprocess.CalledProcessError(f.returncode, failing, f.stdout, f.stderr)
	except subprocess.CalledProcessError as e:
		ledger.write(kind="failure", argv=failing, env=E0, status=f.returncode, stderr=f.stderr, exception=str(e))
	(r / "command.log").write_text(" ".join(failing) + "\n" + f.stderr)
	buf = io.BytesIO()
	with tarfile.open(fileobj=buf, mode="w") as t:
		t.add(r, arcname="rehearsal")
	(r / "rehearsal.tar.xz").write_bytes(lzma.compress(buf.getvalue()))
	hits = scan(r, [sentinel])
	assert not hits, ("STOP: sentinel found in rehearsal output", hits)
	return {"files": sorted(str(p.relative_to(out)) for p in r.rglob("*") if p.is_file()), "occurrences": 0}


def decide(pmu, walls, alloc, res):
	rows, regress, disagree = {}, [], []
	for label, _, _ in WORKLOADS:
		bi, ci = pmu[label]["instructions"]["base_median"], pmu[label]["instructions"]["cand_median"]
		w = walls[label]
		bw, cw, band = w["base_median_ms"], w["cand_median_ms"], w["base_p10_p90_ms"]
		di, dw = ci / bi - 1, cw / bw - 1
		rows[label] = {"base_instr": bi, "cand_instr": ci, "instr_change": di, "base_wall_ms": bw, "cand_wall_ms": cw,
			"wall_change": dw, "base_wall_p10_p90_ms": band}
		if di > 0.005:
			regress.append((label, "instructions", di))
		if cw - bw > band:
			regress.append((label, "wall", dw))
		if not (abs(di) <= 0.005 or abs(cw - bw) <= band) and di * dw < 0 and abs(di) > 0.03 and abs(dw) > 0.03:
			disagree.append((label, di, dw))
	if regress or disagree:
		decision = "STOP"
	elif all(rows[w]["instr_change"] <= -0.10 for w in WIN_INSTR) and alloc[WIN_ALLOC]["calls_change"] <= -0.90:
		decision = "WIN"
	else:
		decision = "NO-WIN"
	return {"decision": decision, "rows": rows, "regressions": regress, "disagreements": disagree,
		"win_instr": {w: rows[w]["instr_change"] for w in WIN_INSTR}, "win_alloc": alloc[WIN_ALLOC]["calls_change"]}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	assert os.stat(tmp).st_dev == os.stat(out).st_dev
	sentinel = new_sentinel()
	os.sched_setaffinity(0, {4})
	pinned()
	ref69, r71 = read_0169(), read_0171()
	res = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0], "env": E0, "sources": SOURCES}
	for s in ("base", "cand"):
		HASHES[s] = sha(BIN / f"{s}-primary")
	res["identity"] = {f"{s}-{k}": {"sha256": sha(BIN / f"{s}-{k}"), "text_sha256": text_sha(BIN / f"{s}-{k}")}
		for s in ("base", "cand") for k in ("primary", "counter", "allocation")}
	res["clock"] = {"sha256": sha(CLOCK)}
	res["lua"] = {k: {"path": str(p), "sha256": sha(p), "version": run_bounded([str(p), "-v"], 10, E0).stdout.strip() or
		run_bounded([str(p), "-v"], 10, E0).stderr.strip()} for k, p in LUA_BINS.items()}
	persist(out, "partial.json", res)
	res["rehearsal"] = rehearse(out, sentinel)
	print("rehearsal: 0 occurrences", flush=True)
	res["controls_start"] = controls("start")
	persist(out, "partial.json", res)
	# 1. Correctness: 36 origin-qualified fixtures base vs candidate; range fixtures against the oracle on both.
	corr = {}
	for origin, d in (("corpus", CORPUS), ("fixtures", FIX), ("range", RANGE)):
		for fx in sorted(d.glob("*.rn")):
			mode = "async" if fx.stem == "async" else "run"
			extra = ["2000000"] if fx.stem == "budget" else []
			a = run_bounded([str(BIN / "base-primary"), mode, str(fx), *extra], 300, E0)
			b = run_bounded([str(BIN / "cand-primary"), mode, str(fx), *extra], 300, E0)
			ra, rb = (a.returncode, a.stdout, a.stderr), (b.returncode, b.stdout, b.stderr)
			key = f"{origin}/{fx.stem}"
			corr[key] = {"same": norm(ra) == norm(rb), "raw_identical": ra == rb, "base": list(ra), "cand": list(rb)}
			if origin != "corpus":
				corr[key]["oracle"] = ra == (0, EXPECT[fx.stem], "") and rb == (0, EXPECT[fx.stem], "")
	persist(out, "correctness.json", corr)
	assert len(corr) == 40, len(corr)
	bad = [k for k, v in corr.items() if not v["same"] or v.get("oracle") is False]
	assert not bad, ("STOP: correctness", bad)
	res["correctness"] = {"checked": len(corr), "all_identical": True}
	print("correctness:", len(corr), "identical", flush=True)
	# Allocation controls: separate counting builds, every workload plus manual-next, exact outputs.
	alloc = {}
	for label, tail, expect in WORKLOADS + [("run-manual_next", ["run", str(path_for("manual_next"))], EXPECT["manual_next"])]:
		row = {}
		for s in ("base", "cand"):
			r = run_bounded([str(BIN / f"{s}-allocation"), *tail], 300, E0)
			last = r.stderr.splitlines()[-1] if r.stderr else ""
			row[s] = {"status": r.returncode, "stdout": r.stdout, "alloc_line": last}
			if r.returncode == 0 and r.stdout == expect and last.startswith("ALLOC "):
				calls, nbytes, live, peak = json.loads(last[6:])
				row[s].update(calls=calls, bytes=nbytes, live=live, peak=peak)
		alloc[label] = row
		if "calls" in row["base"] and "calls" in row["cand"]:
			row["calls_delta"] = row["cand"]["calls"] - row["base"]["calls"]
			row["calls_change"] = row["cand"]["calls"] / row["base"]["calls"] - 1
	persist(out, "allocation.json", alloc)
	assert all("calls_delta" in v for v in alloc.values()), ("STOP: allocation run", [k for k, v in alloc.items() if "calls_delta" not in v])
	# Qualification (accepted in review): exactly one temporary allocation for the tagged registration, wherever the
	# std modules are installed; none without them. No other workload may rise.
	over = {k: v["calls_delta"] for k, v in alloc.items() if k not in RANGE_ALLOC
		and v["calls_delta"] > (0 if k in NO_STD_CONTEXT else 1)}
	res["allocation"] = {"context_delta": alloc["context"]["calls_delta"], "context_delta_is_plus_one": alloc["context"]["calls_delta"] == 1,
		"numeric_calls": [alloc[WIN_ALLOC]["base"]["calls"], alloc[WIN_ALLOC]["cand"]["calls"]], "rises": over}
	persist(out, "partial.json", res)
	assert not over, ("STOP: allocation calls rose", over)
	# The manual-next control keeps every Option it observes, so it must lose no allocation: its delta equals context's.
	assert alloc["run-manual_next"]["calls_delta"] == alloc["context"]["calls_delta"], ("STOP: manual-next allocations changed",
		alloc["run-manual_next"]["calls_delta"], alloc["context"]["calls_delta"])
	print("allocation: context delta", res["allocation"]["context_delta"], "numeric calls", res["allocation"]["numeric_calls"], flush=True)
	if REHEARSAL:
		res.update(ended=time.time(), rehearsal_only=True)
		shutil.rmtree(tmp)
		(out / "partial.json").unlink()
		persist(out, "rehearsal-measure.json", res)
		hits = scan(out, [sentinel])
		assert not hits, ("STOP: sentinel found in rehearsal-mode output", hits)
		print("rehearsal mode: stopped before any timed phase; sentinel 0 occurrences", flush=True)
		return
	# 2. Historical reproduction on the base (0172's reviewed method; tiny FIFO windows descriptive).
	repro = {}
	with (out / "reproduction-samples.jsonl").open("w") as f:
		for mode, work in REPRO_0169:
			vals = []
			for i in range(3):
				v, text, argv = fifo(mode, work, tmp)
				vals.append(v)
				f.write(json.dumps({"reference": "0169", "mode": mode, "work": work, "index": i, "instructions": v, "raw": text,
					"argv": argv, "env": E0, "controller_affinity": [4]}) + "\n")
				f.flush()
			got, want = statistics.median(vals), statistics.median(ref69[(mode, work)])
			repro[f"0169 fifo {mode} {work}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want,
				"ratio": got / want, "gated": (mode, work) not in DESCRIPTIVE}
		for w in REPRO_0171:
			vals = []
			for i in range(3):
				c = perf(stage("base"), ["run", str(path_for(w))], EXPECT[w])
				vals.append(c["instructions"])
				f.write(json.dumps({"reference": "0171", "work": w, "index": i, "instructions": c["instructions"], "raw": c["raw_perf"]}) + "\n")
				f.flush()
			got, want = statistics.median(vals), statistics.median(r71[f"base-{w}"]["instructions"])
			repro[f"0171 whole-process run {w}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want,
				"ratio": got / want, "gated": True}
	persist(out, "base-reproduction.json", repro)
	bad = {k: v["ratio"] for k, v in repro.items() if v["gated"] and abs(v["ratio"] - 1) > 0.02}
	assert not bad, ("STOP: base reproduction", bad)
	print("reproduction: gated rows within 2%; descriptive", {k: round(v["difference"]) for k, v in repro.items() if not v["gated"]}, flush=True)
	# 3. PMU.
	pmu = compare("base", "cand", WORKLOADS, out, "base-vs-cand")
	persist(out, "pmu.json", pmu)
	print("pmu done", flush=True)
	# 4. Calibration first, then wall.
	cal = {}
	for name, argv, subject in (("true", ["/bin/true"], None), ("floor", ["floor"], "base")):
		resident(argv, "", 5, tmp, f"cal-warm-{name}", subject)
		nat = statistics.median(resident(argv, "", 50, tmp, f"cal-{name}", subject))
		hf = hf_median([str(STAGE), "floor"] if subject else argv)
		cal[name] = {"native_ms": nat, "hyperfine_pipe_ms": hf, "difference_ms": nat - hf}
	res["calibration"] = cal
	persist(out, "partial.json", res)
	assert all(abs(v["difference_ms"]) <= 0.15 for v in cal.values()), ("STOP: calibration", cal)
	print("calibration:", {k: round(v["difference_ms"], 3) for k, v in cal.items()}, flush=True)
	walls = wall(WORKLOADS, tmp, out)
	persist(out, "wall.json", walls)
	print("wall done", flush=True)
	# 5. Lua references under the same clock (not gates).
	lua = {}
	for binary, path in LUA_BINS.items():
		for script, expect in (("numeric", EXPECT["numeric"]), ("while", EXPECT["while"])):
			resident([str(path), str(LUA / f"{script}.lua")], expect, 5, tmp, f"lua-warm-{binary}-{script}")
			ms = []
			for _ in range(6):
				ms += resident([str(path), str(LUA / f"{script}.lua")], expect, 5, tmp, f"lua-{binary}-{script}")
			lua[f"{binary}-{script}"] = {"ms": ms, "median_ms": statistics.median(ms)}
	res["lua_reference"] = lua
	res["controls_end"] = controls("end")
	res.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	res["decision"] = decide(pmu, walls, alloc, res)
	shutil.rmtree(tmp)
	(out / "partial.json").unlink()
	persist(out, "measure.json", res)
	hits = scan(out, [sentinel])
	assert not hits, ("STOP: sentinel found in official output", hits)
	persist(out, "sentinel-scan.json", {"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": 0})
	d = res["decision"]
	print("DECISION", d["decision"], "regressions", d["regressions"], "disagreements", d["disagreements"], flush=True)
	print("win instr", {k: f"{v * 100:+.2f}%" for k, v in d["win_instr"].items()}, "numeric alloc", f"{d['win_alloc'] * 100:+.2f}%", flush=True)
	for k, v in d["rows"].items():
		print(f"{k}: instr {v['instr_change'] * 100:+.3f}% wall {v['wall_change'] * 100:+.2f}% (band {v['base_wall_p10_p90_ms']:.3f} ms)", flush=True)
	print("lua", {k: round(v["median_ms"], 3) for k, v in lua.items()}, flush=True)


if __name__ == "__main__":
	# --rehearsal: untimed receipts only (rehearsal, controls, correctness, allocation); no PMU, FIFO or wall timing.
	REHEARSAL = sys.argv[1:2] == ["--rehearsal"]
	main(sys.argv[-1])
