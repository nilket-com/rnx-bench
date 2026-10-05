"""rnx 0174 build-profile study (plan rnx 4866b00, sections 3, 4 and 8). Descriptive only: no tolerance, no gate.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 measure.py OUT_DIR

Order: sentinel rehearsal (STOP on any occurrence); affinity controls; identity; correctness of every binary against
base-p0 (36 fixtures, environment E0); whole-process PMU comparisons (i) and (ii) and rnx eval 42, each 5 true ABBA
repetitions per workload; the resident-driver calibration; wall clock for (i) and rnx eval 42 (3 rounds ABBA/BAAB/ABBA,
blocks of 5, one resident process per block); end affinity controls; the final sentinel scan.

Every subject runs from one fixed staged path per binary family (stage/primary for the harness, stage/rnxbin for rnx,
equal length), atomically replaced and hash-verified before and after every sample or block, with environment E0
exactly. The controller is pinned to CPU 4 and children inherit it through subprocess -> perf stat -> subject (or
subprocess -> plan_clock -> subject); per-sample fields are controller affinity, checked before every sample.
"""
import io, json, lzma, os, pathlib, re, shutil, statistics, subprocess, sys, tarfile, time
from common import HERE, E0, sha, text_sha, new_sentinel, count, scan, Ledger

sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = HERE / "bin"
PROFILES = ["p0", "p1", "p2", "p3"]
HARNESS = [f"{s}-{p}" for s in ("base", "s71", "s72") for p in PROFILES]
RNX = [f"rnx-{p}" for p in PROFILES]
CORPUS, FIX = HERE / "corpus", HERE / "fixtures"
STAGE = {"harness": HERE / "stage/primary", "rnx": HERE / "stage/rnxbin"}
CLOCK = HERE / "clock/plan_clock"
CONTROL = ["perf", "stat", "--", "/usr/bin/grep", "Cpus_allowed_list", "/proc/self/status"]

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
EVAL = [("eval-42", ["eval", "42"], "42\n")]
NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]
HASHES = {}


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
	family = "rnx" if subject.startswith("rnx-") else "harness"
	dest = STAGE[family]
	dest.parent.mkdir(exist_ok=True)
	tmp = dest.parent / f".staging-{subject}"
	shutil.copy2(BIN / subject, tmp)
	os.replace(tmp, dest)
	assert sha(dest) == HASHES[subject], (subject, "staged hash")
	return dest


def controls(label):
	"""Representative child affinity control: same env and launch path as the subjects, exact output, 5 times."""
	rows = []
	for i in range(5):
		pinned()
		r = subprocess.run(CONTROL, capture_output=True, text=True, timeout=30, env=E0)
		assert r.returncode == 0 and r.stdout == "Cpus_allowed_list:\t4\n", (label, i, r.returncode, r.stdout)
		rows.append({"argv": CONTROL, "env": E0, "status": r.returncode, "stdout": r.stdout})
	return rows


def perf(exe, tail, expect):
	argv = [str(exe), *tail]
	aff = pinned()
	r = subprocess.run(["perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--", *argv],
		capture_output=True, text=True, timeout=300, env=E0)
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
	return {"argv": argv, "env": E0, "cwd": os.getcwd(), "controller_affinity": aff, "stdout": r.stdout, "raw_perf": r.stderr, **counts}


def compare(name, left, right, workloads, out):
	"""5 true ABBA repetitions (L R R L) per workload, whole-process counts, raw perf JSON retained per sample."""
	samples = []
	for rep in range(5):
		for label, tail, expect in workloads:
			for side in ("L", "R", "R", "L"):
				subject = left if side == "L" else right
				exe = stage(subject)
				s = perf(exe, tail, expect)
				after = sha(exe)
				assert after == HASHES[subject], (name, "stage changed during sample")
				samples.append({"comparison": name, "rep": rep, "workload": label, "side": side, "subject": subject,
					"hash": HASHES[subject], "hash_after": after, **s})
	with (out / f"pmu-{name}.jsonl").open("w") as f:
		for s in samples:
			f.write(json.dumps(s) + "\n")
	rows = {}
	for label, _, _ in workloads:
		row = {}
		for n in ("instructions", "cycles"):
			l = [s[n] for s in samples if s["workload"] == label and s["side"] == "L"]
			r = [s[n] for s in samples if s["workload"] == label and s["side"] == "R"]
			assert len(l) == 10 and len(r) == 10
			row[n] = {"left": l, "right": r, "left_median": statistics.median(l), "right_median": statistics.median(r),
				"change": statistics.median(r) / statistics.median(l) - 1}
		rows[label] = row
	return rows


def resident(subject, tail, expect, n, tmp, label):
	"""One resident-driver process running n samples of one staged subject; returns ms per sample, receipts checked."""
	exe = stage(subject)
	argv = [str(exe), *tail]
	lines = [str(n)]
	for _ in range(n):
		lines.append(str(len(argv)))
		lines += [a.encode().hex() for a in argv]
	plan = tmp / "block.plan"
	plan.write_text("\n".join(lines) + "\n")
	pinned()
	r = subprocess.run([str(CLOCK), str(plan)], capture_output=True, text=True, timeout=1800, env=E0)
	assert r.returncode == 0, (label, r.stderr[-300:])
	assert sha(exe) == HASHES[subject], (label, "stage changed during block")
	rec = r.stdout.splitlines()
	assert len(rec) == 6 * n, (label, len(rec), n)
	out = []
	for i in range(n):
		block = rec[6 * i: 6 * i + 6]
		assert block[0] == f"EXEC {i}" and block[1] == " ".join(a.encode().hex() for a in argv), (label, i, "receipt")
		ns, status = int(block[2]), int(block[3])
		assert status == 0 and bytes.fromhex(block[4]).decode() == expect and ns > 0, (label, i, status)
		out.append(ns / 1e6)
	return out


def wall(name, left, right, workloads, tmp, warmup):
	"""3 rounds: ABBA (rounds 1 and 3) / BAAB (round 2), blocks of 5, 30 samples per side per workload."""
	rows = {}
	for label, tail, expect in workloads:
		if warmup:
			for subject in (left, right):
				resident(subject, tail, expect, warmup, tmp, f"{name}-{label}-warmup")
		got = {"L": [], "R": []}
		blocks = []
		for rnd in range(3):
			order = ("L", "R", "R", "L") if rnd % 2 == 0 else ("R", "L", "L", "R")
			for side in order:
				subject = left if side == "L" else right
				ms = resident(subject, tail, expect, 5, tmp, f"{name}-{label}-{rnd}-{side}")
				got[side] += ms
				blocks.append({"round": rnd, "side": side, "subject": subject, "ms": ms})
		assert len(got["L"]) == 30 and len(got["R"]) == 30
		lm, rm = statistics.median(got["L"]), statistics.median(got["R"])
		rows[label] = {"left": got["L"], "right": got["R"], "left_median_ms": lm, "right_median_ms": rm, "change": rm / lm - 1, "blocks": blocks}
	return rows


def hf_median(argv):
	pinned()
	r = subprocess.run(["hyperfine", "-N", "--output=pipe", "-w", "5", "-r", "50", "--export-json", "/dev/stdout", " ".join(argv)],
		capture_output=True, text=True, timeout=300, env=E0)
	assert r.returncode == 0, r.stderr[-300:]
	return json.loads(r.stdout[r.stdout.index("{"):])["results"][0]["median"] * 1000


def rehearse(out, sentinel):
	"""Sentinel rehearsal: normal results, a failing command, the ledger, an archive and the command log, then a scan."""
	# Scanner positive controls: plain bytes, and an .xz stream whose decompressed copy must add to the raw count
	# (random hex is incompressible, so it may also appear verbatim inside the compressed bytes).
	assert count(b"x" + sentinel.encode(), "", [sentinel]) == 1, "scanner positive control (plain)"
	packed = lzma.compress(b"x" + sentinel.encode())
	assert count(packed, ".xz", [sentinel]) == count(packed, "", [sentinel]) + 1, "scanner positive control (.xz)"
	r = out / "rehearsal"
	r.mkdir()
	ledger = Ledger(r / "commands.jsonl")
	s = perf(BIN / "base-p0", ["floor"], "")
	(r / "result.json").write_text(json.dumps(s, indent=1) + "\n")
	ledger.write(kind="sample", argv=s["argv"], env=E0)
	failing = [str(BIN / "base-p0"), "run", str(r / "missing.rn")]
	f = subprocess.run(failing, capture_output=True, text=True, timeout=60, env=E0)
	assert f.returncode != 0
	try:
		subprocess.run(failing, capture_output=True, text=True, timeout=60, env=E0, check=True)
	except subprocess.CalledProcessError as e:
		ledger.write(kind="failure", argv=failing, env=E0, status=f.returncode, stderr=f.stderr, exception=str(e))
	(r / "command.log").write_text(" ".join(failing) + "\n" + f.stderr)
	buf = io.BytesIO()
	with tarfile.open(fileobj=buf, mode="w") as t:
		t.add(r, arcname="rehearsal")
	(r / "rehearsal.tar.xz").write_bytes(lzma.compress(buf.getvalue()))
	hits = scan(r, [sentinel])
	assert not hits, ("STOP: sentinel found in rehearsal output", {k: v for k, v in hits.items()})
	return {"files": sorted(str(p.relative_to(out)) for p in r.rglob("*") if p.is_file()), "occurrences": 0}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	sentinel = new_sentinel()
	os.sched_setaffinity(0, {4})
	pinned()
	res = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0], "env": E0}
	for s in HARNESS + RNX:
		HASHES[s] = sha(BIN / s)
	res["identity"] = {s: {"sha256": HASHES[s], "text_sha256": text_sha(BIN / s), "bytes": (BIN / s).stat().st_size} for s in HARNESS + RNX}
	res["clock"] = {"sha256": sha(CLOCK)}
	res["rehearsal"] = rehearse(out, sentinel)
	print("rehearsal: 0 occurrences", flush=True)
	res["controls_start"] = controls("start")
	# Correctness: every harness binary against base-p0, 36 origin-qualified fixtures, E0, strict after normalization.
	corr = {}
	for s in HARNESS[1:]:
		for origin, d in (("corpus", CORPUS), ("fixtures", FIX)):
			for fx in sorted(d.glob("*.rn")):
				mode = "async" if fx.stem == "async" else "run"
				extra = ["2000000"] if fx.stem == "budget" else []
				a = subprocess.run([str(BIN / "base-p0"), mode, str(fx), *extra], capture_output=True, text=True, timeout=300, env=E0)
				b = subprocess.run([str(BIN / s), mode, str(fx), *extra], capture_output=True, text=True, timeout=300, env=E0)
				ra, rb = (a.returncode, a.stdout, a.stderr), (b.returncode, b.stdout, b.stderr)
				key = f"{s}:{origin}/{fx.stem}"
				corr[key] = {"same": norm(ra) == norm(rb), "base": ra, "subject": rb}
				assert corr[key]["same"], (key, ra[:2], rb[:2])
	assert len(corr) == 11 * 36
	(out / "correctness.json").write_text(json.dumps(corr, indent=1) + "\n")
	for s in RNX:
		r = subprocess.run([str(BIN / s), "eval", "42"], capture_output=True, text=True, timeout=60, env=E0)
		assert r.returncode == 0 and r.stdout == "42\n", (s, r.stdout, r.stderr[-200:])
	res["correctness"] = {"checked": len(corr), "all_identical": True, "rnx_eval_42": len(RNX)}
	print("correctness:", len(corr), "identical", flush=True)
	# PMU (i), (ii), rnx eval 42.
	pmu = {}
	for p in PROFILES[1:]:
		pmu[f"i-base-p0-vs-base-{p}"] = compare(f"i-base-p0-vs-base-{p}", "base-p0", f"base-{p}", WORKLOADS, out)
	for p in PROFILES:
		for s in ("s71", "s72"):
			pmu[f"ii-{p}-base-vs-{s}"] = compare(f"ii-{p}-base-vs-{s}", f"base-{p}", f"{s}-{p}", WORKLOADS, out)
	for p in PROFILES[1:]:
		pmu[f"eval-rnx-p0-vs-rnx-{p}"] = compare(f"eval-rnx-p0-vs-rnx-{p}", "rnx-p0", f"rnx-{p}", EVAL, out)
	res["pmu"] = pmu
	print("pmu done", flush=True)
	# Calibration of the resident driver against hyperfine --output=pipe (0.15 ms), first of the wall-clock work.
	cal = {}
	for name, subject, tail in (("true", None, []), ("floor", "base-p0", ["floor"])):
		if subject is None:
			argv = ["/bin/true"]
			nat = statistics.median(calibrate_true(argv, tmp))
		else:
			resident(subject, tail, "", 5, tmp, "cal-warm")
			nat = statistics.median(resident(subject, tail, "", 50, tmp, "cal"))
			argv = [str(STAGE["harness"]), *tail]
		hf = hf_median(argv)
		cal[name] = {"native_ms": nat, "hyperfine_pipe_ms": hf, "difference_ms": nat - hf}
		assert abs(nat - hf) <= 0.15, ("STOP: calibration", cal)
	res["calibration"] = cal
	print("calibration:", {k: round(v["difference_ms"], 3) for k, v in cal.items()}, flush=True)
	walls = {}
	for p in PROFILES[1:]:
		walls[f"i-base-p0-vs-base-{p}"] = wall(f"i-base-p0-vs-base-{p}", "base-p0", f"base-{p}", WORKLOADS, tmp, 0)
	for p in PROFILES[1:]:
		walls[f"eval-rnx-p0-vs-rnx-{p}"] = wall(f"eval-rnx-p0-vs-rnx-{p}", "rnx-p0", f"rnx-{p}", EVAL, tmp, 5)
	res["wall_ms"] = walls
	print("wall done", flush=True)
	res["controls_end"] = controls("end")
	res.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	shutil.rmtree(tmp)
	(out / "measure.json").write_text(json.dumps(res, indent=1) + "\n")
	hits = scan(out, [sentinel])
	assert not hits, ("STOP: sentinel found in official output", hits)
	(out / "sentinel-scan.json").write_text(json.dumps({"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": 0}) + "\n")
	for name, rows in pmu.items():
		print(name, " ".join(f"{k}:{v['instructions']['change'] * 100:+.3f}%" for k, v in rows.items()), flush=True)
	for name, rows in walls.items():
		print("wall", name, " ".join(f"{k}:{v['change'] * 100:+.2f}%" for k, v in rows.items()), flush=True)


def calibrate_true(argv, tmp):
	"""The resident driver on /bin/true (unstaged, a system binary): 5 warmups then 50 samples."""
	def block(n):
		lines = [str(n)]
		for _ in range(n):
			lines.append(str(len(argv)))
			lines += [a.encode().hex() for a in argv]
		plan = tmp / "true.plan"
		plan.write_text("\n".join(lines) + "\n")
		pinned()
		r = subprocess.run([str(CLOCK), str(plan)], capture_output=True, text=True, timeout=300, env=E0)
		assert r.returncode == 0
		rec = r.stdout.splitlines()
		assert len(rec) == 6 * n
		return [int(rec[6 * i + 2]) / 1e6 for i in range(n) if rec[6 * i] == f"EXEC {i}" and rec[6 * i + 3] == "0"]
	block(5)
	got = block(50)
	assert len(got) == 50
	return got


if __name__ == "__main__":
	main(sys.argv[1])
