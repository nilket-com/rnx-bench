"""rnx 0181: the branch, frontend-delivery and load diagnostics that 0180 never collected (plan rnx d724cf7).

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/execution-cost-0181/events0181.py discover OUT_DIR
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/execution-cost-0181/events0181.py rehearse OUT_DIR AVAILABILITY_JSON
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/execution-cost-0181/events0181.py official OUT_DIR AVAILABILITY_JSON

A NEW study selected after seeing 0180's measurement STOP; not a replay or completion of 0180. Groups R, C, D and E
only, with 0180's event definitions, subjects, windows, 0179 references, tolerances and descriptive rule unchanged.
Groups A and B are neither opened nor measured here. One official run: R, then every eligible diagnostic in order.

This driver IMPORTS the reviewed 0180 driver (events.py) and 0179's process helpers (common.py) as libraries, pinned
by sha256, and edits neither. What is new here: the four-group discovery and availability manifest, admission against
this record's own reviewed receipts, the per-group identity recheck, and the stop policy of plan section 4:

GLOBAL stop (no later group): anything in R; a failed 0179 reproduction anchor in a completed diagnostic; subject,
	source, receipt, hash, host, affinity or E0 drift; wrong output; nonzero subject/perf status; timeout, interrupt,
	survivor or unreaped process; a malformed counter line; an INVALID ANCHOR COUNTER (instructions or cycles) in any
	group; the outer deadline; a sentinel hit or scan failure; any unclassified exception.
GROUP-LOCAL counter-validity failure: a defect of a DIAGNOSTIC counter row as the parser sees it (missing, duplicate,
	unexpected, non-finite or negative, not counted or unsupported, wrong unit, missing or non-positive running time,
	enabled != running where supplied, running != 100%). The raw row is already retained; the whole diagnostic is marked
	FAILED / INCOMPLETE with no scientific summary for its prefix, its remaining samples are not run, nothing is retried,
	and the next originally eligible group may run after the identity recheck. A zero denominator is NOT a failure:
	the quantity is reported as undefined.

A sample is classified in this order: (i) lifecycle, command status, exact stdout, pre/post stage hash; (ii) every
counter line must be a parseable JSON object that names its event; (iii) the two anchor rows alone must satisfy the unchanged 0180 parser rules;
(iv) only then the whole group is validated, so a failure at (iv) can only come from a diagnostic row.
"""
import json, os, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
LIBRARIES = {"probes/execution-cost-0180/events.py": "36595033600391e412897f2676364a62411c4d8691cf5eb9f5998a1ef2fc10c2",
	"probes/startup-0179/common.py": "abd19671c56d7e8f9a6a07f72a3b98b39e2ef0dfdc45a0602e31937954c9ddba"}
sys.path.insert(0, str(REPO / "probes/execution-cost-0180"))
import events as base  # noqa: E402  (the reviewed 0180 driver, used as a library)
from events import Stop, Nonreproducing, Sink  # noqa: E402

ORDER = ["R", "C", "D", "E"]  # frozen; A and B are not part of this record
REQUIRED, DIAGNOSTICS = "R", ["C", "D", "E"]
GROUPS = {g: base.GROUPS[g] for g in ORDER}
# This record's own reviewed discovery receipts. The byte pins are set only after the availability review; until
# then admission refuses.
DISCOVERY = REPO / "results/execution-cost-0181/discovery1"
AVAILABILITY_SHA256 = None
IDENTITY_SHA256 = None


class LocalInvalid(Exception):
	"""A diagnostic counter row failed validity: stops and invalidates this group only (plan section 4)."""


def library_gate():
	"""The imported libraries must be exactly the reviewed files."""
	for rel, want in LIBRARIES.items():
		if base.sha(REPO / rel) != want:
			raise Stop(("imported library differs from its pinned hash", rel))
	if pathlib.Path(base.__file__).resolve() != (REPO / "probes/execution-cost-0180/events.py").resolve():
		raise Stop(("imported driver is not this repository's 0180 events.py", base.__file__))
	return dict(LIBRARIES)


def classify(text, group):
	"""Counters of one sample, or Stop (global) or LocalInvalid (this diagnostic only). See the module docstring."""
	rows, anchors = [], []
	for line in text.splitlines():
		if not line.startswith("{"):
			continue
		try:
			row = json.loads(line)
		except json.JSONDecodeError as error:
			raise Stop(("malformed counter line (unclassified, global)", line[:160], repr(error)))
		if not isinstance(row, dict):
			raise Stop(("counter line is not an object (unclassified, global)", line[:160]))
		if not isinstance(row.get("event"), str):
			# 0180's parser skips an object without an event name; here such a row is unclassified, hence global.
			raise Stop(("counter line without an event name (unclassified, global)", line[:160]))
		rows.append(line)
		if row.get("event") in ("instructions", "cycles"):
			anchors.append(line)
	try:
		base.parse("\n".join(anchors) + "\n", REQUIRED)  # the anchor rows by themselves, 0180's unchanged rules
	except Stop as stop:
		raise Stop(("invalid anchor counter (global)", group, repr(stop)))
	if group == REQUIRED:
		return base.parse(text, group)  # R has no diagnostic rows: every failure here is global
	try:
		return base.parse(text, group)
	except Stop as stop:
		raise LocalInvalid((group, repr(stop)))


def identity_now():
	return base.current_identity()


def discover(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	base.start_phase(base.PREP_DEADLINE)
	os.sched_setaffinity(0, {4})
	base.pinned()
	libraries = library_gate()
	base.bind_subjects()
	ident, perf_receipt = identity_now()
	(out / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
	(out / "identity-commands.json").write_text(json.dumps({"perf_version": perf_receipt}, indent=1) + "\n")
	base.host_gate(ident)
	sink = Sink(out / "raw.jsonl")
	groups = {}
	for group in ORDER:
		checks = [base.open_check(group, index, sink) for index in range(2)]
		groups[group] = {"argv": base.perf_argv(group), "checks": [{"eligible": ok, "detail": why} for ok, why in checks],
			"eligible": all(ok for ok, _ in checks)}
		print(group, "eligible" if groups[group]["eligible"] else "untested", [why for ok, why in checks if not ok][:1], flush=True)
	diagnostics = [g for g in DIAGNOSTICS if groups[g]["eligible"]]
	status = "STOP: required group R unavailable" if not groups[REQUIRED]["eligible"] else \
		"INCONCLUSIVE at discovery: no diagnostic group available" if not diagnostics else "available"
	previous = REPO / "results/execution-cost-0180/discovery1/identity.json"
	old = json.loads(previous.read_text())
	changed = sorted(k for k in set(old) | set(ident) if old.get(k) != ident.get(k))
	manifest = {"record": "0181", "status": status, "order": [REQUIRED] + diagnostics if status == "available" else [], "groups": groups,
		"identity_sha256": base.sha(out / "identity.json"), "primaries": {k: v[1] for k, v in base.PRIMARY.items()}, "libraries": libraries,
		"changes_since_0180_discovery": {k: [old.get(k), ident.get(k)] for k in changed},
		"note": "Eligibility is decided only by these two open checks per group on the affinity probe; probe counts select nothing. "
			"Groups A and B are not part of this record and were not opened."}
	(out / "availability.json").write_text(json.dumps(manifest, indent=1) + "\n")
	print("discovery:", status, manifest["order"], "changed since 0180:", changed, flush=True)
	if not groups[REQUIRED]["eligible"]:
		raise Stop(("required group R unavailable", groups[REQUIRED]["checks"]))


def validate_availability(m, identity_sha256):
	"""Content validation, independent of the byte pins: this record, status, the companion identity hash, exactly the
	four frozen groups with their frozen argv, two recorded checks each, eligibility equal to both checks passing,
	R eligible, at least one diagnostic eligible, the order equal to R followed by EVERY eligible diagnostic in frozen
	order, the two primaries and the pinned libraries."""
	if m.get("record") != "0181" or m.get("status") != "available":
		raise Stop(("availability manifest does not permit a run", m.get("record"), m.get("status")))
	if m.get("identity_sha256") != identity_sha256 or not identity_sha256:
		raise Stop(("availability manifest is bound to another identity receipt",))
	if list(m.get("groups", {})) != ORDER:
		raise Stop(("availability manifest does not cover exactly R, C, D, E",))
	eligible = []
	for g, row in m["groups"].items():
		if row.get("argv") != base.perf_argv(g):
			raise Stop(("group definition changed since discovery", g))
		checks = row.get("checks")
		if not isinstance(checks, list) or len(checks) != 2 or any(not isinstance(c, dict) or not isinstance(c.get("eligible"), bool) for c in checks):
			raise Stop(("group does not have exactly two recorded open checks", g))
		both = all(c["eligible"] for c in checks)
		if row.get("eligible") is not both:
			raise Stop(("group eligibility disagrees with its open checks", g))
		if both:
			eligible.append(g)
	if REQUIRED not in eligible:
		raise Stop(("required group R is not eligible",))
	if len(eligible) < 2:
		raise Stop(("no diagnostic group is eligible: inconclusive at discovery",))
	if m.get("order") != eligible:
		raise Stop(("order is not R followed by every eligible diagnostic", m.get("order"), eligible))
	if m.get("primaries") != {k: v[1] for k, v in base.PRIMARY.items()}:
		raise Stop(("availability manifest is for other subjects",))
	if m.get("libraries") != LIBRARIES:
		raise Stop(("availability manifest was made with other libraries",))
	return m


def recheck_identity(recorded):
	"""The current filtered host identity must equal the recorded one in every field. Returns the perf receipt."""
	now, perf_receipt = identity_now()
	drift = sorted(k for k in set(recorded) | set(now) if recorded.get(k) != now.get(k))
	if drift:
		raise Stop(("host identity differs from this record's discovery", {k: [recorded.get(k), now.get(k)] for k in drift}))
	return perf_receipt


def load_availability(path):
	"""Admission before anything is staged: this record's reviewed availability and identity receipts byte for byte,
	their contents validated, the libraries pinned, and the host re-observed now and equal to the recorded identity.
	Returns (manifest, recorded identity, admission receipt)."""
	path = pathlib.Path(path)
	identity_path = path.parent / "identity.json"
	if AVAILABILITY_SHA256 is None or IDENTITY_SHA256 is None:
		raise Stop(("the availability review has not frozen this record's receipt hashes",))
	if path.resolve() != (DISCOVERY / "availability.json").resolve():
		raise Stop(("availability manifest is not this record's reviewed discovery receipt", str(path)))
	if base.sha(path) != AVAILABILITY_SHA256:
		raise Stop(("availability manifest does not match its reviewed hash",))
	if not identity_path.is_file() or base.sha(identity_path) != IDENTITY_SHA256:
		raise Stop(("identity receipt does not match its reviewed hash",))
	libraries = library_gate()
	m = validate_availability(json.loads(path.read_text()), IDENTITY_SHA256)
	recorded = json.loads(identity_path.read_text())
	base.host_gate(recorded)
	perf_receipt = recheck_identity(recorded)
	return m, recorded, {"availability_sha256": AVAILABILITY_SHA256, "identity_sha256": IDENTITY_SHA256, "libraries": libraries,
		"identity_fields_compared": sorted(recorded), "perf_version_receipt": perf_receipt}


def rehearse(out, availability):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	base.start_phase(base.PREP_DEADLINE)
	os.sched_setaffinity(0, {4})
	base.pinned()
	base.bind_subjects()
	m, _, admission = load_availability(availability)
	sentinel = base.new_sentinel()
	sink = Sink(out / "raw.jsonl")
	staged = {side: base.stage(side) for side in ("base", "cand")}  # copied and hashed, never executed here
	row = base.run_sample(base.perf_argv(REQUIRED) + base.PROBE, sink, {"kind": "rehearsal-probe"}, deadline=60)
	sink.write(row)
	base.lifecycle(row)
	if row["status"] != 0 or row["stdout"] != base.PROBE_STDOUT:
		raise Stop(("rehearsal probe status/affinity", row["status"], row["stdout"][:80]))
	counters = classify(row["stderr"], REQUIRED)
	failing = base.run_sample(["perf", "stat", "-j", "--", "/usr/bin/false"], sink, {"kind": "rehearsal-failure"}, deadline=60)
	sink.write(failing)
	base.lifecycle(failing)
	if failing["status"] != 1:
		raise Stop(("failure-path rehearsal did not end with status 1", failing["status"]))
	ref, outputs = base.references(), base.expected_stdout()
	report = {"order": m["order"], "admission": admission, "staged": staged, "probe_counters": sorted(counters),
		"failure_status_retained": failing["status"], "references": ref,
		"expected_stdout_sha256": {k: __import__("hashlib").sha256(v.encode()).hexdigest() for k, v in outputs.items()},
		"planned_samples": len(m["order"]) * 5 * len(base.WORKLOADS) * 4}
	(out / "rehearsal.json").write_text(json.dumps(report, indent=1) + "\n")
	hits = base.scan(out, [sentinel])
	(out / "sentinel-scan.json").write_text(json.dumps({"completed": True, "files_scanned": sum(1 for p in out.rglob("*") if p.is_file()),
		"occurrences": sum(hits.values())}) + "\n")
	if hits:
		raise Stop(("sentinel found in rehearsal output", hits))
	print("rehearsal: order", m["order"], "planned samples", report["planned_samples"], "sentinel 0", flush=True)


def run_group(group, sink, outputs):
	"""All 140 samples of one group in the frozen order. Returns ("complete", samples) or ("failed", detail) for a
	group-local counter-validity failure. Every global problem raises Stop."""
	samples, rows = [], 0
	for rep in range(5):
		for label, tail, _, ops in base.WORKLOADS:
			for subject in ("base", "cand", "cand", "base"):
				base.budget(base.SAMPLE_DEADLINE)  # nothing is staged once the phase is over
				digest = base.stage(subject)
				meta = {"kind": "event", "group": group, "rep": rep, "workload": label, "subject": subject, "hash": digest}
				row = base.run_sample(base.perf_argv(group) + [str(base.STAGE), *tail], sink, meta)
				row["hash_after"] = base.sha(base.STAGE)
				sink.write(row)
				rows += 1
				base.lifecycle(row)
				if row["status"] != 0 or row["stdout"] != outputs[label]:
					raise Stop(("status/output", group, label, subject, row["status"], row["stdout"][:80], row["stderr"][-300:]))
				if row["hash_after"] != digest:
					raise Stop(("stage changed during sample", meta))
				try:
					counters = classify(row["stderr"], group)
				except LocalInvalid as invalid:
					return "failed", {"rows_retained": rows, "failing_sample": {k: meta[k] for k in ("rep", "workload", "subject")}, "reason": repr(invalid)}
				samples.append({**meta, "counters": counters, "metrics": base.metrics(group, counters, ops)})
	return "complete", samples


def official(out, availability):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	base.start_phase(base.OFFICIAL_DEADLINE)
	os.sched_setaffinity(0, {4})
	base.pinned()
	res = {"record": "0181", "started": time.time(), "status": "running", "env": base.E0, "load_before": base.read("/proc/loadavg").split()[0]}
	persist = lambda: (out / "official.json").write_text(json.dumps(res, indent=1) + "\n")
	persist()
	sentinel = base.new_sentinel()
	scan_failed = False
	try:
		base.bind_subjects()
		m, recorded, admission = load_availability(availability)  # before staging or any sample
		res.update(order=m["order"], admission=admission)
		ref, outputs = base.references(), base.expected_stdout()
		res["references"] = ref
		sink = Sink(out / "raw.jsonl")
		res["groups"] = {}
		for group in m["order"]:
			receipt = recheck_identity(recorded)  # before each group: drift stops everything
			outcome, detail = run_group(group, sink, outputs)
			if outcome == "failed":
				res["groups"][group] = {"status": "FAILED / INCOMPLETE (counter validity)", "identity_recheck": receipt, **detail,
					"note": "No scientific summary: an incomplete group cannot establish reproduction; its prefix supports no claim."}
				persist()
				print("group", group, "FAILED / INCOMPLETE", detail["reason"][:160], flush=True)
				continue
			summary = base.summarize(group, detail)
			failures = base.anchor_check(group, summary, ref)
			res["groups"][group] = {"status": "complete" if not failures else "NONREPRODUCING", "identity_recheck": receipt, "summary": summary,
				"anchor_failures": failures}
			persist()
			print("group", group, "anchors", "reproduced" if not failures else f"FAILED {failures[:3]}", flush=True)
			if failures:
				raise Nonreproducing((group, failures))
		failed = [g for g, v in res["groups"].items() if v["status"].startswith("FAILED")]
		complete = [g for g, v in res["groups"].items() if v["status"] == "complete" and g != REQUIRED]
		res.update(failed_groups=failed, complete_diagnostics=complete)
		res["status"] = "COMPLETE" if not failed else "PARTIAL COUNTER-VALIDITY STOP"
		if failed and not complete:
			res["note"] = "Every eligible diagnostic failed its validity gate: no mechanism conclusion is supported."
	except Nonreproducing as outcome:
		res.update(status="GLOBAL STOP (NONREPRODUCING)", nonreproduction=repr(outcome))
	except LocalInvalid as leaked:  # cannot happen for R; anything reaching here is unclassified
		res.update(status="GLOBAL STOP (unclassified failure)", failure=repr(leaked))
		raise Stop(("unclassified counter-validity failure", repr(leaked)))
	except BaseException as error:
		res.update(status="GLOBAL STOP (infrastructure, safety or measurement failure)", failure=repr(error))
		raise
	finally:
		res.update(ended=time.time(), load_after=base.read("/proc/loadavg").split()[0])
		persist()
		try:
			hits = base.scan(out, [sentinel])
			receipt = {"completed": True, "files_scanned": sum(1 for p in out.rglob("*") if p.is_file()), "occurrences": sum(hits.values()),
				"files_with_occurrences": sorted(str(pathlib.Path(p).relative_to(out)) for p in hits)}
		except Exception as error:
			receipt = {"completed": False, "error": repr(error)}
		res["sentinel_scan"] = receipt
		if not receipt["completed"] or receipt["occurrences"]:
			scan_failed = True
			res["status_before_scan"] = res["status"]
			res["status"] = "GLOBAL STOP (sentinel occurrence or scan failure)"
		persist()
		(out / "sentinel-scan.json").write_text(json.dumps(receipt, indent=1) + "\n")
	print("OFFICIAL", res["status"], flush=True)
	if scan_failed:
		raise Stop(("sentinel occurrence or scan failure", res["sentinel_scan"]))


if __name__ == "__main__":
	mode, target = sys.argv[1], sys.argv[2]
	if mode == "discover":
		discover(target)
	elif mode == "rehearse":
		rehearse(target, sys.argv[3])
	elif mode == "official":
		official(target, sys.argv[3])
	else:
		raise SystemExit("usage: events0181.py discover|rehearse|official OUT_DIR [AVAILABILITY_JSON]")
