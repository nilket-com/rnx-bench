"""rnx 0180 untimed controls for events.py (plan rnx ee3a5de section 7e). Synthetic perf output and mocked sampling only:
no perf process, no subject, no counter is opened here. Each control injects one defect and requires the stated refusal.

	python3 controls_events.py OUT_DIR
"""
import copy, json, lzma, os, pathlib, sys, time
import events

RESULTS = {}


def control(name):
	def wrap(fn):
		began = time.monotonic()
		try:
			RESULTS[name] = {"pass": True, "detail": fn(), "seconds": time.monotonic() - began}
		except Exception as error:
			RESULTS[name] = {"pass": False, "error": repr(error), "seconds": time.monotonic() - began}
		print(name, "PASS" if RESULTS[name]["pass"] else f"FAIL {RESULTS[name]['error']}", flush=True)
		return fn
	return wrap


def refused(fn, kind=events.Stop):
	try:
		fn()
	except kind as stop:
		return repr(stop)[:300]
	raise AssertionError("accepted")


def perf_text(group, values=None, drop=(), extra=(), running=100.0, pmu="cpu_core", override=None):
	"""Synthetic perf-stat JSON for a group; counters default to plausible positive values."""
	hw, sw = events.names(group)
	default = {"instructions": 1.0e9, "cycles": 5.0e8, "ref_cycles": 4.0e8, "slots": 3.0e9, "td_retiring": 1.5e9, "td_bad_spec": 0.3e9,
		"td_fe_bound": 0.6e9, "td_be_bound": 0.6e9, "br_inst_retired_all": 2.0e8, "br_misp_retired_all": 1.0e6, "idq_dsb_uops": 9.0e8,
		"idq_mite_uops": 1.0e8, "icache_data_stalls": 1.0e6, "mem_load_retired_l1_miss": 1.0e5, "ld_blocks_store_forward": 1.0e4,
		"context_switches": 0.0, "cpu_migrations": 0.0, "task_clock": 1.0e8}
	default.update(values or {})
	software = {v: k for k, v in events.SOFTWARE_NAMES.items()}
	lines = []
	for name in hw + sw:
		if name in drop:
			continue
		row = {"counter-value": f"{default[name]:.6f}", "unit": events.UNITS.get(name, ""), "event": software.get(name, name), "event-runtime": 100,
			"pcnt-running": running}
		if name in hw:
			row["pmu"] = pmu
		if override and name in override:
			row.update(override[name])
		lines.append(json.dumps(row))
	lines += list(extra)
	return "\n".join(lines) + "\n"


def synthetic_samples(group, base=None, cand=None, reps=5, order=("base", "cand", "cand", "base")):
	"""A complete ABBA sample table over the frozen windows with fixed per-side counter values."""
	samples = []
	for rep in range(reps):
		for label, _, _, ops in events.WORKLOADS:
			for subject in order:
				counters = events.parse(perf_text(group, (base if subject == "base" else cand) or {}), group)
				samples.append({"group": group, "rep": rep, "workload": label, "subject": subject, "counters": counters,
					"metrics": events.metrics(group, counters, ops)})
	return samples


def reference_like(instr_change=-0.007, cycle_change=0.083):
	return {label: {"base": {"instructions": 1.0e9, "cycles": 5.0e8}, "cand": {"instructions": 1.0e9 * (1 + instr_change), "cycles": 5.0e8 * (1 + cycle_change)},
		"instructions_change": instr_change, "cycles_change": cycle_change} for label, *_ in events.WORKLOADS}


def summary_like(ref, scale_instr=(1, 1), scale_cycles=(1, 1)):
	out = {}
	for label, r in ref.items():
		b = {"instructions": r["base"]["instructions"] * scale_instr[0], "cycles": r["base"]["cycles"] * scale_cycles[0]}
		c = {"instructions": r["cand"]["instructions"] * scale_instr[1], "cycles": r["cand"]["cycles"] * scale_cycles[1]}
		out[label] = {"base": b, "cand": c, "instructions_change": c["instructions"] / b["instructions"] - 1, "cycles_change": c["cycles"] / b["cycles"] - 1}
	return out


def main(out):
	out = pathlib.Path(out).resolve()
	out.mkdir(parents=True, exist_ok=False)

	@control("G1-frozen-groups-and-argv")
	def _():
		assert list(events.GROUPS) == ["R", "A", "B", "C", "D", "E"] and events.REQUIRED == "R"
		got = {}
		for group in events.GROUPS:
			argv = events.perf_argv(group)
			spec = argv[argv.index("-e") + 1]
			assert argv[:4] == ["perf", "stat", "-j", "--no-scale"] and argv[-1] == "--", argv
			assert spec.startswith("{") and spec.endswith("}:D"), spec  # one strong, pinned group
			members = spec[1:-3].split(",name=")
			assert "cpu_atom" not in spec and spec.count("cpu_core/") == len(events.GROUPS[group]["hardware"]) and spec.count("/u") == spec.count("cpu_core/")
			assert "--metric-no-group" not in argv and "-W" not in argv and "--weak" not in " ".join(argv) and ":W" not in spec
			assert "instructions" in spec and "cycles" in spec
			got[group] = argv
		assert events.GROUPS["B"]["hardware"][0].startswith("cpu_core/slots,")  # slots leads its group
		assert [w[0] for w in events.WORKLOADS] == ["run-numeric", "run-range_signed", "run-range_negative", "run-fib", "run-calls", "run-while", "run-empty"]
		return got

	@control("P1-parser-accepts-each-frozen-group")
	def _():
		return {g: sorted(events.parse(perf_text(g), g)) for g in events.GROUPS}

	@control("P1-absent-extra-duplicate-counter")
	def _():
		dup = json.dumps({"counter-value": "1.0", "unit": "", "event": "cycles", "event-runtime": 100, "pcnt-running": 100.0})
		extra = json.dumps({"counter-value": "1.0", "unit": "", "event": "cache-misses", "event-runtime": 100, "pcnt-running": 100.0})
		return {"absent": refused(lambda: events.parse(perf_text("C", drop=["br_misp_retired_all"]), "C")),
			"absent-anchor": refused(lambda: events.parse(perf_text("R", drop=["cycles"]), "R")),
			"extra": refused(lambda: events.parse(perf_text("R", extra=[extra]), "R")),
			"duplicate": refused(lambda: events.parse(perf_text("R", extra=[dup]), "R")),
			"other-group-member": refused(lambda: events.parse(perf_text("C"), "R"))}

	@control("P1-non-finite-negative-not-counted")
	def _():
		got = {}
		for name, value in (("nan", "nan"), ("inf", "inf"), ("negative", "-1.0"), ("not-counted", "<not counted>"), ("not-supported", "<not supported>")):
			got[name] = refused(lambda: events.parse(perf_text("R", override={"cycles": {"counter-value": value}}), "R"))
		got["zero-anchor"] = refused(lambda: events.parse(perf_text("R", {"instructions": 0.0}), "R"))
		return got

	@control("P1-running-below-100-and-scaling")
	def _():
		return {"99.9": refused(lambda: events.parse(perf_text("D", running=99.9), "D")),
			"missing": refused(lambda: events.parse(perf_text("R", override={"cycles": {"pcnt-running": None}}), "R")),
			"enabled-differs-from-running": refused(lambda: events.parse(perf_text("R", override={"cycles": {"event-enabled": 101}}), "R"))}

	@control("P1-runtime-and-units")
	def _():
		got = {}
		for name, change in (("runtime-missing", {"event-runtime": None}), ("runtime-nan", {"event-runtime": float("nan")}),
				("runtime-negative", {"event-runtime": -1}), ("runtime-zero", {"event-runtime": 0}), ("runtime-string", {"event-runtime": "100"}),
				("runtime-bool", {"event-runtime": True}), ("enabled-nan", {"event-enabled": float("nan")}), ("enabled-negative", {"event-enabled": -1}),
				("hardware-unit", {"unit": "msec"}), ("running-bool", {"pcnt-running": True})):
			got[name] = refused(lambda: events.parse(perf_text("R", override={"cycles": change}), "R"))
		text = perf_text("R").replace('"event-runtime": 100, ', "", 1)  # the field absent altogether on one row
		assert '"event-runtime"' in text
		got["runtime-field-absent"] = refused(lambda: events.parse(text, "R"))
		for name, change in (("task-clock-bananas", {"unit": "bananas"}), ("task-clock-empty-unit", {"unit": ""}), ("task-clock-runtime-nan", {"event-runtime": float("nan")})):
			got[name] = refused(lambda: events.parse(perf_text("A", override={"task_clock": change}), "A"))
		got["context-switch-unit"] = refused(lambda: events.parse(perf_text("A", override={"context_switches": {"unit": "msec"}}), "A"))
		assert events.parse(perf_text("A", override={"cycles": {"event-enabled": 100}}), "A")["cycles"] > 0  # equal enabled time accepted
		return got

	@control("P1-retained-discovery-rows-pass-the-repaired-parser")
	def _():
		rows = [json.loads(l) for l in (events.DISCOVERY / "raw.jsonl").read_text().splitlines()]
		assert len(rows) == 12 and [r["group"] for r in rows] == [g for g in events.GROUPS for _ in range(2)]
		for r in rows:
			events.lifecycle(r)
			assert r["status"] == 0 and r["stdout"] == events.PROBE_STDOUT and r["argv"] == events.perf_argv(r["group"]) + events.PROBE
			events.parse(r["stderr"], r["group"])
		return {"rows": len(rows), "sha256": events.sha(events.DISCOVERY / "raw.jsonl")}

	@control("P1-cpu-atom-counter-refused")
	def _():
		return {"all": refused(lambda: events.parse(perf_text("R", pmu="cpu_atom"), "R")),
			"one": refused(lambda: events.parse(perf_text("C", override={"br_misp_retired_all": {"pmu": "cpu_atom"}}), "C"))}

	@control("M1-topdown-units-and-sum")
	def _():
		good = events.metrics("B", events.parse(perf_text("B"), "B"), None)
		assert abs(sum(good[f"{k}_fraction"] for k in events.TOPDOWN) - 1) < 1e-9
		parse = lambda values: events.parse(perf_text("B", values), "B")
		return {"percentages-as-counts": refused(lambda: events.metrics("B", parse({"td_retiring": 50.0, "td_bad_spec": 10.0, "td_fe_bound": 20.0, "td_be_bound": 20.0}), None)),
			"sum-too-high": refused(lambda: events.metrics("B", parse({"td_be_bound": 0.7e9}), None)),
			"sum-too-low": refused(lambda: events.metrics("B", parse({"td_be_bound": 0.5e9}), None)),
			"fraction-above-one": refused(lambda: events.metrics("B", parse({"td_retiring": 3.1e9, "td_bad_spec": 0.0, "td_fe_bound": 0.0, "td_be_bound": 0.0}), None)),
			"zero-slots": refused(lambda: events.metrics("B", parse({"slots": 0.0}), None)),
			"within-rounding-accepted": events.metrics("B", parse({"td_be_bound": 0.65e9}), None)["td_be_bound_fraction"]}

	@control("M1-zero-denominators-are-undefined-not-zero")
	def _():
		c = events.metrics("C", events.parse(perf_text("C", {"br_inst_retired_all": 0.0, "br_misp_retired_all": 0.0}), "C"), 1_000_000)
		d = events.metrics("D", events.parse(perf_text("D", {"idq_dsb_uops": 0.0, "idq_mite_uops": 0.0}), "D"), None)
		a = events.metrics("A", events.parse(perf_text("A", {"ref_cycles": 0.0}), "A"), None)
		assert c["branch_miss_rate"] is None and d["dsb_share_of_dsb_plus_mite"] is None and a["cycles_per_ref_cycle"] is None
		samples = synthetic_samples("C", {"br_inst_retired_all": 0.0}, {"br_inst_retired_all": 0.0})
		q = events.summarize("C", samples)["run-numeric"]["quantities"]["branch_miss_rate"]
		assert "undefined" in q["status"] and "resolved" not in q
		return {"branch_miss_rate": c["branch_miss_rate"], "summary": q}

	@control("M1-cpu-migration-stops")
	def _():
		return refused(lambda: events.metrics("A", events.parse(perf_text("A", {"cpu_migrations": 1.0}), "A"), None))

	@control("S1-incomplete-or-misordered-abba")
	def _():
		full = synthetic_samples("R")
		events.summarize("R", full)
		missing = [s for s in full if not (s["workload"] == "run-fib" and s["rep"] == 4 and s["subject"] == "cand")]
		return {"missing-sample": refused(lambda: events.summarize("R", full[:-1])),
			"missing-side": refused(lambda: events.summarize("R", missing)),
			"four-repetitions": refused(lambda: events.summarize("R", synthetic_samples("R", reps=4))),
			"abab-order": refused(lambda: events.summarize("R", synthetic_samples("R", order=("base", "cand", "base", "cand")))),
			"missing-workload": refused(lambda: events.summarize("R", [s for s in full if s["workload"] != "run-while"]))}

	@control("S1-resolved-rule")
	def _():
		flat = events.summarize("R", synthetic_samples("R"))["run-numeric"]["quantities"]["cycles"]
		assert flat["resolved"] is False and flat["direction"] == "none"
		up = events.summarize("R", synthetic_samples("R", cand={"cycles": 5.5e8}))["run-numeric"]["quantities"]["cycles"]
		assert up["resolved"] is True and up["direction"] == "up" and all(c > 0 for c in up["paired_contrasts"])
		# A shift present in only four of five repetitions is not resolved, whatever its size.
		mixed = synthetic_samples("R", cand={"cycles": 5.5e8})
		for s in mixed:
			if s["rep"] == 2 and s["subject"] == "cand":
				s["counters"]["cycles"] = 4.9e8
		four = events.summarize("R", mixed)["run-numeric"]["quantities"]["cycles"]
		assert four["resolved"] is False
		# A consistent shift smaller than the base p10-p90 width is not resolved.
		noisy = synthetic_samples("R", cand={"cycles": 5.0e8 + 10})
		for i, s in enumerate(x for x in noisy if x["workload"] == "run-numeric" and x["subject"] == "base"):
			s["counters"]["cycles"] = 5.0e8 - 1000 * i
		for s in noisy:
			if s["workload"] == "run-numeric" and s["subject"] == "cand":
				s["counters"]["cycles"] = 5.0e8 + 500
		small = events.summarize("R", noisy)["run-numeric"]["quantities"]["cycles"]
		assert small["base_p10_p90_width"] > abs(small["difference"]) and small["resolved"] is False
		return {"flat": flat["resolved"], "consistent": up["resolved"], "four-of-five": four["resolved"], "inside-base-width": small["resolved"]}

	@control("A1-reproduction-tolerances-both-sides-and-boundaries")
	def _():
		ref = reference_like()
		assert events.anchor_check("R", summary_like(ref), ref) == []
		got = {}
		for name, kwargs, expect in (
				("instructions +2% both sides (boundary accepted)", {"scale_instr": (1.02, 1.02)}, False),
				("instructions -2% both sides (boundary accepted)", {"scale_instr": (0.98, 0.98)}, False),
				("instructions +2.01% base", {"scale_instr": (1.0201, 1.0201)}, True),
				("instructions -2.01% cand", {"scale_instr": (0.9799, 0.9799)}, True),
				("cycles +10% both sides (boundary accepted)", {"scale_cycles": (1.10, 1.10)}, False),
				("cycles -10% both sides (boundary accepted)", {"scale_cycles": (0.90, 0.90)}, False),
				("cycles +10.1% both", {"scale_cycles": (1.101, 1.101)}, True),
				("cycles -10.1% both", {"scale_cycles": (0.899, 0.899)}, True),
				("instruction change +0.51 pp", {"scale_instr": (1, 1 + 0.0051 / (1 - 0.007))}, True),
				("instruction change -0.51 pp", {"scale_instr": (1, 1 - 0.0051 / (1 - 0.007))}, True),
				("instruction change +0.49 pp accepted", {"scale_instr": (1, 1 + 0.0049 / (1 - 0.007))}, False),
				("cycle change +3.1 pp", {"scale_cycles": (1, 1 + 0.031 / 1.083)}, True),
				("cycle change -3.1 pp", {"scale_cycles": (1, 1 - 0.031 / 1.083)}, True),
				("cycle change +2.9 pp accepted", {"scale_cycles": (1, 1 + 0.029 / 1.083)}, False),
				("cycle excess disappears", {"scale_cycles": (1, 1 / 1.083)}, True)):
			bad = events.anchor_check("R", summary_like(ref, **kwargs), ref)
			assert bool(bad) is expect, (name, bad[:2])
			got[name] = len(bad)
		# run-empty: cycles and change exempt, instructions still anchored.
		s = summary_like(ref)
		s["run-empty"]["base"]["cycles"] *= 3
		s["run-empty"]["cycles_change"] = 9.0
		s["run-empty"]["instructions_change"] = 0.5
		assert events.anchor_check("R", s, ref) == []
		s["run-empty"]["cand"]["instructions"] *= 1.03
		assert [b[1:4] for b in events.anchor_check("R", s, ref)] == [("run-empty", "cand", "instructions")]
		got["run-empty cycles exempt, instructions anchored"] = True
		return got

	@control("V1-availability-content-validation")
	def _():
		ok = [{"eligible": True, "detail": "ok"}, {"eligible": True, "detail": "ok"}]
		groups = {g: {"argv": events.perf_argv(g), "eligible": g != "E", "checks": copy.deepcopy(ok) if g != "E" else [{"eligible": True, "detail": "ok"},
			{"eligible": False, "detail": "second open failed"}]} for g in events.GROUPS}
		good = {"status": "available", "order": ["R", "A", "B", "C", "D"], "groups": groups, "identity_sha256": "a" * 64,
			"primaries": {k: v[1] for k, v in events.PRIMARY.items()}}

		def load(change):
			m = copy.deepcopy(good)
			change(m)
			return events.validate_availability(m, "a" * 64)
		assert load(lambda m: None)["order"] == good["order"]
		spec = lambda m, g: m["groups"][g]["argv"].__setitem__(5, m["groups"][g]["argv"][5])
		return {"ineligible-group-in-order": refused(lambda: load(lambda m: m["order"].append("E"))),
			"eligible-group-dropped": refused(lambda: load(lambda m: m["order"].remove("D"))),
			"R-missing": refused(lambda: load(lambda m: m["order"].remove("R"))),
			"R-only": refused(lambda: load(lambda m: m.update(order=["R"]))),
			"reordered": refused(lambda: load(lambda m: m.update(order=["R", "C", "A", "B", "D"]))),
			"inconclusive-status": refused(lambda: load(lambda m: m.update(status="INCONCLUSIVE at discovery: no optional group available"))),
			"identity-hash-zeroed": refused(lambda: load(lambda m: m.update(identity_sha256="0" * 64))),
			"identity-hash-absent": refused(lambda: load(lambda m: m.pop("identity_sha256"))),
			"flag-disagrees-with-checks": refused(lambda: load(lambda m: m["groups"]["E"].update(eligible=True))),
			"eligible-flag-cleared": refused(lambda: load(lambda m: (m["groups"]["D"].update(eligible=False), m["order"].remove("D")))),
			"one-check-only": refused(lambda: load(lambda m: m["groups"]["C"]["checks"].pop())),
			"three-checks": refused(lambda: load(lambda m: m["groups"]["C"]["checks"].append({"eligible": True}))),
			"group-missing": refused(lambda: load(lambda m: m["groups"].pop("B"))),
			"R-ineligible": refused(lambda: load(lambda m: (m["groups"]["R"]["checks"][0].update(eligible=False), m["groups"]["R"].update(eligible=False)))),
			"weak-group-drift": refused(lambda: load(lambda m: m["groups"]["C"]["argv"].__setitem__(5, m["groups"]["C"]["argv"][5].replace("}:D", "}:W")))),
			"unpinned-drift": refused(lambda: load(lambda m: m["groups"]["A"]["argv"].__setitem__(5, m["groups"]["A"]["argv"][5].replace("}:D", "}")))),
			"scaling-drift": refused(lambda: load(lambda m: m["groups"]["R"]["argv"].remove("--no-scale"))),
			"atom-event-drift": refused(lambda: load(lambda m: m["groups"]["R"]["argv"].__setitem__(5, m["groups"]["R"]["argv"][5].replace("cpu_core/cpu-cycles", "cpu_atom/cpu-cycles")))),
			"drift-in-ineligible-group": refused(lambda: load(lambda m: m["groups"]["E"]["argv"].remove("--no-scale"))),
			"other-subjects": refused(lambda: load(lambda m: m["primaries"].update(cand="0" * 64)))}

	@control("V2-admission-binds-reviewed-bytes-and-current-host")
	def _():
		real_path = events.DISCOVERY / "availability.json"
		events.start_phase(120)
		m, admission = events.load_availability(real_path)  # the reviewed receipts on this host: admitted
		assert m["order"] == list(events.GROUPS) and admission["perf_version_receipt"]["status"] == 0
		got = {"admitted_order": m["order"], "fields": admission["identity_fields_compared"]}
		copy_dir = out / "copied-discovery"
		copy_dir.mkdir()
		for name in ("availability.json", "identity.json"):
			(copy_dir / name).write_bytes((events.DISCOVERY / name).read_bytes())
		got["same-bytes-other-path"] = refused(lambda: events.load_availability(copy_dir / "availability.json"))
		real = (events.AVAILABILITY_SHA256, events.IDENTITY_SHA256, events.current_identity, events.DISCOVERY)
		try:
			# Tampered bytes at the reviewed location (simulated by pointing DISCOVERY at a tampered copy).
			events.DISCOVERY = copy_dir
			doc = json.loads((copy_dir / "availability.json").read_text())
			doc["order"].remove("E")
			(copy_dir / "availability.json").write_text(json.dumps(doc, indent=1) + "\n")
			got["availability-bytes-changed"] = refused(lambda: events.load_availability(copy_dir / "availability.json"))
			(copy_dir / "availability.json").write_bytes(real_path.read_bytes())
			ident = json.loads((copy_dir / "identity.json").read_text())
			ident["kernel"] = "0.0.0"
			(copy_dir / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
			got["identity-bytes-changed"] = refused(lambda: events.load_availability(copy_dir / "availability.json"))
			(copy_dir / "identity.json").unlink()
			got["identity-receipt-missing"] = refused(lambda: events.load_availability(copy_dir / "availability.json"))
			events.DISCOVERY = real[3]
			# Pins alone are not validation: with the pins moved to tampered bytes, the content checks still refuse.
			events.DISCOVERY = copy_dir
			(copy_dir / "identity.json").write_bytes((real[3] / "identity.json").read_bytes())
			(copy_dir / "availability.json").write_text(json.dumps(doc, indent=1) + "\n")
			events.AVAILABILITY_SHA256 = events.sha(copy_dir / "availability.json")
			got["eligible-group-dropped-even-if-pinned"] = refused(lambda: events.load_availability(copy_dir / "availability.json"))
			events.DISCOVERY, events.AVAILABILITY_SHA256 = real[3], real[0]
			# Host drift at admission: each must stop before anything is staged.
			recorded = json.loads((real[3] / "identity.json").read_text())

			def drifted(change):
				now = copy.deepcopy(recorded)
				change(now)
				events.current_identity = lambda: (now, {"status": 0})
				return refused(lambda: events.load_availability(real_path))
			got["alias-drift"] = drifted(lambda i: i["cpu_core_event_aliases"].update({"ref-cycles": "event=0x00,umask=0x03"}))
			got["format-drift"] = drifted(lambda i: i["cpu_core_format"].update({"umask": "config:8-23"}))
			got["perf-version-drift"] = drifted(lambda i: i.update(perf="perf version 7.1.0"))
			got["kernel-drift"] = drifted(lambda i: i.update(kernel="7.0.0-32-generic"))
			got["cpu4-offline"] = drifted(lambda i: i.update(cpu4_online="0"))
			got["core-mask-drift"] = drifted(lambda i: i.update(cpu_core_cpus="0-3,6-15"))
			got["pmu-type-drift"] = drifted(lambda i: i.update(cpu_core_type="5"))
			got["microcode-drift"] = drifted(lambda i: i["cpu4"].update(microcode="0x134"))
			got["governor-drift"] = drifted(lambda i: i.update(cpu4_scaling_governor="performance"))
			got["watchdog-drift"] = drifted(lambda i: i.update(nmi_watchdog="0"))
			got["field-removed"] = drifted(lambda i: i.pop("cpu4_thread_siblings"))
			events.current_identity = real[2]
			# A failed perf --version is not an identity.
			real_run = events.run_bounded
			events.run_bounded = lambda argv, *a, **k: events.__dict__["_R"](argv)
			class R:
				def __init__(self, argv):
					self.returncode, self.stdout, self.timed_out, self.interrupted, self.reaped, self.survivors = 1, "", False, False, True, []
				def record(self):
					return {"status": 1}
			events._R = R
			try:
				got["perf-version-fails"] = refused(lambda: events.load_availability(real_path))
			finally:
				events.run_bounded = real_run
				del events._R
		finally:
			events.AVAILABILITY_SHA256, events.IDENTITY_SHA256, events.current_identity, events.DISCOVERY = real
		return got

	@control("D1-phase-deadline-kills-reaps-and-nothing-starts-after")
	def _():
		sink_path = out / "deadline.jsonl"
		sink = events.Sink(sink_path)
		real_pinned = events.pinned
		events.pinned = lambda: None
		try:
			events.start_phase(1.5)
			began = time.monotonic()
			row = events.run_sample(["/bin/sh", "-c", "sleep 60 & sleep 60"], sink, {"kind": "control-deadline"}, deadline=120)
			elapsed = time.monotonic() - began
			sink.write(row)
			assert row["timed_out"] and row["reaped"] is True and row["group_survivors"] == [] and elapsed < 20, (row, elapsed)
			stopped = refused(lambda: events.lifecycle(row))
			late = refused(lambda: events.run_sample(["/bin/true"], sink, {"kind": "control-after-deadline"}))
			assert len(sink_path.read_text().splitlines()) == 1  # the late command never started
			events.PHASE["deadline"] = None
			unset = refused(lambda: events.budget(1))
			events.start_phase(100)
			assert events.budget(120) <= 100 and events.budget(5) == 5
		finally:
			events.pinned = real_pinned
			events.PHASE["deadline"] = None
		return {"elapsed_s": round(elapsed, 2), "lifecycle": stopped, "after_deadline": late, "no_phase": unset}

	@control("B1-wrong-primary-or-source-refused")
	def _():
		events.bind_subjects()  # the retained pair and pinned manifest are intact
		got = {}
		real = dict(events.PRIMARY)
		try:
			events.PRIMARY["cand"] = ("p0-cand-primary", "0" * 64)
			got["wrong-hash"] = refused(events.bind_subjects)
			events.PRIMARY["cand"] = ("p0-base-primary", real["cand"][1])
			got["swapped-role"] = refused(events.bind_subjects)
			events.PRIMARY["cand"] = ("p0-cand-counter", real["cand"][1])
			got["counter-role"] = refused(events.bind_subjects)
		finally:
			events.PRIMARY.update(real)
		real_w = list(events.WORKLOADS)
		try:
			tmp = out / "numeric.rn"
			tmp.write_text("pub fn main() { 4 }\n")
			events.WORKLOADS[0] = ("run-numeric", ["run", str(tmp)], "3\n", 1_000_000)
			got["changed-source"] = refused(events.bind_subjects, (events.Stop, ValueError))
		finally:
			events.WORKLOADS[:] = real_w
		real_s = events.SUBJECTS_JSON
		try:
			events.SUBJECTS_JSON = (real_s[0], "1" * 64)
			got["wrong-manifest-pin"] = refused(events.bind_subjects)
		finally:
			events.SUBJECTS_JSON = real_s
		ref = events.references()
		assert [w[3] for w in events.WORKLOADS] == [1_000_000, 1_000_000, 1_000_000, 635_621, 1_000_000, 1_000_000, None]
		got["0179 cycle changes"] = {k: round(v["cycles_change"], 4) for k, v in ref.items()}
		return got

	def mocked_official(name, make_row):
		"""Run events.official with sampling, staging and affinity mocked; returns (exception or None, report)."""
		groups = {g: {"argv": events.perf_argv(g), "eligible": g in ("R", "A"), "checks": []} for g in events.GROUPS}
		avail = out / f"availability-{name}.json"
		avail.write_text(json.dumps({"status": "available", "order": ["R", "A"], "groups": groups, "primaries": {k: v[1] for k, v in events.PRIMARY.items()}}))
		real = (events.run_sample, events.stage, events.sha, events.pinned, events.os.sched_setaffinity)
		real_load = events.load_availability
		events.load_availability = lambda path: (json.loads(pathlib.Path(path).read_text()), {"mocked": True})
		state = {"subject": None}

		def fake_stage(side):
			state["subject"] = side
			return events.PRIMARY[side][1]
		events.stage, events.pinned, events.os.sched_setaffinity = fake_stage, (lambda: None), (lambda *a: None)
		real_sha = events.sha
		events.sha = lambda p: events.PRIMARY[state["subject"]][1] if pathlib.Path(p) == events.STAGE else real_sha(p)
		events.run_sample = lambda argv, sink, meta, deadline=120: make_row(meta, state)
		target, error = out / f"official-{name}", None
		try:
			events.official(target, avail)
		except BaseException as e:
			error = e
		finally:
			events.run_sample, events.stage, events.sha, events.pinned, events.os.sched_setaffinity = real
			events.load_availability = real_load
			events.PHASE["deadline"] = None
		return error, json.loads((target / "official.json").read_text()), target

	def row_for(ref, outputs, scale=None, fail_at=None):
		count = {"n": 0}

		def make(meta, state):
			count["n"] += 1
			label, side, group = meta["workload"], meta["subject"], meta["group"]
			values = dict(ref[label][side])
			if scale:
				values = scale(group, label, side, values)
			if fail_at and count["n"] == fail_at:
				return {**meta, "argv": ["mock"], "status": 0, "stdout": outputs[label], "stderr": "", "timed_out": False, "interrupted": False,
					"reaped": True, "group_survivors": [123456]}
			return {**meta, "argv": ["mock"], "status": 0, "stdout": outputs[label], "stderr": perf_text(group, values), "timed_out": False,
				"interrupted": False, "reaped": True, "group_survivors": []}
		return make

	@control("O1-reproducing-run-completes-both-groups")
	def _():
		ref, outputs = events.references(), events.expected_stdout()
		error, report, target = mocked_official("complete", row_for(ref, outputs))
		assert error is None and report["status"] == "complete" and list(report["groups"]) == ["R", "A"], (error, report["status"])
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()]
		assert len(rows) == 2 * 5 * 7 * 4 and all(not g["anchor_failures"] for g in report["groups"].values())
		return {"rows": len(rows), "status": report["status"]}

	@control("O1-nonreproduction-is-a-completed-outcome-and-stops-later-groups")
	def _():
		ref, outputs = events.references(), events.expected_stdout()

		def vanish(group, label, side, values):  # the candidate's excess cycles disappear
			if side == "cand" and label != "run-empty":
				values["cycles"] = ref[label]["base"]["cycles"]
			return values
		error, report, target = mocked_official("nonreproducing", row_for(ref, outputs, scale=vanish))
		assert error is None and report["status"] == "NONREPRODUCING / STOP" and list(report["groups"]) == ["R"], (error, report["status"])
		assert report["groups"]["R"]["anchor_failures"] and "failure" not in report
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()]
		assert len(rows) == 5 * 7 * 4 and {r["group"] for r in rows} == {"R"}  # group A never started
		return {"status": report["status"], "first_failures": report["groups"]["R"]["anchor_failures"][:2], "rows": len(rows)}

	@control("O1-infrastructure-failure-stops-with-partial-retained")
	def _():
		ref, outputs = events.references(), events.expected_stdout()
		error, report, target = mocked_official("infrastructure", row_for(ref, outputs, fail_at=11))
		assert isinstance(error, events.Stop) and report["status"].startswith("STOPPED") and "nonreproduction" not in report, (error, report["status"])
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()]
		assert len(rows) == 11 and rows[-1]["group_survivors"] == [123456]  # the failing raw row was retained first
		wrong = row_for(ref, outputs)
		error2, report2, _ = mocked_official("wrong-output", lambda meta, state: {**wrong(meta, state), "stdout": "4\n"})
		assert isinstance(error2, events.Stop) and report2["status"].startswith("STOPPED")
		return {"survivor": repr(error)[:160], "wrong_output": repr(error2)[:160], "rows_retained": len(rows)}

	@control("O1-deadline-inside-official-stops-and-starts-nothing-later")
	def _():
		ref, outputs = events.references(), events.expected_stdout()
		normal = row_for(ref, outputs)
		calls = {"n": 0}

		def make(meta, state):
			calls["n"] += 1
			row = normal(meta, state)
			if calls["n"] == 7:  # the phase runs out while this child is running: killed, reaped, recorded as timed out
				events.PHASE["deadline"] = time.monotonic() - 1
				row.update(timed_out=True, status=-9)
			return row
		error, report, target = mocked_official("deadline", make)
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()]
		assert isinstance(error, events.Stop) and report["status"].startswith("STOPPED") and calls["n"] == 7 and len(rows) == 7, (error, calls, len(rows))
		assert rows[-1]["timed_out"] is True and "groups" in report and report["groups"] == {}
		# The phase already over before a sample: nothing is staged or run.
		calls["n"] = 0

		def expired(meta, state):
			calls["n"] += 1
			return normal(meta, state)
		real_start = events.start_phase
		events.start_phase = lambda seconds: events.PHASE.update(deadline=time.monotonic() - 1)
		try:
			error2, report2, target2 = mocked_official("deadline-before-first", expired)
		finally:
			events.start_phase = real_start
		assert isinstance(error2, events.Stop) and calls["n"] == 0 and report2["status"].startswith("STOPPED")
		return {"mid-run": repr(error)[:120], "rows": len(rows), "before-first": repr(error2)[:120]}

	@control("O1-sentinel-hit-overrides-a-complete-status")
	def _():
		ref, outputs = events.references(), events.expected_stdout()
		normal = row_for(ref, outputs)
		leak = lambda meta, state: {**normal(meta, state), "note": os.environ["RNX0179_SENTINEL"]} if meta["rep"] == 4 and meta["group"] == "A" else normal(meta, state)
		error, report, target = mocked_official("sentinel-complete", leak)
		assert isinstance(error, events.Stop) and report["status"] == "STOPPED (sentinel occurrence or scan failure)", (error, report["status"])
		assert report["status_before_scan"] == "complete" and report["sentinel_scan"]["occurrences"] > 0 and report["sentinel_scan"]["completed"] is True
		assert (target / "raw.jsonl").exists() and json.loads((target / "sentinel-scan.json").read_text())["occurrences"] > 0
		# On a failing run too: the scan still runs and its hit is recorded beside the original failure.
		failing = row_for(ref, outputs, fail_at=5)
		leak2 = lambda meta, state: {**failing(meta, state), "note": os.environ["RNX0179_SENTINEL"]}
		error2, report2, _ = mocked_official("sentinel-failure", leak2)
		assert isinstance(error2, events.Stop) and report2["status"] == "STOPPED (sentinel occurrence or scan failure)" and "failure" in report2
		# A scan that cannot complete is not a clean scan.
		real_scan = events.scan
		events.scan = lambda *a: (_ for _ in ()).throw(OSError("scan failed"))
		try:
			error3, report3, _ = mocked_official("scan-error", row_for(ref, outputs))
		finally:
			events.scan = real_scan
		assert isinstance(error3, events.Stop) and report3["sentinel_scan"]["completed"] is False and report3["status"].startswith("STOPPED (sentinel")
		clean_error, clean, _ = mocked_official("sentinel-clean", row_for(ref, outputs))
		assert clean_error is None and clean["status"] == "complete" and clean["sentinel_scan"] == {**clean["sentinel_scan"], "completed": True, "occurrences": 0}
		return {"complete-run-with-hit": report["status"], "failing-run-with-hit": report2["status"], "scan-error": report3["sentinel_scan"],
			"clean": clean["sentinel_scan"]}

	@control("R1-rehearsal-failure-path-needs-a-clean-status-1")
	def _():
		real = (events.run_sample, events.stage, events.pinned, events.os.sched_setaffinity, events.load_availability)
		events.stage, events.pinned, events.os.sched_setaffinity = (lambda side: events.PRIMARY[side][1]), (lambda: None), (lambda *a: None)
		events.load_availability = lambda path: ({"order": list(events.GROUPS)}, {"mocked": True})
		got = {}
		try:
			for name, change in (("timed-out", {"timed_out": True, "status": -9}), ("survivor", {"group_survivors": [123456]}), ("status-0", {"status": 0}),
					("status-2", {"status": 2}), ("clean-status-1", {})):
				def fake(argv, sink, meta, deadline=120, change=change):
					base = {**meta, "argv": argv, "stdout": "", "stderr": "", "timed_out": False, "interrupted": False, "reaped": True, "group_survivors": []}
					if meta["kind"] == "rehearsal-probe":
						return {**base, "status": 0, "stdout": events.PROBE_STDOUT, "stderr": perf_text("R")}
					return {**base, "status": 1, **change}
				events.run_sample = fake
				target = out / f"rehearsal-{name}"
				if name == "clean-status-1":
					events.rehearse(target, "unused")
					got[name] = json.loads((target / "rehearsal.json").read_text())["planned_samples"]
				else:
					got[name] = refused(lambda: events.rehearse(target, "unused"))
		finally:
			events.run_sample, events.stage, events.pinned, events.os.sched_setaffinity, events.load_availability = real
			events.PHASE["deadline"] = None
		return got

	@control("H1-host-gate")
	def _():
		good = {"cpu4": {"vendor_id": "GenuineIntel", "cpu family": "6", "model": "183"}, "cpu_core_cpus": "0-15"}
		events.host_gate(good)
		return {"other-model": refused(lambda: events.host_gate({**good, "cpu4": {**good["cpu4"], "model": "154"}})),
			"other-vendor": refused(lambda: events.host_gate({**good, "cpu4": {**good["cpu4"], "vendor_id": "AuthenticAMD"}})),
			"cpu4-is-atom": refused(lambda: events.host_gate({**good, "cpu_core_cpus": "0-3,8-15"}))}

	@control("X1-fake-secret-retention")
	def _():
		sentinel = events.new_sentinel()
		d = out / "secret"
		d.mkdir()
		(d / "clean.json").write_text(json.dumps({"env": events.E0}))
		assert events.scan(d, [sentinel]) == {}
		(d / "leak.json").write_text(json.dumps({"env": {"X": sentinel}}))
		hits = events.scan(d, [sentinel])
		assert list(hits.values()) == [1]
		(d / "leak.json").unlink()
		(d / "archive.xz").write_bytes(lzma.compress(json.dumps({"env": {"X": sentinel}}).encode()))
		packed = events.scan(d, [sentinel])
		# Found in the archive. The scanner searches the stored bytes and the decompressed stream; xz stores so short a
		# payload almost literally, so one marker can be counted in both. Any positive count is a hit.
		assert list(packed) == [str(d / "archive.xz")] and packed[str(d / "archive.xz")] >= 1, packed
		assert events.scan(d, ["0" * 32]) == {}
		(d / "archive.xz").unlink()
		assert sentinel not in json.dumps(events.E0)
		return {"clean": 0, "leak_detected": 1, "leak_in_xz_detected": 1}

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("event controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
