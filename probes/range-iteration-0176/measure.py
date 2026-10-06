"""rnx 0176 measurement (plan rnx 084d2b4 section 5; 0175 tooling 640a792d, gates unchanged, frozen before candidate timing). Run under the shared lock:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 measure.py [--rehearsal] OUT_DIR

Order: manifest check (refuses before anything else on any mismatch); sentinel rehearsal; affinity controls;
(1) correctness and allocation controls; (2) historical reproduction; (3) PMU, 5 true ABBA repetitions per workload;
(4) resident-driver calibration then wall clock, 3 rounds ABBA/BAAB/ABBA in blocks of 5; (5) Lua references (not gates);
end controls; the frozen decision; the final sentinel scan. --rehearsal stops after (1): no timing at all.

Retention: every command's argv, status, raw stdout/stderr, deadline/interrupt outcome, affinity and subject hash is
appended to a JSONL sink BEFORE it is parsed or asserted, failures included; summaries are derived afterwards. Each
phase is recorded in phases.jsonl when it starts, so a stopped run shows exactly which phases began.
Subjects run from one staged path with environment E0 exactly, each as its own process group with a deadline
(common.run_bounded); the controller is pinned to CPU 4 and children inherit it (per-sample fields are controller
affinity; 10 representative grep controls observe a child).
"""
import io, json, lzma, math, os, pathlib, re, shutil, signal, statistics, subprocess, sys, tarfile, time
from common import HERE, E0, SOURCES, PRODUCTION_PARENT, sha, run_bounded, kill_group, settle, LineReader, new_sentinel, count, scan, Ledger
import freeze

sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = HERE / "bin"
CLOCK = HERE / "clock/plan_clock"
STAGE = HERE / "stage/primary"
MANIFEST = HERE / "subjects.json"
CORPUS, FIX, RANGE, LUA = HERE / "corpus", HERE / "fixtures", HERE / "range", HERE / "lua"
CONTROL = ["perf", "stat", "--", "/usr/bin/grep", "Cpus_allowed_list", "/proc/self/status"]

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
EXPECT_BY_LABEL = {label: expect for label, _, expect in WORKLOADS}
EXPECT_BY_LABEL["run-manual_next"] = EXPECT["manual_next"]
WIN_INSTR = ["run-numeric", "run-range_signed", "run-range_negative"]
WIN_ALLOC = "run-numeric"
RANGE_ALLOC = {"run-numeric", "run-range_signed", "run-range_negative", "run-strings"}  # strings also iterates ranges
NO_STD_CONTEXT = {"floor", "empty-context"}  # Context::new() or nothing: no ops module, no tagged registration
# Budget variants of the numeric loop, measured separately (plan section 3.6); exact outputs compared, counts reported.
BUDGETS = [("zero", ["0"]), ("default", []), ("unlimited", [str(2**64 - 1)]), ("tight", ["1000"])]
NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]
HASHES = {}
REHEARSAL = False


class Stop(Exception):
	pass


class Sink:
	"""Append-only JSONL, flushed per row: every raw result lands here before it is interpreted."""

	def __init__(self, path):
		self.f = pathlib.Path(path).open("a")

	def write(self, row):
		self.f.write(json.dumps(row) + "\n")
		self.f.flush()


def persist(out, name, obj):
	(out / name).write_text(json.dumps(obj, indent=1) + "\n")


def phase(out, name):
	with (out / "phases.jsonl").open("a") as f:
		f.write(json.dumps({"phase": name, "started": time.time()}) + "\n")


def pinned():
	got = sorted(os.sched_getaffinity(0))
	if got != [4]:
		raise Stop(("controller affinity", got))
	return got


def norm(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


def sample(argv, timeout, sink, meta, scratch=None):
	"""Run one bounded command and retain its raw record (also on interrupt) before anyone looks at it."""
	aff = sorted(os.sched_getaffinity(0))
	try:
		r = run_bounded(argv, timeout, E0, scratch=scratch)
	except BaseException as error:
		sink.write({**meta, **getattr(error, "partial", {"argv": argv}), "controller_affinity": aff, "env": E0,
			"exception": repr(error)})
		raise
	row = {**meta, **r.record(), "controller_affinity": aff, "env": E0, "cwd": os.getcwd()}
	return row


def lifecycle(row):
	"""Post-retention cleanup gate for every result: no deadline or interrupt, leader reaped, no live group member left."""
	if row.get("timed_out") or row.get("interrupted"):
		raise Stop(("deadline or interrupt", row.get("argv"), row.get("timed_out"), row.get("interrupted")))
	if row.get("reaped") is not True or row.get("group_survivors"):
		raise Stop(("cleanup", row.get("argv"), row.get("reaped"), row.get("group_survivors")))


def check_status(row, expect):
	lifecycle(row)
	if row["timed_out"] or row["interrupted"]:
		raise Stop(("deadline or interrupt", row["argv"], row["timed_out"], row["interrupted"]))
	if row["status"] != 0 or row["stdout"] != expect:
		raise Stop(("status/output", row["argv"], row["status"], row["stdout"][:80], row["stderr"][-300:]))


def parse(text):
	got = {}
	for line in text.splitlines():
		if line.startswith("{"):
			try:
				row = json.loads(line)
			except json.JSONDecodeError as error:
				raise Stop(("malformed counter line", line[:120], repr(error)))
			name = next((n for n in ("instructions", "cycles") if row.get("event") in (n + ":u", f"cpu_core/{n}/u")), None)
			if name:
				try:
					running, val = float(row["pcnt-running"]), float(row["counter-value"])
				except (KeyError, ValueError) as error:
					raise Stop(("malformed counter row", row, repr(error)))
				if running < 99 or not math.isfinite(val) or val <= 0:
					raise Stop(("counter not usable", row))
				got[name] = val
	if set(got) != {"instructions", "cycles"}:
		raise Stop(("counters missing", text[-300:]))
	return got


def stage(subject):
	STAGE.parent.mkdir(exist_ok=True)
	tmp = STAGE.parent / f".staging-{subject}"
	shutil.copy2(BIN / f"{subject}-primary", tmp)
	os.replace(tmp, STAGE)
	if sha(STAGE) != HASHES[subject]:
		raise Stop((subject, "staged hash"))
	return STAGE


def controls(label, sink):
	rows = []
	for i in range(5):
		pinned()
		row = sample(CONTROL, 30, sink, {"kind": "affinity-control", "label": label, "index": i})
		sink.write(row)
		rows.append(row)
		lifecycle(row)
		if row["status"] != 0 or row["stdout"] != "Cpus_allowed_list:\t4\n":
			raise Stop(("affinity control", label, i, row["status"], row["stdout"]))
	return rows


def perf(argv, expect, sink, meta, perf_argv=None):
	"""One whole-process perf sample; the raw row (with the staged hash after the run) is retained first."""
	pinned()
	full = (perf_argv or ["perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--"]) + argv
	row = sample(full, 300, sink, meta)
	if meta.get("subject"):
		row["hash_after"] = sha(STAGE)
	sink.write(row)
	check_status(row, expect)
	if meta.get("subject") and row["hash_after"] != HASHES[meta["subject"]]:
		raise Stop(("stage changed during sample", meta))
	return {**row, **parse(row["stderr"])}


def ack_ok(line):
	"""perf --control acknowledges with "ack\\n" plus NUL padding; the NUL of one acknowledgement can lead the next
	newline-split line. Accept NULs only at the line's boundaries; an embedded NUL ("a\\0ck") is malformed."""
	return line.strip("\0") == "ack\n"


def fifo(mode, work, tmp, sink, meta, exe=None):
	"""0169's counter method (FIFO-bracketed go/DONE window on the base counter build), for reproduction only.
	Every protocol read is a bounded line read; the raw row (protocol bytes, counter file, statuses) is written in
	`finally`, before the counter output is parsed."""
	ctl, ack, raw = tmp / "c.ctl", tmp / "c.ack", tmp / f"c-{meta['work']}-{meta['index']}.jsonl"
	for p in (ctl, ack):
		if p.exists():
			p.unlink()
	os.mkfifo(ctl)
	os.mkfifo(ack)
	cf, af = os.open(ctl, os.O_RDWR | os.O_NONBLOCK), os.open(ack, os.O_RDWR | os.O_NONBLOCK)
	argv = [str(exe or BIN / "base-counter"), mode, *([str(path_for(work))] if work else [])]
	row = {**meta, "argv": argv, "env": E0, "controller_affinity": sorted(os.sched_getaffinity(0)), "acks": []}
	child = counter = reader = acks = None
	try:
		pinned()
		with (tmp / "child.out").open("wb") as child_out:
			child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=child_out, stderr=subprocess.PIPE, env=E0, start_new_session=True)
		reader = LineReader(child.stderr.fileno())
		if reader.line(time.monotonic() + 10) != "READY\n":
			raise Stop(("counter child: expected READY", bytes(reader.seen)))
		row["child_affinity"] = sorted(os.sched_getaffinity(child.pid))
		if row["child_affinity"] != [4]:
			raise Stop(("counter target affinity", row["child_affinity"]))
		with (tmp / "perf.out").open("wb") as perf_out:
			counter = subprocess.Popen(["taskset", "-c", "0", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u",
				"-p", str(child.pid), "-D", "-1", "--control", f"fifo:{ctl},{ack}", "-o", str(raw)], stdout=perf_out, stderr=subprocess.STDOUT,
				env=E0, start_new_session=True)
		acks = LineReader(af)

		def control(m):
			os.write(cf, (m + "\n").encode())
			got = acks.line(time.monotonic() + 10)
			row["acks"].append({"command": m, "line": got})  # retained before it is interpreted
			if not ack_ok(got):
				raise Stop(("perf control", m, got))
		control("enable")
		child.stdin.write(b"go\n")
		child.stdin.flush()
		deadline = time.monotonic() + 120
		while reader.line(deadline) != "DONE\n":
			pass
		control("disable")
		child.stdin.write(b"stop\n")
		child.stdin.flush()
		row["child_status"] = child.wait(timeout=10)
		counter.send_signal(signal.SIGINT)
		row["counter_status"] = counter.wait(timeout=10)
		if row["child_status"] != 0:
			raise Stop(("counter child status", row["child_status"]))
	except BaseException as error:
		row["exception"] = repr(error)
		raise
	finally:
		for name, p in (("child", child), ("counter", counter)):
			if p is not None:
				kill_group(p.pid)
				try:
					p.wait(timeout=10)
					row[f"{name}_reaped"] = True
				except subprocess.TimeoutExpired:
					row[f"{name}_reaped"] = False
				row[f"{name}_survivors"] = settle(p.pid)
		row["protocol_bytes"] = bytes(reader.seen).decode(errors="replace") if reader else ""
		row["ack_bytes"] = bytes(acks.seen).decode(errors="replace") if acks else ""  # every ack byte, pending included
		row["counter_raw"] = raw.read_text() if raw.exists() else None
		row["perf_output"] = (tmp / "perf.out").read_text(errors="replace") if (tmp / "perf.out").exists() else None
		sink.write(row)
		os.close(cf)
		os.close(af)
		ctl.unlink()
		ack.unlink()
	fifo_gate(row)
	return parse(row["counter_raw"] or "")["instructions"], row


def fifo_gate(row):
	"""Post-retention FIFO gate: child exited 0, perf stopped by our SIGINT (status -SIGINT), both groups reaped with
	no live survivor."""
	for name in ("child", "counter"):
		if row.get(f"{name}_reaped") is not True or row.get(f"{name}_survivors"):
			raise Stop(("fifo cleanup", name, row.get(f"{name}_reaped"), row.get(f"{name}_survivors")))
	if row.get("child_status") != 0 or row.get("counter_status") != -signal.SIGINT:
		raise Stop(("fifo statuses", row.get("child_status"), row.get("counter_status")))


def read_0169():
	data = tarfile.open(R0169_ARCHIVE).extractfile(R0169_MEMBER).read()
	if sha_bytes(data) != R0169_SHA256:
		raise Stop("0169 reference hash")
	sums = (REPO / "results/rune-runtime-0169-SHA256SUMS").read_text()
	if f"{R0169_SHA256}  {R0169_MEMBER}" not in sums:
		raise Stop("0169 reference not in SHA256SUMS")
	ref = {}
	for r in json.loads(data):
		if r["base"] == "new":
			ref.setdefault((r["mode"], r["work"]), []).append(r["counts"]["instructions"])
	for key in REPRO_0169:
		if not (len(ref.get(key, [])) >= 3 and all(isinstance(v, (int, float)) and v > 0 for v in ref[key])):
			raise Stop(("0169 reference rows", key))
	return ref


def read_0171():
	data = R0171.read_bytes()
	if sha_bytes(data) != R0171_SHA256:
		raise Stop("0171 reference hash")
	pmu = json.loads(data)["pmu"]
	for w in REPRO_0171:
		v = pmu[f"base-{w}"]["instructions"]
		if not (len(v) == 5 and all(isinstance(x, (int, float)) and x > 0 for x in v)):
			raise Stop(("0171 reference rows", w))
	return pmu


def sha_bytes(data):
	return __import__("hashlib").sha256(data).hexdigest()


def compare(workloads, sink):
	"""5 true ABBA repetitions (base cand cand base) per workload; summaries derived from the retained rows."""
	samples = []
	for rep in range(5):
		for label, tail, expect in workloads:
			for subject in ("base", "cand", "cand", "base"):
				exe = stage(subject)
				samples.append(perf([str(exe), *tail], expect, sink,
					{"kind": "pmu", "rep": rep, "workload": label, "subject": subject, "hash": HASHES[subject]}))
	rows = {}
	for label, _, _ in workloads:
		row = {}
		for n in ("instructions", "cycles"):
			l = [s[n] for s in samples if s["workload"] == label and s["subject"] == "base"]
			r = [s[n] for s in samples if s["workload"] == label and s["subject"] == "cand"]
			if len(l) != 10 or len(r) != 10:
				raise Stop(("sample count", label, len(l), len(r)))
			row[n] = {"base": l, "cand": r, "base_median": statistics.median(l), "cand_median": statistics.median(r),
				"change": statistics.median(r) / statistics.median(l) - 1}
		rows[label] = row
	return rows


def resident(argv, expect, n, tmp, sink, meta, subject=None, clock=CLOCK):
	"""One resident-driver process running n samples of one command. Its plan, raw output (every target's hex
	stdout/stderr), status and the staged hash after the block are retained before the receipts are checked."""
	if subject is not None:
		exe = stage(subject)
		argv = [str(exe), *argv]
	lines = [str(n)]
	for _ in range(n):
		lines.append(str(len(argv)))
		lines += [a.encode().hex() for a in argv]
	plan_text = "\n".join(lines) + "\n"
	plan = tmp / "block.plan"
	plan.write_text(plan_text)
	pinned()
	row = sample([str(clock), str(plan)], 1800, sink, {**meta, "kind": meta.get("kind", "resident"), "subject": subject,
		"hash": HASHES.get(subject), "plan": plan_text, "target_argv": argv})
	if subject is not None:
		row["hash_after"] = sha(STAGE)
	sink.write(row)
	lifecycle(row)
	if row["status"] != 0:
		raise Stop(("resident driver", meta, row["status"], row["stderr"][-300:]))
	if subject is not None and row["hash_after"] != HASHES[subject]:
		raise Stop((meta, "stage changed during block"))
	rec = row["stdout"].splitlines()
	if len(rec) != 6 * n:
		raise Stop(("incomplete receipt", meta, len(rec), 6 * n))
	got = []
	for i in range(n):
		block = rec[6 * i: 6 * i + 6]
		if block[0] != f"EXEC {i}" or block[1] != " ".join(a.encode().hex() for a in argv):
			raise Stop(("receipt order/argv", meta, i))
		ns, status = int(block[2]), int(block[3])
		if status != 0 or bytes.fromhex(block[4]).decode() != expect or ns <= 0:
			raise Stop(("target status/output", meta, i, status))
		got.append(ns / 1e6)
	return got


def wall(workloads, tmp, sink):
	"""3 rounds: ABBA (rounds 1 and 3) / BAAB (round 2), blocks of 5, 30 samples per side per workload. No warm-up
	block (pre-timing method amendment, accepted in review; it applies equally to both sides)."""
	rows = {}
	for label, tail, expect in workloads:
		got = {"base": [], "cand": []}
		for rnd in range(3):
			order = ("base", "cand", "cand", "base") if rnd % 2 == 0 else ("cand", "base", "base", "cand")
			for block, subject in enumerate(order):
				got[subject] += resident(tail, expect, 5, tmp, sink, {"kind": "wall", "workload": label, "round": rnd, "block": block}, subject)
		q = statistics.quantiles(got["base"], n=10)
		rows[label] = {"base": got["base"], "cand": got["cand"], "base_median_ms": statistics.median(got["base"]),
			"cand_median_ms": statistics.median(got["cand"]), "base_p10_p90_ms": q[-1] - q[0],
			"change": statistics.median(got["cand"]) / statistics.median(got["base"]) - 1}
	return rows


def hf_median(argv, sink, meta):
	pinned()
	row = sample(["hyperfine", "-N", "--output=pipe", "-w", "5", "-r", "50", "--export-json", "/dev/stdout", " ".join(argv)], 300, sink, meta)
	sink.write(row)
	lifecycle(row)
	if row["status"] != 0:
		raise Stop(("hyperfine", row["status"], row["stderr"][-300:]))
	return json.loads(row["stdout"][row["stdout"].index("{"):])["results"][0]["median"] * 1000


def alloc_row_gate(label, row, expect):
	"""An ordinary counting run counts only if both sides completed cleanly with the exact expected output."""
	for s in ("base", "cand"):
		lifecycle(row[s])
		if row[s]["status"] != 0 or row[s]["stdout"] != expect or "calls" not in row[s]:
			raise Stop(("allocation run", label, s, row[s]["status"], row[s]["stdout"][:80]))


BUDGET_STATUS = {"numeric-budget-zero": 1, "numeric-budget-default": 0, "numeric-budget-unlimited": 0, "numeric-budget-tight": 1}


def budget_row_gate(label, row):
	"""Budget variants: each side ends with the expected completion/halt status and its ALLOC line, cleanly; the two
	sides agree on status, stdout and normalized stderr (minus the ALLOC line). Matching crashes are not credited."""
	strip = lambda x: (x["status"], x["stdout"], norm((0, "", "\n".join(l for l in x["stderr"].splitlines() if not l.startswith("ALLOC "))))[2])
	for s in ("base", "cand"):
		lifecycle(row[s])
		if row[s]["status"] != BUDGET_STATUS[label] or "calls" not in row[s]:
			raise Stop(("budget status", label, s, row[s]["status"], BUDGET_STATUS[label]))
	if label in ("numeric-budget-default", "numeric-budget-unlimited"):
		for s in ("base", "cand"):
			if row[s]["stdout"] != EXPECT["numeric"]:
				raise Stop(("budget output", label, s, row[s]["stdout"][:80]))
	if strip(row["base"]) != strip(row["cand"]):
		raise Stop(("budget outcomes differ", label))


def alloc_gate(alloc):
	"""Accepted qualification: exactly one temporary allocation for the tagged registration wherever the std modules
	are installed (context delta exactly +1), none without them (floor/empty-context exactly 0); no other workload may
	rise above that; the manual-next control loses nothing (delta equals context's)."""
	problems = []
	if alloc["context"]["calls_delta"] != 1:
		problems.append(("context delta is not exactly +1", alloc["context"]["calls_delta"]))
	for k in NO_STD_CONTEXT:
		if alloc[k]["calls_delta"] != 0:
			problems.append((f"{k} delta is not exactly 0", alloc[k]["calls_delta"]))
	for k, v in alloc.items():
		if k not in RANGE_ALLOC and k not in NO_STD_CONTEXT and v["calls_delta"] > 1:
			problems.append((f"{k} allocation calls rose", v["calls_delta"]))
	if alloc["run-manual_next"]["calls_delta"] != alloc["context"]["calls_delta"]:
		problems.append(("manual-next allocations changed", alloc["run-manual_next"]["calls_delta"]))
	if problems:
		raise Stop(("allocation", problems))


def verify_manifest(path):
	"""Every frozen identity must still hold; returns the list of mismatches (empty when the run may proceed)."""
	m = json.loads(pathlib.Path(path).read_text())
	bad = []
	if m.get("sources") != SOURCES or m.get("production_parent") != PRODUCTION_PARENT:
		bad.append(("sources differ from the frozen constants",))
	for name, h in m["binaries"].items():
		p = BIN / name
		if not p.exists() or sha(p) != h:
			bad.append(("binary", name))
	if sha(CLOCK) != m["clock"]["sha256"] or sha(HERE / "plan_clock.rs") != m["clock"]["source_sha256"]:
		bad.append(("resident driver",))
	receipt = REPO / m["build_receipt"]["path"]
	if not receipt.exists() or sha(receipt) != m["build_receipt"]["sha256"]:
		bad.append(("build receipt",))
	else:
		b = json.loads(receipt.read_text())
		if b["sources"] != m["sources"] or {k: v["sha256"] for k, v in b["builds"].items()} != m["binaries"]:
			bad.append(("build receipt content",))
		for primary in ("base-primary", "cand-primary"):
			if b["builds"][primary].get("rune_features") != m["rune_features"]:
				bad.append(("feature set", primary))
		if "tracing" in m["rune_features"]:
			bad.append(("tracing in feature set",))
	for subject, r in m["inventory"]["receipts"].items():
		p = REPO / r["log"]
		if not p.exists() or sha(p) != r["log_sha256"] or not all(r["tests_passed"].values()):
			bad.append(("inventory receipt", subject))
	now = freeze.inputs_digest()
	if now != m["inputs"]:
		bad.append(("inputs", sorted(k for k in set(now) | set(m["inputs"]) if now.get(k) != m["inputs"].get(k))))
	for k, v in m["lua"].items():
		if sha(v["path"]) != v["sha256"]:
			bad.append(("lua", k))
	return m, bad


def rehearse(out, sentinel):
	"""Sentinel rehearsal: results, a failing command (exception text and argv), the ledger, an archive, a command log."""
	assert count(b"x" + sentinel.encode(), "", [sentinel]) == 1, "scanner positive control (plain)"
	packed = lzma.compress(b"x" + sentinel.encode())
	assert count(packed, ".xz", [sentinel]) == count(packed, "", [sentinel]) + 1, "scanner positive control (.xz)"
	r = out / "rehearsal"
	r.mkdir()
	ledger = Ledger(r / "commands.jsonl")
	sink = Sink(r / "raw.jsonl")
	s = perf([str(BIN / "base-primary"), "floor"], "", sink, {"kind": "rehearsal"})
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
	persist(r, "sentinel-scan.json", {"files_scanned": sum(1 for p in r.rglob("*") if p.is_file()), "occurrences": sum(hits.values())})
	if hits:
		raise Stop(("sentinel found in rehearsal output", hits))
	return {"files": sorted(str(p.relative_to(out)) for p in r.rglob("*") if p.is_file()), "occurrences": 0}


def decide(pmu, walls, alloc):
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


def main(out, manifest=MANIFEST):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	# 0. Bind to the reviewed build before anything else; a mismatch refuses with no phase begun.
	m, bad = verify_manifest(manifest)
	if bad:
		persist(out, "refused.json", {"manifest": str(manifest), "mismatches": bad})
		raise Stop(("manifest mismatch: refusing before any phase", bad))
	HASHES.update(base=m["binaries"]["base-primary"], cand=m["binaries"]["cand-primary"])
	tmp = out / "tmp"
	tmp.mkdir()
	assert os.stat(tmp).st_dev == os.stat(out).st_dev
	sentinel = new_sentinel()
	os.sched_setaffinity(0, {4})
	pinned()
	ref69, r71 = read_0169(), read_0171()
	res = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0], "env": E0, "manifest": m,
		"manifest_sha256": sha(manifest), "rehearsal_mode": REHEARSAL}
	persist(out, "partial.json", res)
	sink = Sink(out / "raw.jsonl")
	phase(out, "rehearsal")
	res["rehearsal"] = rehearse(out, sentinel)
	print("rehearsal: 0 occurrences", flush=True)
	phase(out, "controls-start")
	res["controls_start"] = controls("start", sink)
	persist(out, "partial.json", res)
	# 1. Correctness: 36 origin-qualified fixtures base vs candidate; range fixtures against the oracle on both.
	phase(out, "correctness")
	corr = {}
	for origin, d in (("corpus", CORPUS), ("fixtures", FIX), ("range", RANGE)):
		for fx in sorted(d.glob("*.rn")):
			mode = "async" if fx.stem == "async" else "run"
			extra = ["2000000"] if fx.stem == "budget" else []
			key = f"{origin}/{fx.stem}"
			rows = {}
			for s in ("base", "cand"):
				rows[s] = sample([str(BIN / f"{s}-primary"), mode, str(fx), *extra], 300, sink, {"kind": "correctness", "key": key, "subject": s})
				sink.write(rows[s])
				lifecycle(rows[s])
			ra, rb = ((rows[s]["status"], rows[s]["stdout"], rows[s]["stderr"]) for s in ("base", "cand"))
			corr[key] = {"same": norm(ra) == norm(rb) and not rows["base"]["timed_out"] and not rows["cand"]["timed_out"],
				"raw_identical": ra == rb, "base": list(ra), "cand": list(rb)}
			if origin != "corpus":
				corr[key]["oracle"] = ra == (0, EXPECT[fx.stem], "") and rb == (0, EXPECT[fx.stem], "")
	persist(out, "correctness.json", corr)
	bad = [k for k, v in corr.items() if not v["same"] or v.get("oracle") is False]
	if len(corr) != 40 or bad:
		raise Stop(("correctness", len(corr), bad))
	res["correctness"] = {"checked": len(corr), "all_identical": True}
	print("correctness:", len(corr), "identical", flush=True)
	# Allocation controls: separate counting builds, every workload plus manual-next, then the numeric loop's budget
	# variants (zero / default / unlimited / tight halt), exact outputs.
	phase(out, "allocation")
	alloc, budget = {}, {}
	jobs = [(label, tail, expect, alloc) for label, tail, expect in WORKLOADS]
	jobs.append(("run-manual_next", ["run", str(path_for("manual_next"))], EXPECT["manual_next"], alloc))
	jobs += [(f"numeric-budget-{name}", ["run", str(path_for("numeric")), *arg], None, budget) for name, arg in BUDGETS]
	for label, tail, expect, table in jobs:
		row = {}
		for s in ("base", "cand"):
			r = sample([str(BIN / f"{s}-allocation"), *tail], 300, sink, {"kind": "allocation", "label": label, "subject": s})
			sink.write(r)
			alloc_line = next((l for l in r["stderr"].splitlines() if l.startswith("ALLOC ")), "")
			row[s] = {"status": r["status"], "stdout": r["stdout"], "stderr": r["stderr"], "timed_out": r["timed_out"],
				"interrupted": r["interrupted"], "reaped": r["reaped"], "group_survivors": r["group_survivors"], "argv": r["argv"]}
			if alloc_line:
				calls, nbytes, live, peak = json.loads(alloc_line[6:])
				row[s].update(calls=calls, bytes=nbytes, live=live, peak=peak)
		table[label] = row
		if "calls" in row["base"] and "calls" in row["cand"]:
			row["calls_delta"] = row["cand"]["calls"] - row["base"]["calls"]
			row["calls_change"] = row["cand"]["calls"] / row["base"]["calls"] - 1
	persist(out, "allocation.json", alloc)
	persist(out, "allocation-budgets.json", budget)
	for label, row in alloc.items():
		alloc_row_gate(label, row, EXPECT_BY_LABEL[label])
	for label, row in budget.items():
		budget_row_gate(label, row)
	alloc_gate(alloc)
	res["allocation"] = {"context_delta": alloc["context"]["calls_delta"], "numeric_calls": [alloc[WIN_ALLOC]["base"]["calls"],
		alloc[WIN_ALLOC]["cand"]["calls"]], "budget_variants": {k: [v["base"]["calls"], v["cand"]["calls"], v["base"]["status"]]
		for k, v in budget.items()}}
	persist(out, "partial.json", res)
	print("allocation: context delta", res["allocation"]["context_delta"], "numeric calls", res["allocation"]["numeric_calls"],
		"budgets", res["allocation"]["budget_variants"], flush=True)
	if REHEARSAL:
		res.update(ended=time.time())
		shutil.rmtree(tmp)
		(out / "partial.json").unlink()
		persist(out, "rehearsal-measure.json", res)
		hits = scan(out, [sentinel])
		persist(out, "sentinel-scan.json", {"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": sum(hits.values())})
		if hits:
			raise Stop(("sentinel found in rehearsal-mode output", hits))
		print("rehearsal mode: stopped before any timed phase; sentinel 0 occurrences", flush=True)
		return
	# 2. Historical reproduction on the base (0172's reviewed method; tiny FIFO windows descriptive).
	phase(out, "reproduction")
	repro = {}
	for mode, work in REPRO_0169:
		vals = []
		for i in range(3):
			v, _ = fifo(mode, work, tmp, sink, {"kind": "reproduction-fifo", "reference": "0169", "mode": mode, "work": work, "index": i})
			vals.append(v)
		got, want = statistics.median(vals), statistics.median(ref69[(mode, work)])
		repro[f"0169 fifo {mode} {work}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want,
			"ratio": got / want, "gated": (mode, work) not in DESCRIPTIVE}
	for w in REPRO_0171:
		vals = []
		for i in range(3):
			exe = stage("base")
			vals.append(perf([str(exe), "run", str(path_for(w))], EXPECT[w], sink,
				{"kind": "reproduction-pmu", "reference": "0171", "work": w, "index": i, "subject": "base", "hash": HASHES["base"]})["instructions"])
		got, want = statistics.median(vals), statistics.median(r71[f"base-{w}"]["instructions"])
		repro[f"0171 whole-process run {w}"] = {"samples": vals, "median": got, "reference": want, "difference": got - want,
			"ratio": got / want, "gated": True}
	persist(out, "base-reproduction.json", repro)
	bad = {k: v["ratio"] for k, v in repro.items() if v["gated"] and abs(v["ratio"] - 1) > 0.02}
	if bad:
		raise Stop(("base reproduction", bad))
	print("reproduction: gated rows within 2%; descriptive", {k: round(v["difference"]) for k, v in repro.items() if not v["gated"]}, flush=True)
	# 3. PMU.
	phase(out, "pmu")
	pmu = compare(WORKLOADS, sink)
	persist(out, "pmu.json", pmu)
	print("pmu done", flush=True)
	# 4. Calibration first, then wall.
	phase(out, "calibration")
	cal = {}
	for name, argv, subject in (("true", ["/bin/true"], None), ("floor", ["floor"], "base")):
		resident(argv, "", 5, tmp, sink, {"kind": "calibration-warm", "name": name}, subject)
		nat = statistics.median(resident(argv, "", 50, tmp, sink, {"kind": "calibration", "name": name}, subject))
		hf = hf_median([str(STAGE), "floor"] if subject else argv, sink, {"kind": "calibration-hyperfine", "name": name})
		cal[name] = {"native_ms": nat, "hyperfine_pipe_ms": hf, "difference_ms": nat - hf}
	res["calibration"] = cal
	persist(out, "partial.json", res)
	if not all(abs(v["difference_ms"]) <= 0.15 for v in cal.values()):
		raise Stop(("calibration", cal))
	print("calibration:", {k: round(v["difference_ms"], 3) for k, v in cal.items()}, flush=True)
	phase(out, "wall")
	walls = wall(WORKLOADS, tmp, sink)
	persist(out, "wall.json", walls)
	print("wall done", flush=True)
	# 5. Lua references under the same clock (not gates).
	phase(out, "lua")
	lua = {}
	for binary, info in m["lua"].items():
		for script, expect in (("numeric", EXPECT["numeric"]), ("while", EXPECT["while"])):
			argv = [info["path"], str(LUA / f"{script}.lua")]
			resident(argv, expect, 5, tmp, sink, {"kind": "lua-warm", "binary": binary, "script": script})
			ms = []
			for block in range(6):
				ms += resident(argv, expect, 5, tmp, sink, {"kind": "lua", "binary": binary, "script": script, "block": block})
			lua[f"{binary}-{script}"] = {"ms": ms, "median_ms": statistics.median(ms)}
	res["lua_reference"] = lua
	phase(out, "controls-end")
	res["controls_end"] = controls("end", sink)
	res.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	res["decision"] = decide(pmu, walls, alloc)
	shutil.rmtree(tmp)
	(out / "partial.json").unlink()
	persist(out, "measure.json", res)
	hits = scan(out, [sentinel])
	persist(out, "sentinel-scan.json", {"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": sum(hits.values())})
	if hits:
		raise Stop(("sentinel found in official output", hits))
	d = res["decision"]
	print("DECISION", d["decision"], "regressions", d["regressions"], "disagreements", d["disagreements"], flush=True)
	print("win instr", {k: f"{v * 100:+.2f}%" for k, v in d["win_instr"].items()}, "numeric alloc", f"{d['win_alloc'] * 100:+.2f}%", flush=True)
	for k, v in d["rows"].items():
		print(f"{k}: instr {v['instr_change'] * 100:+.3f}% wall {v['wall_change'] * 100:+.2f}% (band {v['base_wall_p10_p90_ms']:.3f} ms)", flush=True)
	print("lua", {k: round(v["median_ms"], 3) for k, v in lua.items()}, flush=True)


if __name__ == "__main__":
	# --rehearsal: untimed receipts only (manifest, rehearsal, controls, correctness, allocation); no FIFO, PMU or wall.
	REHEARSAL = sys.argv[1:2] == ["--rehearsal"]
	main(sys.argv[-1])
