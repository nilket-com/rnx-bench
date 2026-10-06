"""rnx 0183 Stage A: the counting gate of the bounded frontend-delivery study (plan rnx 17d6d5a; grouping audit
2d3a11b). Groups R and F1 only, on the two retained 0179 primary binaries.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/frontend-0183/events0183.py discover OUT_DIR
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/frontend-0183/events0183.py rehearse OUT_DIR AVAILABILITY_JSON
	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/frontend-0183/events0183.py official OUT_DIR AVAILABILITY_JSON

F1 = instructions, cycles and DSB2MITE_SWITCHES.PENALTY_CYCLES (event 0x61, umask 0x02) in one strong pinned
cpu_core user-only group, --no-scale. F2 and F3 (the FRONTEND_RETIRED DSB-miss events) are EXCLUDED by the reviewed
grouping audit: their collection state is "not collected (unavailable)" and no spelling of them is ever opened here.
With no locating event the record closes at Stage A whatever F1 shows; Stages B and C do not run.

This driver imports the reviewed 0180 driver (events.py), 0181 driver (events0181.py) and 0179 helpers (common.py)
as libraries, pinned by sha256 and verified with the standard library BEFORE import. It edits none of them. The one
in-process addition is registering the F1 group definition in the 0180 library's GROUPS table so that its unchanged
argv builder and parser apply; the six 0180 definitions are not touched (checked by a control).

Sampling, classification, stop policy (anchor, safety, identity and deadline problems global; a defect of the F1
counter row group-local), reproduction anchors, the descriptive "resolved" rule, deadlines and retention are
0181's. Sentinel scope, as inherited: the official run scans everything it wrote on success and on failure, and a hit or
scan error overrides its status; rehearsal scans on its success path only; discovery sets no sentinel (it runs
with a fixed minimal environment and writes only identity, probe rows and the manifest). What is new is stage_a(): the statuses, disposition and contrast flag of plan section 3.
"""
import hashlib, json, math, os, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
LIBRARIES = {"probes/execution-cost-0180/events.py": "36595033600391e412897f2676364a62411c4d8691cf5eb9f5998a1ef2fc10c2",
	"probes/execution-cost-0181/events0181.py": "bb44cf0df873ac6412298f643e4957cc1eb491cc23f091cdbd4f0185224d94c7",
	"probes/startup-0179/common.py": "abd19671c56d7e8f9a6a07f72a3b98b39e2ef0dfdc45a0602e31937954c9ddba"}
for _rel, _want in LIBRARIES.items():
	_got = hashlib.sha256((REPO / _rel).read_bytes()).hexdigest()
	if _got != _want:
		raise SystemExit(f"refusing to import {_rel}: sha256 {_got} is not the pinned {_want}")
sys.path.insert(0, str(REPO / "probes/execution-cost-0181"))
import events0181 as ev81  # noqa: E402  (also verifies and imports the 0180 driver and 0179 helpers)
base = ev81.base
Stop, Nonreproducing, LocalInvalid, Sink = ev81.Stop, ev81.Nonreproducing, ev81.LocalInvalid, ev81.Sink
for _name, _module in (("probes/execution-cost-0181/events0181.py", ev81), ("probes/execution-cost-0180/events.py", base)):
	if pathlib.Path(_module.__file__).resolve() != (REPO / _name).resolve():
		raise SystemExit(f"refusing: a library resolved to {_module.__file__}, not this repository's pinned {_name}")

ORDER = ["R", "F1"]
REQUIRED = "R"
F1_EVENT = "dsb2mite_penalty_cycles"
F1_GROUP = {"hardware": base.ANCHORS + [base.raw("0x61", "0x02", F1_EVENT)], "software": []}
if "F1" in base.GROUPS and base.GROUPS["F1"] != F1_GROUP:
	raise SystemExit("refusing: the 0180 library already defines a different F1")
base.GROUPS["F1"] = F1_GROUP  # in-process registration only; no library file is edited
EXCLUDED = {"F2": "not collected (unavailable)", "F3": "not collected (unavailable)"}
EXCLUSION_REASON = ("TakenAlone safety beside other possibly active programmable counters cannot be established from primary "
	"sources on this host without changing system services (grouping audit rnx 2d3a11b)")
SIGNAL = ["run-numeric", "run-range_signed", "run-range_negative"]
CONTRAST = ["run-while", "run-empty"]
REPORTED = ["run-calls", "run-fib"]
# This record's own reviewed discovery receipts; unset until the availability review, and admission refuses until then.
DISCOVERY = REPO / "results/frontend-0183/discovery1"
AVAILABILITY_SHA256 = None
IDENTITY_SHA256 = None


def library_gate():
	for rel, want in LIBRARIES.items():
		if base.sha(REPO / rel) != want:
			raise Stop(("imported library differs from its pinned hash", rel))
	return dict(LIBRARIES)


def resolves(q, direction):
	return isinstance(q, dict) and q.get("resolved") is True and q.get("direction") == direction


def checked(q, what):
	"""A summary quantity as the decision uses it, or Stop. `difference` a finite number (not bool, not a string);
	`resolved` exactly a bool; `direction` exactly "up", "down" or "none" and consistent with the sign of the
	difference; a resolved quantity cannot have a zero difference. The inherited summarizer emits coherent fields;
	this guards the decision boundary against a malformed or contradictory summary."""
	if not isinstance(q, dict) or "status" in q:
		raise Stop(("summary quantity missing or undefined for a valid group", what))
	d = q.get("difference")
	if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d):
		raise Stop(("summary difference is not a finite number", what, d))
	if not isinstance(q.get("resolved"), bool):
		raise Stop(("summary `resolved` is not a bool", what, q.get("resolved")))
	want = "up" if d > 0 else "down" if d < 0 else "none"
	if q.get("direction") != want:
		raise Stop(("summary `direction` is not consistent with its difference", what, q.get("direction"), d))
	if q["resolved"] and d == 0:
		raise Stop(("a resolved quantity cannot have a zero difference", what))
	return q


def window_status(state, quantities):
	"""Status of F1 on one signal window, by the frozen precedence of plan section 3 (first match wins):
	unavailable, failed, undefined, contrary, strong, weak, intermediate. Returns (status, detail)."""
	if state == "not collected (unavailable)":
		return "unavailable", {}
	if state == "invalid":
		return "failed", {}
	if state != "valid":
		raise Stop(("unknown collection state", state))
	f1, cycles = checked(quantities.get(F1_EVENT), F1_EVENT), checked(quantities.get("cycles"), "cycles")
	detail = {"D_f1": f1["difference"], "D_cycles": cycles["difference"], "f1_resolved": f1["resolved"], "f1_direction": f1["direction"],
		"cycles_resolved": cycles["resolved"], "cycles_direction": cycles["direction"]}
	if not resolves(cycles, "up") or cycles["difference"] <= 0:
		return "undefined", detail  # no resolved positive cycle excess in this group: r is not formed
	if resolves(f1, "down"):
		return "contrary", detail
	r = f1["difference"] / cycles["difference"]
	if not math.isfinite(r):
		raise Stop(("r is not finite", f1["difference"], cycles["difference"]))
	detail["r"] = r
	if resolves(f1, "up"):
		if r >= 0.5:
			return "strong", detail
		if r <= 0.1:
			return "weak", detail
		return "intermediate", detail
	return "weak", detail  # resolves neither up nor down


def locating_event(states):
	"""Selected by collection states alone: F3 if valid; F2 only if F3 was unavailable and F2 is valid; else none.
	An invalid F3 is never replaced by F2."""
	if states.get("F3") == "valid":
		return "F3"
	if states.get("F3") == "not collected (unavailable)" and states.get("F2") == "valid":
		return "F2"
	return None


def stage_a(f1_state, summary, states=None):
	"""Per-window statuses, the Stage A disposition, the contrast flag and the closure consequence (plan section 3).
	`summary` is the F1 group's 0180-style summary (None unless F1 is valid)."""
	states = dict(EXCLUDED if states is None else states)
	states["F1"] = f1_state
	windows = {}
	for w in SIGNAL:
		status, detail = window_status(f1_state, summary[w]["quantities"] if f1_state == "valid" else {})
		windows[w] = {"status": status, **detail}
	got = [windows[w]["status"] for w in SIGNAL]
	if all(s == "unavailable" for s in got):
		disposition = "A-unavailable"
	elif any(s in ("failed", "undefined", "unavailable") for s in got):
		disposition = "A-failed"
	elif all(s == "strong" for s in got):
		disposition = "A-strengthened"
	elif all(s in ("weak", "contrary") for s in got):
		disposition = "A-weakened"
	else:
		disposition = "A-mixed"
	out = {"collection_states": states, "exclusion_reason": EXCLUSION_REASON, "signal_windows": windows, "disposition": disposition}
	flags = {}
	if f1_state == "valid":
		smallest = min(windows[w]["D_f1"] for w in SIGNAL)
		for w in CONTRAST + REPORTED:  # the same validation as the signal windows, before any flag or report is formed
			checked(summary[w]["quantities"].get(F1_EVENT), (w, F1_EVENT))
			checked(summary[w]["quantities"].get("cycles"), (w, "cycles"))
		for w in CONTRAST:
			q = summary[w]["quantities"][F1_EVENT]
			flagged = resolves(q, "up") and q["difference"] >= 0.5 * smallest
			flags[w] = {"D_f1": q["difference"], "resolved": q["resolved"], "direction": q["direction"], "threshold": 0.5 * smallest,
				"flagged": bool(flagged)}
		out["reported_windows"] = {w: {"D_f1": summary[w]["quantities"][F1_EVENT]["difference"], "D_cycles": summary[w]["quantities"]["cycles"]["difference"],
			"f1_resolved": summary[w]["quantities"][F1_EVENT]["resolved"], "f1_direction": summary[w]["quantities"][F1_EVENT]["direction"]} for w in REPORTED}
	out["contrast_flag"] = {"windows": flags, "any": any(v["flagged"] for v in flags.values()),
		"meaning": "A flagged contrast window means the penalty-cycle difference is not specific to the windows with excess cycles. "
			"It qualifies the inference and does not change the disposition."}
	event = locating_event(states)
	out["locating_event"] = event
	# This record excludes F2 and F3, so no Stage B proposal is ever permitted by this driver. General Stage B
	# eligibility for a valid locating event (which also requires that event to resolve up on all three signal
	# windows) is NOT implemented here; locating_event() is only the state selector, tested separately.
	out["stage_b_proposal_permitted"] = False
	out["closure"] = "The record closes at Stage A with this counting result: no locating event is available." if not event else \
		"Not evaluated: Stage B eligibility for a collected locating event is not implemented in this driver."
	out["limits"] = ("r is a ratio of two differences of pooled medians: a comparison of magnitudes, not a same-sample ratio and not an "
		"accounting of where cycles went. A-strengthened does not make the switch penalty an additive explanation of the excess.")
	return out


def discover(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	base.start_phase(base.PREP_DEADLINE)
	os.sched_setaffinity(0, {4})
	base.pinned()
	libraries = library_gate()
	base.bind_subjects()
	ident, perf_receipt = ev81.identity_now()
	(out / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
	(out / "identity-commands.json").write_text(json.dumps({"perf_version": perf_receipt}, indent=1) + "\n")
	base.host_gate(ident)
	sink = Sink(out / "raw.jsonl")
	groups = {}
	for group in ORDER:
		checks = [ev81.open_check(group, index, sink) for index in range(2)]
		groups[group] = {"argv": base.perf_argv(group), "checks": [{"eligible": ok, "detail": why} for ok, why in checks],
			"eligible": all(ok for ok, _ in checks)}
		print(group, "eligible" if groups[group]["eligible"] else "untested", [why for ok, why in checks if not ok][:1], flush=True)
	status = "STOP: required group R unavailable" if not groups[REQUIRED]["eligible"] else \
		"A-unavailable: F1 not available at discovery" if not groups["F1"]["eligible"] else "available"
	previous = json.loads((REPO / "results/execution-cost-0181/discovery1/identity.json").read_text())
	changed = sorted(k for k in set(previous) | set(ident) if previous.get(k) != ident.get(k))
	manifest = {"record": "0183", "status": status, "order": list(ORDER) if status == "available" else [], "groups": groups,
		"excluded": dict(EXCLUDED), "exclusion_reason": EXCLUSION_REASON, "identity_sha256": base.sha(out / "identity.json"),
		"primaries": {k: v[1] for k, v in base.PRIMARY.items()}, "libraries": libraries,
		"changes_since_0181_discovery": {k: [previous.get(k), ident.get(k)] for k in changed},
		"note": "Eligibility is decided only by two open checks per group on the affinity probe; probe counts select nothing. "
			"F2, F3 and every 0180 group other than R are not opened in this record."}
	(out / "availability.json").write_text(json.dumps(manifest, indent=1) + "\n")
	print("discovery:", status, manifest["order"], "changed since 0181:", changed, flush=True)
	if not groups[REQUIRED]["eligible"]:
		raise Stop(("required group R unavailable", groups[REQUIRED]["checks"]))


def validate_availability(m, identity_sha256):
	"""Content validation, independent of the byte pins."""
	if m.get("record") != "0183" or m.get("status") != "available":
		raise Stop(("availability manifest does not permit a run", m.get("record"), m.get("status")))
	if m.get("identity_sha256") != identity_sha256 or not identity_sha256:
		raise Stop(("availability manifest is bound to another identity receipt",))
	if list(m.get("groups", {})) != ORDER:
		raise Stop(("availability manifest does not cover exactly R and F1",))
	for g, row in m["groups"].items():
		if row.get("argv") != base.perf_argv(g):
			raise Stop(("group definition changed since discovery", g))
		checks = row.get("checks")
		if not isinstance(checks, list) or len(checks) != 2 or any(not isinstance(c, dict) or not isinstance(c.get("eligible"), bool) for c in checks):
			raise Stop(("group does not have exactly two recorded open checks", g))
		if row.get("eligible") is not all(c["eligible"] for c in checks) or row["eligible"] is not True:
			raise Stop(("group is not eligible by both of its open checks", g))
	if m.get("order") != ORDER:
		raise Stop(("order is not R then F1", m.get("order")))
	if m.get("excluded") != EXCLUDED:
		raise Stop(("excluded events differ from the reviewed exclusion", m.get("excluded")))
	if m.get("primaries") != {k: v[1] for k, v in base.PRIMARY.items()}:
		raise Stop(("availability manifest is for other subjects",))
	if m.get("libraries") != LIBRARIES:
		raise Stop(("availability manifest was made with other libraries",))
	return m


def load_availability(path):
	"""Admission before anything is staged: reviewed receipt bytes, content, libraries, and the current host equal to
	the recorded identity. Returns (manifest, recorded identity, admission receipt)."""
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
	perf_receipt = ev81.recheck_identity(recorded)
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
	counters = ev81.classify(row["stderr"], REQUIRED)
	failing = base.run_sample(["perf", "stat", "-j", "--", "/usr/bin/false"], sink, {"kind": "rehearsal-failure"}, deadline=60)
	sink.write(failing)
	base.lifecycle(failing)
	if failing["status"] != 1:
		raise Stop(("failure-path rehearsal did not end with status 1", failing["status"]))
	ref, outputs = base.references(), base.expected_stdout()
	report = {"order": m["order"], "admission": admission, "staged": staged, "probe_counters": sorted(counters),
		"failure_status_retained": failing["status"], "references": ref,
		"expected_stdout_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in outputs.items()},
		"planned_samples": len(m["order"]) * 5 * len(base.WORKLOADS) * 4}
	(out / "rehearsal.json").write_text(json.dumps(report, indent=1) + "\n")
	hits = base.scan(out, [sentinel])
	(out / "sentinel-scan.json").write_text(json.dumps({"completed": True, "files_scanned": sum(1 for p in out.rglob("*") if p.is_file()),
		"occurrences": sum(hits.values())}) + "\n")
	if hits:
		raise Stop(("sentinel found in rehearsal output", hits))
	print("rehearsal: order", m["order"], "planned samples", report["planned_samples"], "sentinel 0", flush=True)


def official(out, availability):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	base.start_phase(base.OFFICIAL_DEADLINE)
	os.sched_setaffinity(0, {4})
	base.pinned()
	res = {"record": "0183", "stage": "A", "started": time.time(), "status": "running", "env": base.E0,
		"load_before": base.read("/proc/loadavg").split()[0]}
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
		f1_state, f1_summary = "invalid", None
		for group in m["order"]:
			receipt = ev81.recheck_identity(recorded)  # before each group: drift stops everything
			outcome, detail = ev81.run_group(group, sink, outputs)
			if outcome == "failed":  # only reachable for F1: a defect of its counter row
				res["groups"][group] = {"status": "FAILED / INCOMPLETE (counter validity)", "identity_recheck": receipt, **detail,
					"note": "No scientific summary: an incomplete group supports no claim."}
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
			if group == "F1":
				f1_state, f1_summary = "valid", summary
		res["stage_a"] = stage_a(f1_state, f1_summary)
		res["status"] = "COMPLETE" if f1_state == "valid" else "PARTIAL COUNTER-VALIDITY STOP"
		print("STAGE A", res["stage_a"]["disposition"], {w: v["status"] for w, v in res["stage_a"]["signal_windows"].items()}, flush=True)
	except Nonreproducing as outcome:
		res.update(status="GLOBAL STOP (NONREPRODUCING)", nonreproduction=repr(outcome))
	except LocalInvalid as leaked:
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
		raise SystemExit("usage: events0183.py discover|rehearse|official OUT_DIR [AVAILABILITY_JSON]")
