"""rnx 0180 paired native-event study on the two RETAINED 0179 primary binaries (plan rnx ee3a5de section 7).

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 events.py discover OUT_DIR
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 events.py rehearse OUT_DIR
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 events.py official OUT_DIR

discover: host/PMU identity for CPU 4, then exactly two bounded open checks per frozen group on the affinity probe
	(`/usr/bin/grep Cpus_allowed_list /proc/self/status`); writes availability.json. No experiment workload runs and no
	event magnitude selects a group. R failing stops; no optional group eligible closes INCONCLUSIVE at discovery.
rehearse: untimed plumbing only: manifest binding, staging and hashing both primaries (not executed), the sentinel
	rehearsal on the affinity probe, the frozen availability manifest. No Q1/Q2 workload runs.
official: ONE run. Groups in frozen order (R, then eligible A-E), five repetitions, the seven frozen windows in order,
	each as base/candidate/candidate/base: ten samples per side per workload per group. Every raw row is retained before
	it is parsed. After each group its instruction/cycle anchors must reproduce 0179 (section 7c); a failure closes
	NONREPRODUCING and stops later groups. No added samples, events or reruns.

Subjects are staged at exactly 0179's stage path and run with 0179's E0 environment and argv, one perf process per
sample, the controller pinned to CPU 4. Nothing here builds, edits or re-decides 0179.
"""
import json, math, os, pathlib, shutil, statistics, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "probes/startup-0179"))
from common import E0, sha, run_bounded, new_sentinel, scan  # noqa: E402  (0179's reviewed process/retention helpers)

# The retained 0179 subjects: binaries, stage path and scripts live in 0179's driver worktree (untracked build outputs).
SUBJECT_ROOT = pathlib.Path("/home/me/work/rnx-bench-w-0179d/probes/startup-0179")
BIN = SUBJECT_ROOT / "bin"
STAGE = SUBJECT_ROOT / "stage/primary"
PRIMARY = {"base": ("p0-base-primary", "af06e8b3b1621b7f763dfb39f967fab1cca0b9b615b145152634463cefbb0c87"),
	"cand": ("p0-cand-primary", "e4a5f207c38a8ae59bc311e3611a6bdd3d542fe82665a8e12b201f61eaf9a787")}
# Pinned 0179 evidence (tracked copies in this repository).
SUBJECTS_JSON = (REPO / "probes/startup-0179/subjects.json", "d3552638c3e0fbc8d9cfe538a3488a35edf0d432454b6c4e9d1359363e1fd8a1")
RAW_0179 = (REPO / "results/startup-0179/official1/p0-cand/raw.jsonl", "d0643c0fc1ca42f6c4e9e5d9748c351da546b0baed3d1226349d6e5fab848b03")
PROBE = ["/usr/bin/grep", "Cpus_allowed_list", "/proc/self/status"]
PROBE_STDOUT = "Cpus_allowed_list:\t4\n"

# The seven frozen windows, in order: (label, argv tail, expected stdout, source-bound operations or None).
# Operation counts are the script-bound counts of static2/arithmetic.json (1M loop iterations or calls; fib(27) = 635,621
# invocations); run-empty has none.
_w = lambda name: str(SUBJECT_ROOT / ("corpus" if name in ("numeric", "fib", "empty") else "range" if name.startswith("range") else "fixtures") / f"{name}.rn")
WORKLOADS = [("run-numeric", ["run", _w("numeric")], "3\n", 1_000_000), ("run-range_signed", ["run", _w("range_signed")], None, 1_000_000),
	("run-range_negative", ["run", _w("range_negative")], None, 1_000_000), ("run-fib", ["run", _w("fib")], "196418\n", 635_621),
	("run-calls", ["run", _w("calls")], None, 1_000_000), ("run-while", ["run", _w("while")], None, 1_000_000),
	("run-empty", ["run", _w("empty")], "", None)]
CYCLE_EXEMPT = {"run-empty"}  # short window: cycles descriptive (section 7c)
CHANGE_EXEMPT = {"run-empty"}  # instruction-change tolerance applies to the six nonempty workloads

ANCHORS = ["cpu_core/instructions,name=instructions/u", "cpu_core/cpu-cycles,name=cycles/u"]
raw = lambda event, umask, name: f"cpu_core/event={event},umask={umask},name={name}/u"
# Frozen groups, in order. hardware = one strong pinned group; software = separate events in the same invocation.
GROUPS = {
	"R": {"hardware": ANCHORS, "software": []},
	"A": {"hardware": ANCHORS + ["cpu_core/ref-cycles,name=ref_cycles/u"], "software": ["context-switches", "cpu-migrations", "task-clock"]},
	"B": {"hardware": ["cpu_core/slots,name=slots/u", "cpu_core/topdown-retiring,name=td_retiring/u", "cpu_core/topdown-bad-spec,name=td_bad_spec/u",
		"cpu_core/topdown-fe-bound,name=td_fe_bound/u", "cpu_core/topdown-be-bound,name=td_be_bound/u"] + ANCHORS, "software": []},
	"C": {"hardware": ANCHORS + [raw("0xc4", "0x00", "br_inst_retired_all"), raw("0xc5", "0x00", "br_misp_retired_all")], "software": []},
	"D": {"hardware": ANCHORS + [raw("0x79", "0x08", "idq_dsb_uops"), raw("0x79", "0x04", "idq_mite_uops"), raw("0x80", "0x04", "icache_data_stalls")],
		"software": []},
	"E": {"hardware": ANCHORS + [raw("0xd1", "0x08", "mem_load_retired_l1_miss"), raw("0x03", "0x82", "ld_blocks_store_forward")], "software": []},
}
REQUIRED = "R"
SOFTWARE_NAMES = {"context-switches": "context_switches", "cpu-migrations": "cpu_migrations", "task-clock": "task_clock"}
TOPDOWN = ["td_retiring", "td_bad_spec", "td_fe_bound", "td_be_bound"]
SAMPLE_DEADLINE, OFFICIAL_DEADLINE, PREP_DEADLINE = 120, 1800, 600
# Tolerance boundaries are inclusive; EPS only absorbs binary floating-point rounding of a value that is on the boundary
# (1.02 - 1 is 0.020000000000000018 in doubles). It is nine orders of magnitude below any tolerance.
EPS = 1e-12


class Stop(Exception):
	"""Infrastructure, safety or measurement-validity failure: the run stops, partial evidence retained."""


class Nonreproducing(Exception):
	"""A completed scientific outcome: a group's anchors did not reproduce 0179 (section 7c)."""


class Sink:
	def __init__(self, path):
		self.f = pathlib.Path(path).open("a")

	def write(self, row):
		self.f.write(json.dumps(row) + "\n")
		self.f.flush()


def names(group):
	"""Frozen counter names of a group, hardware then software."""
	hw = [e.split("name=")[1].split("/")[0] for e in GROUPS[group]["hardware"]]
	return hw, [SOFTWARE_NAMES[e] for e in GROUPS[group]["software"]]


def perf_argv(group):
	"""perf stat for one group: JSON, no scaling, one strong ({...}) pinned (:D) cpu_core user-only hardware group, no
	weak-group fallback and no metric expansion; software events (group A) outside the hardware group."""
	g = GROUPS[group]
	argv = ["perf", "stat", "-j", "--no-scale", "-e", "{" + ",".join(g["hardware"]) + "}:D"]
	for e in g["software"]:
		argv += ["-e", e]
	return argv + ["--"]


def pinned():
	got = sorted(os.sched_getaffinity(0))
	if got != [4]:
		raise Stop(("controller affinity", got))


def lifecycle(row):
	if row.get("timed_out") or row.get("interrupted") or row.get("reaped") is not True or row.get("group_survivors"):
		raise Stop(("process lifecycle", row.get("argv"), row.get("timed_out"), row.get("interrupted"), row.get("reaped"), row.get("group_survivors")))


def parse(text, group):
	"""Counter values of one perf JSON stderr for `group`. Fails closed: every frozen counter exactly once, nothing
	else, hardware rows cpu_core only, finite non-negative values, no scaled/unsupported/not-counted marker, and every
	hardware row at exactly 100% running."""
	hw, sw = names(group)
	got = {}
	for line in text.splitlines():
		if not line.startswith("{"):
			continue
		try:
			row = json.loads(line)
		except json.JSONDecodeError as error:
			raise Stop(("malformed counter line", line[:160], repr(error)))
		if "event" not in row:
			continue
		event = row["event"]
		name = event if event in hw else SOFTWARE_NAMES.get(event.split(":")[0])
		if name is None or name not in hw + sw:
			raise Stop(("unexpected counter", group, event))
		if name in got:
			raise Stop(("duplicate counter", group, name))
		if name in hw and row.get("pmu", "cpu_core") != "cpu_core":
			raise Stop(("counter not on cpu_core", group, name, row.get("pmu")))
		value = row.get("counter-value")
		try:
			number = float(value)
		except (TypeError, ValueError):
			raise Stop(("counter not counted or unsupported", group, name, value))
		if not math.isfinite(number) or number < 0:
			raise Stop(("counter not finite and non-negative", group, name, value))
		if name in hw:
			running = row.get("pcnt-running")
			if not isinstance(running, (int, float)) or running != 100:
				raise Stop(("counter not running 100%", group, name, running))
			if "event-runtime" in row and "event-enabled" in row and row["event-runtime"] != row["event-enabled"]:
				raise Stop(("enabled and running times differ", group, name))
		got[name] = number
	if sorted(got) != sorted(hw + sw):
		raise Stop(("counter set differs from the frozen group", group, sorted(set(hw + sw) - set(got)), sorted(set(got) - set(hw + sw))))
	if got.get("instructions", 1) <= 0 or got.get("cycles", 1) <= 0:
		raise Stop(("anchor is zero", group))
	return got


def metrics(group, c, ops):
	"""Same-sample derived values (raw counts are kept beside them). Undefined ratios are None, never zero."""
	div = lambda a, b: a / b if b else None
	m = {"cycles_per_instruction": c["cycles"] / c["instructions"]}
	if ops:
		m["instructions_per_operation"], m["cycles_per_operation"] = c["instructions"] / ops, c["cycles"] / ops
	if group == "A":
		if c["cpu_migrations"] != 0:
			raise Stop(("cpu migration during a sample", c["cpu_migrations"]))
		m.update(cycles_per_ref_cycle=div(c["cycles"], c["ref_cycles"]), ref_cycles_per_instruction=c["ref_cycles"] / c["instructions"])
	if group == "B":
		if c["slots"] <= 0:
			raise Stop(("slots is zero",))
		fractions = {k: c[k] / c["slots"] for k in TOPDOWN}
		if not all(math.isfinite(v) and 0 <= v <= 1 for v in fractions.values()) or abs(sum(fractions.values()) - 1) > 0.02:
			raise Stop(("topdown fractions out of range or not summing to one", fractions))
		m.update({f"{k}_fraction": v for k, v in fractions.items()})
	if group == "C":
		m.update(branch_miss_rate=div(c["br_misp_retired_all"], c["br_inst_retired_all"]), branches_per_instruction=c["br_inst_retired_all"] / c["instructions"])
		if ops:
			m.update(branch_misses_per_operation=c["br_misp_retired_all"] / ops, branches_per_operation=c["br_inst_retired_all"] / ops)
	if group == "D":
		m.update(dsb_share_of_dsb_plus_mite=div(c["idq_dsb_uops"], c["idq_dsb_uops"] + c["idq_mite_uops"]), icache_stall_cycles_per_cycle=c["icache_data_stalls"] / c["cycles"])
	if group == "E":
		m.update(l1_miss_loads_per_instruction=c["mem_load_retired_l1_miss"] / c["instructions"], store_forward_blocks_per_instruction=c["ld_blocks_store_forward"] / c["instructions"])
		if ops:
			m.update(l1_miss_loads_per_operation=c["mem_load_retired_l1_miss"] / ops, store_forward_blocks_per_operation=c["ld_blocks_store_forward"] / ops)
	return m


def references():
	"""0179's deciding medians per workload and side, rebuilt from the pinned raw rows (not from a summary)."""
	path, want = RAW_0179
	if sha(path) != want:
		raise Stop(("0179 raw rows do not match their pinned hash",))
	rows = {}
	for line in path.read_text().splitlines():
		r = json.loads(line)
		if r.get("kind") == "pmu":
			counters = {}
			for l in r["stderr"].splitlines():
				if l.startswith("{"):
					j = json.loads(l)
					for n in ("instructions", "cycles"):
						if j.get("event") in (n + ":u", f"cpu_core/{n}/u"):
							counters[n] = float(j["counter-value"])
			rows.setdefault((r["workload"], r["subject"]), []).append(counters)
	ref = {}
	for label, *_ in WORKLOADS:
		ref[label] = {}
		for side in ("base", "cand"):
			got = rows.get((label, side), [])
			if len(got) != 10 or any(set(c) != {"instructions", "cycles"} for c in got):
				raise Stop(("0179 reference samples", label, side, len(got)))
			ref[label][side] = {n: statistics.median(c[n] for c in got) for n in ("instructions", "cycles")}
		for n in ("instructions", "cycles"):
			ref[label][f"{n}_change"] = ref[label]["cand"][n] / ref[label]["base"][n] - 1
	return ref


def anchor_check(group, summary, ref):
	"""Section 7c, per collected group: each side's instruction median within 2% of 0179's; for the six nonempty
	workloads the instruction change within 0.5 percentage points, each side's cycle median within 10%, and the cycle
	change within 3 percentage points. Returns the list of failures (empty = reproduced). Boundaries are inclusive."""
	bad = []
	for label, *_ in WORKLOADS:
		s, r = summary[label], ref[label]
		for side in ("base", "cand"):
			ratio = s[side]["instructions"] / r[side]["instructions"]
			if not abs(ratio - 1) <= 0.02 + EPS:
				bad.append((group, label, side, "instructions", ratio))
			if label not in CYCLE_EXEMPT:
				ratio = s[side]["cycles"] / r[side]["cycles"]
				if not abs(ratio - 1) <= 0.10 + EPS:
					bad.append((group, label, side, "cycles", ratio))
		if label not in CHANGE_EXEMPT:
			d = s["instructions_change"] - r["instructions_change"]
			if not abs(d) <= 0.005 + EPS:
				bad.append((group, label, "instructions change", d))
		if label not in CYCLE_EXEMPT:
			d = s["cycles_change"] - r["cycles_change"]
			if not abs(d) <= 0.03 + EPS:
				bad.append((group, label, "cycles change", d))
	return bad


def summarize(group, samples):
	"""Per workload: raw-count and metric medians per side, the five ABBA paired contrasts (each repetition's median
	candidate minus median base), and the frozen descriptive rule: a direction is `resolved` only if all five contrasts
	share one strict sign AND the pooled median difference exceeds the base p10-p90 width of that quantity."""
	out = {}
	for label, _, _, ops in WORKLOADS:
		rows = [s for s in samples if s["workload"] == label]
		by = {side: [s for s in rows if s["subject"] == side] for side in ("base", "cand")}
		if len(by["base"]) != 10 or len(by["cand"]) != 10 or sorted({s["rep"] for s in rows}) != [0, 1, 2, 3, 4]:
			raise Stop(("incomplete ABBA", group, label, len(by["base"]), len(by["cand"])))
		for rep in range(5):
			order = [s["subject"] for s in rows if s["rep"] == rep]
			if order != ["base", "cand", "cand", "base"]:
				raise Stop(("sample order", group, label, rep, order))
		res = {"base": {}, "cand": {}, "quantities": {}}
		keys = list(by["base"][0]["counters"]) + list(by["base"][0]["metrics"])
		value = lambda s, k: s["counters"][k] if k in s["counters"] else s["metrics"][k]
		for k in keys:
			vals = {side: [value(s, k) for s in by[side]] for side in ("base", "cand")}
			if any(v is None for side in vals for v in vals[side]):
				res["quantities"][k] = {"status": "undefined (zero denominator in at least one sample)"}
				continue
			med = {side: statistics.median(vals[side]) for side in vals}
			res["base"][k], res["cand"][k] = med["base"], med["cand"]
			contrasts = [statistics.median(value(s, k) for s in by["cand"] if s["rep"] == rep) -
				statistics.median(value(s, k) for s in by["base"] if s["rep"] == rep) for rep in range(5)]
			q = statistics.quantiles(vals["base"], n=10)
			width, diff = q[-1] - q[0], med["cand"] - med["base"]
			same_sign = all(c > 0 for c in contrasts) or all(c < 0 for c in contrasts)
			res["quantities"][k] = {"base_median": med["base"], "cand_median": med["cand"], "difference": diff,
				"relative": diff / med["base"] if med["base"] else None, "paired_contrasts": contrasts, "base_p10_p90_width": width,
				"resolved": bool(same_sign and abs(diff) > width), "direction": "up" if diff > 0 else "down" if diff < 0 else "none"}
		res["instructions_change"] = res["cand"]["instructions"] / res["base"]["instructions"] - 1
		res["cycles_change"] = res["cand"]["cycles"] / res["base"]["cycles"] - 1
		out[label] = res
	return out


def bind_subjects():
	"""Both retained primaries and the pinned 0179 manifest must still be exactly the frozen ones."""
	path, want = SUBJECTS_JSON
	if sha(path) != want:
		raise Stop(("0179 subjects.json does not match its pinned hash",))
	frozen = json.loads(path.read_text())["binaries"]
	for side, (name, digest) in PRIMARY.items():
		if frozen.get(name) != digest or not (BIN / name).is_file() or sha(BIN / name) != digest:
			raise Stop(("retained primary does not match", side, name))
	for label, tail, _, _ in WORKLOADS:
		if not pathlib.Path(tail[1]).is_file():
			raise Stop(("script missing", label))
	inputs = json.loads(path.read_text())["inputs"]
	for label, tail, _, _ in WORKLOADS:
		rel = str(pathlib.Path(tail[1]).relative_to(SUBJECT_ROOT))
		if inputs.get(rel) != sha(tail[1]):
			raise Stop(("script differs from the frozen 0179 input", label, rel))


def stage(side):
	name, digest = PRIMARY[side]
	STAGE.parent.mkdir(exist_ok=True)
	tmp = STAGE.parent / f".staging-{side}"
	shutil.copy2(BIN / name, tmp)
	os.replace(tmp, STAGE)
	if sha(STAGE) != digest:
		raise Stop((side, "staged hash"))
	return digest


def expected_stdout():
	"""Exact outputs of the frozen windows, from 0179's own retained PMU rows (identical on both sides there)."""
	out = {}
	for line in RAW_0179[0].read_text().splitlines():
		r = json.loads(line)
		if r.get("kind") == "pmu":
			out.setdefault(r["workload"], set()).add((r["status"], r["stdout"]))
	got = {}
	for label, _, expect, _ in WORKLOADS:
		if len(out.get(label, ())) != 1:
			raise Stop(("0179 outputs not unique", label))
		(status, stdout), = out[label]
		if status != 0 or (expect is not None and stdout != expect):
			raise Stop(("0179 output differs from the frozen expectation", label))
		got[label] = stdout
	return got


def run_sample(argv, sink, meta, deadline=SAMPLE_DEADLINE):
	"""One bounded command in E0; its raw record is written before anything inspects it."""
	pinned()
	try:
		r = run_bounded(argv, deadline, E0)
	except BaseException as error:
		sink.write({**meta, **getattr(error, "partial", {"argv": argv}), "env": E0, "exception": repr(error)})
		raise
	row = {**meta, **r.record(), "controller_affinity": sorted(os.sched_getaffinity(0)), "env": E0}
	return row


def read(path):
	try:
		return pathlib.Path(path).read_text().strip()
	except OSError as error:
		return f"<unreadable: {type(error).__name__}>"


def identity():
	"""Filtered host/PMU identity for CPU 4 (no full machine or environment dump)."""
	block = {}
	for chunk in pathlib.Path("/proc/cpuinfo").read_text().split("\n\n"):
		fields = dict((k.strip(), v.strip()) for k, _, v in (l.partition(":") for l in chunk.splitlines()) if k.strip())
		if fields.get("processor") == "4":
			block = {k: fields.get(k) for k in ("vendor_id", "cpu family", "model", "model name", "stepping", "microcode")}
	core = pathlib.Path("/sys/devices/cpu_core")
	ident = {"cpu4": block, "cpu_core_type": read(core / "type"), "cpu_core_cpus": read(core / "cpus"),
		"cpu_atom_cpus": read("/sys/devices/cpu_atom/cpus"), "cpu4_online": read("/sys/devices/system/cpu/cpu4/online"),
		"cpu4_thread_siblings": read("/sys/devices/system/cpu/cpu4/topology/thread_siblings_list"),
		"cpu4_scaling_driver": read("/sys/devices/system/cpu/cpu4/cpufreq/scaling_driver"),
		"cpu4_scaling_governor": read("/sys/devices/system/cpu/cpu4/cpufreq/scaling_governor"),
		"nmi_watchdog": read("/proc/sys/kernel/nmi_watchdog"), "perf_event_paranoid": read("/proc/sys/kernel/perf_event_paranoid"),
		"kernel": read("/proc/sys/kernel/osrelease"),
		"cpu_core_format": {p.name: read(p) for p in sorted((core / "format").glob("*"))},
		"cpu_core_event_aliases": {n: read(core / "events" / n) for n in ("instructions", "cpu-cycles", "ref-cycles", "slots", "topdown-retiring",
			"topdown-bad-spec", "topdown-fe-bound", "topdown-be-bound")}}
	return ident


def expand_cpus(text):
	cpus = set()
	for part in text.split(","):
		lo, _, hi = part.partition("-")
		cpus.update(range(int(lo), int(hi or lo) + 1))
	return cpus


def host_gate(ident):
	"""Section 7a: GenuineIntel family 6 model 0xB7 and CPU 4 inside cpu_core's mask, or stop for review."""
	c = ident["cpu4"]
	if c.get("vendor_id") != "GenuineIntel" or c.get("cpu family") != "6" or c.get("model") != str(0xB7):
		raise Stop(("host is not the documented Intel 6/0xB7", c))
	if 4 not in expand_cpus(ident["cpu_core_cpus"]):
		raise Stop(("CPU 4 is not a cpu_core CPU", ident["cpu_core_cpus"]))


def open_check(group, index, sink):
	"""One availability/format/affinity open of a group on the affinity probe. Returns (eligible, reason)."""
	row = run_sample(perf_argv(group) + PROBE, sink, {"kind": "open-check", "group": group, "index": index}, deadline=60)
	sink.write(row)
	try:
		lifecycle(row)
		if row["status"] != 0 or row["stdout"] != PROBE_STDOUT:
			return False, f"status {row['status']}, stdout {row['stdout'][:60]!r}, stderr tail {row['stderr'][-200:]!r}"
		parse(row["stderr"], group)
	except Stop as stop:
		return False, repr(stop)
	return True, "opened, counted, 100% running, probe saw CPU 4 only"


def discover(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	began = time.monotonic()
	os.sched_setaffinity(0, {4})
	pinned()
	bind_subjects()
	ident = identity()
	version = run_bounded(["perf", "--version"], 30, E0)
	ident["perf"] = version.stdout.strip()
	(out / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
	host_gate(ident)
	sink = Sink(out / "raw.jsonl")
	groups = {}
	for group in GROUPS:
		checks = []
		for index in range(2):
			if time.monotonic() - began > PREP_DEADLINE:
				raise Stop(("discovery deadline",))
			checks.append(open_check(group, index, sink))
		groups[group] = {"argv": perf_argv(group), "checks": [{"eligible": ok, "detail": why} for ok, why in checks],
			"eligible": all(ok for ok, _ in checks)}
		print(group, "eligible" if groups[group]["eligible"] else "untested", [why for ok, why in checks if not ok][:1], flush=True)
	optional = [g for g in GROUPS if g != REQUIRED and groups[g]["eligible"]]
	status = "STOP: required group R unavailable" if not groups[REQUIRED]["eligible"] else \
		"INCONCLUSIVE at discovery: no optional group available" if not optional else "available"
	manifest = {"status": status, "order": [REQUIRED] + optional if status == "available" else [], "groups": groups,
		"identity_sha256": sha(out / "identity.json"), "primaries": {k: v[1] for k, v in PRIMARY.items()},
		"note": "Eligibility is decided only by these two open checks per group on the affinity probe; probe counts select nothing."}
	(out / "availability.json").write_text(json.dumps(manifest, indent=1) + "\n")
	print("discovery:", status, manifest["order"], flush=True)
	if not groups[REQUIRED]["eligible"]:
		raise Stop(("required group R unavailable", groups[REQUIRED]["checks"]))


def load_availability(path):
	m = json.loads(pathlib.Path(path).read_text())
	if m.get("status") != "available" or m.get("order", [None])[0] != REQUIRED or len(m["order"]) < 2:
		raise Stop(("availability manifest does not permit a run", m.get("status")))
	if m["order"] != [g for g in GROUPS if g in m["order"]] or any(not m["groups"][g]["eligible"] for g in m["order"]):
		raise Stop(("availability manifest order or eligibility is inconsistent",))
	for g in m["order"]:
		if m["groups"][g]["argv"] != perf_argv(g):
			raise Stop(("group definition changed since discovery", g))
	if m.get("primaries") != {k: v[1] for k, v in PRIMARY.items()}:
		raise Stop(("availability manifest is for other subjects",))
	return m


def rehearse(out, availability):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	os.sched_setaffinity(0, {4})
	pinned()
	bind_subjects()
	m = load_availability(availability)
	sentinel = new_sentinel()
	sink = Sink(out / "raw.jsonl")
	staged = {side: stage(side) for side in ("base", "cand")}  # copied and hashed, never executed here
	row = run_sample(perf_argv(REQUIRED) + PROBE, sink, {"kind": "rehearsal-probe"}, deadline=60)
	sink.write(row)
	lifecycle(row)
	counters = parse(row["stderr"], REQUIRED)
	failing = run_sample(["perf", "stat", "-j", "--", "/usr/bin/false"], sink, {"kind": "rehearsal-failure"}, deadline=60)
	sink.write(failing)
	ref, outputs = references(), expected_stdout()
	report = {"order": m["order"], "staged": staged, "probe_counters": sorted(counters), "failure_status_retained": failing["status"],
		"references": ref, "expected_stdout_sha256": {k: __import__("hashlib").sha256(v.encode()).hexdigest() for k, v in outputs.items()},
		"planned_samples": len(m["order"]) * 5 * len(WORKLOADS) * 4}
	(out / "rehearsal.json").write_text(json.dumps(report, indent=1) + "\n")
	hits = scan(out, [sentinel])
	(out / "sentinel-scan.json").write_text(json.dumps({"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": sum(hits.values())}) + "\n")
	if hits or failing["status"] == 0:
		raise Stop(("rehearsal", hits, failing["status"]))
	print("rehearsal: order", m["order"], "planned samples", report["planned_samples"], "sentinel 0", flush=True)


def official(out, availability):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	began = time.monotonic()
	os.sched_setaffinity(0, {4})
	pinned()
	res = {"started": time.time(), "status": "running", "env": E0, "load_before": read("/proc/loadavg").split()[0]}
	persist = lambda: (out / "official.json").write_text(json.dumps(res, indent=1) + "\n")
	persist()
	try:
		bind_subjects()
		m = load_availability(availability)
		res.update(order=m["order"], availability_sha256=sha(availability))
		sentinel = new_sentinel()
		ref, outputs = references(), expected_stdout()
		res["references"] = ref
		sink = Sink(out / "raw.jsonl")
		res["groups"] = {}
		for group in m["order"]:
			samples = []
			for rep in range(5):
				for label, tail, _, ops in WORKLOADS:
					for subject in ("base", "cand", "cand", "base"):
						if time.monotonic() - began > OFFICIAL_DEADLINE:
							raise Stop(("official deadline",))
						digest = stage(subject)
						meta = {"kind": "event", "group": group, "rep": rep, "workload": label, "subject": subject, "hash": digest}
						row = run_sample(perf_argv(group) + [str(STAGE), *tail], sink, meta)
						row["hash_after"] = sha(STAGE)
						sink.write(row)
						lifecycle(row)
						if row["status"] != 0 or row["stdout"] != outputs[label]:
							raise Stop(("status/output", group, label, subject, row["status"], row["stdout"][:80], row["stderr"][-300:]))
						if row["hash_after"] != digest:
							raise Stop(("stage changed during sample", meta))
						counters = parse(row["stderr"], group)
						samples.append({**meta, "counters": counters, "metrics": metrics(group, counters, ops)})
			summary = summarize(group, samples)
			failures = anchor_check(group, summary, ref)
			res["groups"][group] = {"summary": summary, "anchor_failures": failures}
			persist()
			print("group", group, "anchors", "reproduced" if not failures else f"FAILED {failures[:3]}", flush=True)
			if failures:
				raise Nonreproducing((group, failures))
		res["status"] = "complete"
	except Nonreproducing as outcome:
		res.update(status="NONREPRODUCING / STOP", nonreproduction=repr(outcome))
	except BaseException as error:
		res.update(status="STOPPED (infrastructure, safety or measurement failure)", failure=repr(error))
		raise
	finally:
		res.update(ended=time.time(), load_after=read("/proc/loadavg").split()[0])
		persist()
		hits = scan(out, [os.environ.get("RNX0179_SENTINEL", "")]) if os.environ.get("RNX0179_SENTINEL") else {}
		(out / "sentinel-scan.json").write_text(json.dumps({"files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": sum(hits.values())}) + "\n")
	if hits:
		raise Stop(("sentinel found in official output", hits))
	print("OFFICIAL", res["status"], flush=True)


if __name__ == "__main__":
	mode, target = sys.argv[1], sys.argv[2]
	if mode == "discover":
		discover(target)
	elif mode == "rehearse":
		rehearse(target, sys.argv[3])
	elif mode == "official":
		official(target, sys.argv[3])
	else:
		raise SystemExit("usage: events.py discover|rehearse|official OUT_DIR [AVAILABILITY_JSON]")
