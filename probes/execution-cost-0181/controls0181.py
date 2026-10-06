"""rnx 0181 untimed controls (plan rnx d724cf7 section 6). Synthetic perf output and mocked sampling only: no subject
runs and no hardware event is opened. The only real processes are `perf --version` (identity) and, in the replayed
0180 control set, one `sleep` child for the deadline control.

	python3 probes/execution-cost-0181/controls0181.py OUT_DIR      # from the repository root

Part 1 replays 0180's reviewed control set unchanged (parser, units, 100% running, hashes, identity drift, output and
affinity, summary and anchor boundaries, compressed sentinel, scan error) against the pinned library.
Part 2 covers what 0181 adds: the classifier, independent-group stop policy, statuses, exact eligible order, the
per-group identity recheck, this record's availability validation and admission.
"""
import copy, json, os, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import events0181 as ev  # noqa: E402
import controls_events as c80  # noqa: E402  (0180's control helpers: perf_text, refused; found via ev's sys.path entry)

base, perf_text, refused = ev.base, c80.perf_text, c80.refused
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


DIAGNOSTIC_ROW = {"C": "br_misp_retired_all", "D": "icache_data_stalls", "E": "ld_blocks_store_forward"}


def main(out):
	out = pathlib.Path(out).resolve()
	out.mkdir(parents=True, exist_ok=False)

	@control("L0-replay-of-the-0180-control-set")
	def _():
		target = out / "replay-0180"
		r = subprocess.run([sys.executable, str(base.REPO / "probes/execution-cost-0180/controls_events.py"), str(target)], capture_output=True, text=True,
			env={"PATH": "/usr/bin:/bin", "HOME": "/home/me", "LANG": "C.UTF-8"}, cwd=str(base.REPO), timeout=600)
		(out / "replay-0180.out").write_text(r.stdout + r.stderr)
		got = json.loads((target / "controls.json").read_text())
		assert r.returncode == 0 and len(got) == 26 and all(v["pass"] for v in got.values()), (r.returncode, [k for k, v in got.items() if not v["pass"]])
		return {"controls": len(got), "all_pass": True, "library": ev.library_gate()}

	@control("G1-frozen-scope")
	def _():
		assert ev.ORDER == ["R", "C", "D", "E"] and ev.DIAGNOSTICS == ["C", "D", "E"] and "A" not in ev.GROUPS and "B" not in ev.GROUPS
		assert all(ev.GROUPS[g] is base.GROUPS[g] for g in ev.ORDER)  # the 0180 definitions themselves, not copies
		for g in ev.ORDER:
			spec = base.perf_argv(g)[5]
			assert spec.endswith("}:D") and "instructions" in spec and "cpu-cycles" in spec and "cpu_atom" not in spec
		return {g: base.perf_argv(g) for g in ev.ORDER}

	@control("C1-diagnostic-row-defects-are-group-local")
	def _():
		got = {}
		for g, name in DIAGNOSTIC_ROW.items():
			assert ev.classify(perf_text(g), g)[name] > 0
			extra = json.dumps({"counter-value": "1.0", "unit": "", "event": "cache-misses", "event-runtime": 100, "pcnt-running": 100.0})
			dup = json.dumps({"counter-value": "1.0", "unit": "", "event": name, "event-runtime": 100, "pcnt-running": 100.0})
			cases = {"missing": perf_text(g, drop=[name]), "duplicate": perf_text(g, extra=[dup]), "unexpected": perf_text(g, extra=[extra]),
				"nan": perf_text(g, override={name: {"counter-value": "nan"}}), "negative": perf_text(g, override={name: {"counter-value": "-1.0"}}),
				"not-counted": perf_text(g, override={name: {"counter-value": "<not counted>"}}),
				"not-supported": perf_text(g, override={name: {"counter-value": "<not supported>"}}),
				"unit": perf_text(g, override={name: {"unit": "msec"}}), "runtime-missing": perf_text(g, override={name: {"event-runtime": None}}),
				"runtime-negative": perf_text(g, override={name: {"event-runtime": -1}}), "enabled-differs": perf_text(g, override={name: {"event-enabled": 101}}),
				"running-99.9": perf_text(g, override={name: {"pcnt-running": 99.9}})}
			for case, text in cases.items():
				got[f"{g}-{case}"] = refused(lambda: ev.classify(text, g), ev.LocalInvalid)[:120]
		return got

	@control("C1-anchor-defects-are-global-in-every-group")
	def _():
		got = {}
		for g in ev.ORDER:
			for anchor in ("instructions", "cycles"):
				dup = json.dumps({"counter-value": "1.0", "unit": "", "event": anchor, "event-runtime": 100, "pcnt-running": 100.0})
				cases = {"missing": perf_text(g, drop=[anchor]), "duplicate": perf_text(g, extra=[dup]), "nan": perf_text(g, override={anchor: {"counter-value": "nan"}}),
					"zero": perf_text(g, {anchor: 0.0}), "not-counted": perf_text(g, override={anchor: {"counter-value": "<not counted>"}}),
					"unit": perf_text(g, override={anchor: {"unit": "msec"}}), "runtime-nan": perf_text(g, override={anchor: {"event-runtime": float("nan")}}),
					"running-99.9": perf_text(g, override={anchor: {"pcnt-running": 99.9}})}
				for case, text in cases.items():
					got[f"{g}-{anchor}-{case}"] = refused(lambda: ev.classify(text, g), ev.Stop)[:60]
		# An anchor defect takes precedence over a diagnostic defect in the same sample.
		both = perf_text("C", override={"cycles": {"pcnt-running": 99.9}, "br_misp_retired_all": {"counter-value": "nan"}})
		got["anchor-and-diagnostic-defect"] = refused(lambda: ev.classify(both, "C"), ev.Stop)[:60]
		return {"cases": len(got), "sample": dict(list(got.items())[:3])}

	@control("C1-malformed-or-unclassified-is-global")
	def _():
		got = {}
		for g in ev.ORDER:
			got[f"{g}-malformed-json"] = refused(lambda: ev.classify(perf_text(g) + '{"counter-value": \n', g), ev.Stop)[:60]
			got[f"{g}-object-without-event"] = refused(lambda: ev.classify(perf_text(g) + "{}\n", g), ev.Stop)[:60]
			got[f"{g}-event-not-a-string"] = refused(lambda: ev.classify(perf_text(g) + '{"event": 7, "counter-value": "1.0"}\n', g), ev.Stop)[:60]
			got[f"{g}-metric-only-row"] = refused(lambda: ev.classify(perf_text(g) + '{"metric-value": "1.0", "metric-unit": "insn per cycle"}\n', g), ev.Stop)[:60]
		extra = json.dumps({"counter-value": "1.0", "unit": "", "event": "cache-misses", "event-runtime": 100, "pcnt-running": 100.0})
		got["R-unexpected-row-is-global"] = refused(lambda: ev.classify(perf_text("R", extra=[extra]), "R"), ev.Stop)[:60]
		got["R-diagnostic-rows-present-is-global"] = refused(lambda: ev.classify(perf_text("C"), "R"), ev.Stop)[:60]
		return got

	@control("C1-zero-denominator-is-undefined-not-a-failure")
	def _():
		c = ev.classify(perf_text("C", {"br_inst_retired_all": 0.0, "br_misp_retired_all": 0.0}), "C")
		d = ev.classify(perf_text("D", {"idq_dsb_uops": 0.0, "idq_mite_uops": 0.0, "icache_data_stalls": 0.0}), "D")
		e = ev.classify(perf_text("E", {"mem_load_retired_l1_miss": 0.0, "ld_blocks_store_forward": 0.0}), "E")
		m = (base.metrics("C", c, 1_000_000), base.metrics("D", d, None), base.metrics("E", e, 1_000_000))
		assert m[0]["branch_miss_rate"] is None and m[1]["dsb_share_of_dsb_plus_mite"] is None and m[2]["store_forward_blocks_per_instruction"] == 0
		return {"branch_miss_rate": m[0]["branch_miss_rate"], "dsb_share": m[1]["dsb_share_of_dsb_plus_mite"]}

	# ---- mocked official runs -------------------------------------------------------------------------------------
	ref, outputs = base.references(), base.expected_stdout()

	def mocked(name, make_row, order=("R", "C", "D", "E"), identity=None):
		"""events0181.official with sampling, staging, affinity, admission and identity mocked. Returns
		(error or None, report, rows). make_row(meta, n) -> raw row; identity(n_groups_started) may raise Stop."""
		real = (base.run_sample, base.stage, base.sha, base.pinned, base.os.sched_setaffinity, ev.load_availability, ev.recheck_identity)
		state = {"subject": None, "n": 0, "groups": 0}

		def fake_stage(side):
			state["subject"] = side
			return base.PRIMARY[side][1]

		def fake_run(argv, sink, meta, deadline=120):
			state["n"] += 1
			row = make_row(meta, state["n"])
			state["after"] = row.pop("_stage_hash_after", None)  # lets a control change the staged file under a sample
			return row

		def fake_recheck(recorded):
			state["groups"] += 1
			if identity:
				identity(state["groups"])
			return {"status": 0, "mocked": True}
		real_sha = base.sha
		base.run_sample, base.stage, base.pinned, base.os.sched_setaffinity = fake_run, fake_stage, (lambda: None), (lambda *a: None)
		base.sha = lambda p: (state.get("after") or base.PRIMARY[state["subject"]][1]) if pathlib.Path(p) == base.STAGE else real_sha(p)
		ev.load_availability = lambda path: ({"order": list(order)}, {}, {"mocked": True})
		ev.recheck_identity = fake_recheck
		target, error = out / f"official-{name}", None
		try:
			ev.official(target, "unused")
		except BaseException as e:
			error = e
		finally:
			base.run_sample, base.stage, base.sha, base.pinned, base.os.sched_setaffinity, ev.load_availability, ev.recheck_identity = real
			base.PHASE["deadline"] = None
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()] if (target / "raw.jsonl").exists() else []
		return error, json.loads((target / "official.json").read_text()), rows

	def good(meta, override=None, values=None, **row_changes):
		label, side, group = meta["workload"], meta["subject"], meta["group"]
		v = dict(ref[label][side])
		v.update(values or {})
		return {**meta, "argv": ["mock"], "status": 0, "stdout": outputs[label], "stderr": perf_text(group, v, override=override), "timed_out": False,
			"interrupted": False, "reaped": True, "group_survivors": [], **row_changes}

	def per_group(rows):
		return {g: sum(1 for r in rows if r["group"] == g) for g in ev.ORDER if any(r["group"] == g for r in rows)}

	@control("O1-all-groups-complete")
	def _():
		error, report, rows = mocked("complete", lambda meta, n: good(meta))
		assert error is None and report["status"] == "COMPLETE" and per_group(rows) == {"R": 140, "C": 140, "D": 140, "E": 140}, (error, report["status"])
		assert all(report["groups"][g]["status"] == "complete" and not report["groups"][g]["anchor_failures"] for g in ev.ORDER)
		assert report["failed_groups"] == [] and report["complete_diagnostics"] == ["C", "D", "E"]
		return {"rows": len(rows), "status": report["status"]}

	@control("O1-local-failure-invalidates-only-its-group-no-retry")
	def _():
		got = {}
		for g, name in DIAGNOSTIC_ROW.items():
			seen = {"n": 0}

			def make(meta, n, g=g, name=name):
				if meta["group"] == g:
					seen["n"] += 1
					if seen["n"] == 37:
						return good(meta, override={name: {"pcnt-running": 99.9}})
				return good(meta)
			error, report, rows = mocked(f"local-{g}", make)
			want = {x: (37 if x == g else 140) for x in ev.ORDER}
			assert error is None and report["status"] == "PARTIAL COUNTER-VALIDITY STOP" and per_group(rows) == want, (g, error, report["status"], per_group(rows))
			grp = report["groups"][g]
			assert grp["status"].startswith("FAILED / INCOMPLETE") and grp["rows_retained"] == 37 and "summary" not in grp and "anchor_failures" not in grp
			assert report["failed_groups"] == [g] and report["complete_diagnostics"] == [x for x in ev.DIAGNOSTICS if x != g]
			assert all(report["groups"][x]["status"] == "complete" for x in ev.ORDER if x != g)
			assert json.loads(rows[sum(want[x] for x in ev.ORDER[:ev.ORDER.index(g)]) + 36]["stderr"].splitlines()[-1])["pcnt-running"] == 99.9  # the failing raw row is retained
			got[g] = {"rows": per_group(rows), "failing": grp["failing_sample"]}
		return got

	@control("O1-every-diagnostic-failed-is-partial-with-no-conclusion")
	def _():
		def make(meta, n):
			g = meta["group"]
			return good(meta, override={DIAGNOSTIC_ROW[g]: {"counter-value": "<not counted>"}}) if g != "R" else good(meta)
		error, report, rows = mocked("all-failed", make)
		assert error is None and report["status"] == "PARTIAL COUNTER-VALIDITY STOP" and per_group(rows) == {"R": 140, "C": 1, "D": 1, "E": 1}
		assert report["complete_diagnostics"] == [] and "no mechanism conclusion" in report["note"]
		return {"rows": per_group(rows), "note": report["note"]}

	@control("O1-invalid-anchor-in-a-diagnostic-is-global")
	def _():
		seen = {"n": 0}

		def make(meta, n):
			if meta["group"] == "D":
				seen["n"] += 1
				if seen["n"] == 9:
					return good(meta, override={"cycles": {"counter-value": "<not counted>"}})
			return good(meta)
		error, report, rows = mocked("anchor-in-D", make)
		assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP (infrastructure") and per_group(rows) == {"R": 140, "C": 140, "D": 9}, (error, per_group(rows))
		assert "D" not in report["groups"] and "E" not in report["groups"] and "invalid anchor counter" in report["failure"]
		return {"rows": per_group(rows), "failure": report["failure"][:120]}

	@control("O1-R-failures-are-all-global")
	def _():
		got = {}
		extra = json.dumps({"counter-value": "1.0", "unit": "", "event": "cache-misses", "event-runtime": 100, "pcnt-running": 100.0})
		for name, change in (("anchor-99.9", {"override": {"cycles": {"pcnt-running": 99.9}}}), ("survivor", {"group_survivors": [123456]}), ("status-1", {"status": 1}),
				("wrong-output", {"stdout": "nope\n"}), ("timed-out", {"timed_out": True})):
			error, report, rows = mocked(f"R-{name}", lambda meta, n, change=change: good(meta, **change) if n == 5 else good(meta))
			assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP") and per_group(rows) == {"R": 5} and report["groups"] == {}, (name, error)
			got[name] = report["status"]

		def unexpected(meta, n):
			row = good(meta)
			if n == 5:
				row["stderr"] += extra + "\n"
			return row
		error, report, rows = mocked("R-unexpected-row", unexpected)
		assert isinstance(error, ev.Stop) and per_group(rows) == {"R": 5}
		got["unexpected-row"] = report["status"]
		return got

	@control("O1-nonreproduction-stops-globally")
	def _():
		got = {}
		for g in ev.ORDER:
			def make(meta, n, g=g):
				label, side = meta["workload"], meta["subject"]
				if meta["group"] == g and side == "cand" and label != "run-empty":
					return good(meta, values={"cycles": ref[label]["base"]["cycles"]})  # the excess disappears in this group
				return good(meta)
			error, report, rows = mocked(f"nonreproducing-{g}", make)
			index = ev.ORDER.index(g)
			assert error is None and report["status"] == "GLOBAL STOP (NONREPRODUCING)" and per_group(rows) == {x: 140 for x in ev.ORDER[:index + 1]}, (g, error, report["status"])
			assert report["groups"][g]["status"] == "NONREPRODUCING" and report["groups"][g]["anchor_failures"] and list(report["groups"]) == ev.ORDER[:index + 1]
			got[g] = per_group(rows)
		return got

	@control("O1-global-safety-failure-in-a-diagnostic-stops-everything")
	def _():
		got = {}
		for name, change in (("survivor", {"group_survivors": [123456]}), ("unreaped", {"reaped": False}), ("status-1", {"status": 1}), ("wrong-output", {"stdout": "4\n"}),
				("interrupted", {"interrupted": True}), ("stage-changed-during-sample", {"_stage_hash_after": "0" * 64})):
			seen = {"n": 0}

			def make(meta, n, change=change):
				if meta["group"] == "C":
					seen["n"] += 1
					if seen["n"] == 3:
						return good(meta, **change)
				return good(meta)
			error, report, rows = mocked(f"safety-{name}", make)
			assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP") and per_group(rows) == {"R": 140, "C": 3}, (name, error, per_group(rows))
			assert "C" not in report["groups"]
			got[name] = repr(error)[:80]
		return got

	@control("O1-deadline-starts-nothing-later")
	def _():
		def make(meta, n):
			row = good(meta)
			if n == 150:
				base.PHASE["deadline"] = time.monotonic() - 1
				row.update(timed_out=True, status=-9)
			return row
		error, report, rows = mocked("deadline", make)
		assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP") and per_group(rows) == {"R": 140, "C": 10}
		# The phase ends between two groups: the next group's first sample is never staged.
		def make2(meta, n):
			if n == 140:
				base.PHASE["deadline"] = time.monotonic() - 1
			return good(meta)
		error2, report2, rows2 = mocked("deadline-between-groups", make2)
		assert isinstance(error2, ev.Stop) and per_group(rows2) == {"R": 140} and list(report2["groups"]) == ["R"]
		return {"mid-group": per_group(rows), "between-groups": per_group(rows2)}

	@control("O1-identity-drift-before-a-group-stops-everything")
	def _():
		def drift(groups_started):
			if groups_started == 3:  # before D
				raise ev.Stop(("host identity differs from this record's discovery", {"kernel": ["a", "b"]}))
		error, report, rows = mocked("identity-drift", lambda meta, n: good(meta), identity=drift)
		assert isinstance(error, ev.Stop) and per_group(rows) == {"R": 140, "C": 140} and list(report["groups"]) == ["R", "C"], (error, per_group(rows))
		assert report["status"].startswith("GLOBAL STOP")
		return {"rows": per_group(rows), "status": report["status"]}

	@control("O1-only-the-eligible-order-runs")
	def _():
		error, report, rows = mocked("order-R-C-D", lambda meta, n: good(meta), order=("R", "C", "D"))
		assert error is None and report["status"] == "COMPLETE" and per_group(rows) == {"R": 140, "C": 140, "D": 140} and report["complete_diagnostics"] == ["C", "D"]
		error2, report2, rows2 = mocked("order-R-E", lambda meta, n: good(meta), order=("R", "E"))
		assert error2 is None and per_group(rows2) == {"R": 140, "E": 140}
		return {"R,C,D": per_group(rows), "R,E": per_group(rows2)}

	@control("O1-sentinel-hit-or-scan-error-overrides-complete-and-partial")
	def _():
		leak = lambda meta, n: {**good(meta), "note": os.environ["RNX0179_SENTINEL"]} if n == 500 else good(meta)
		error, report, _ = mocked("sentinel-complete", leak)
		assert isinstance(error, ev.Stop) and report["status"] == "GLOBAL STOP (sentinel occurrence or scan failure)" and report["status_before_scan"] == "COMPLETE"
		seen = {"n": 0}

		def partial_leak(meta, n):
			if meta["group"] == "C":
				seen["n"] += 1
				if seen["n"] == 2:
					return {**good(meta, override={"br_misp_retired_all": {"counter-value": "nan"}}), "note": os.environ["RNX0179_SENTINEL"]}
			return good(meta)
		error2, report2, _ = mocked("sentinel-partial", partial_leak)
		assert isinstance(error2, ev.Stop) and report2["status_before_scan"] == "PARTIAL COUNTER-VALIDITY STOP" and report2["status"].startswith("GLOBAL STOP (sentinel")
		real_scan = base.scan
		base.scan = lambda *a: (_ for _ in ()).throw(OSError("scan failed"))
		try:
			error3, report3, _ = mocked("scan-error", lambda meta, n: good(meta))
		finally:
			base.scan = real_scan
		assert isinstance(error3, ev.Stop) and report3["sentinel_scan"]["completed"] is False and report3["status"].startswith("GLOBAL STOP (sentinel")
		return {"complete": report["status"], "partial": report2["status"], "scan-error": report3["sentinel_scan"]}

	# ---- availability and admission -----------------------------------------------------------------------------
	ok = [{"eligible": True, "detail": "ok"}, {"eligible": True, "detail": "ok"}]

	def manifest(ineligible=()):
		groups = {g: {"argv": base.perf_argv(g), "eligible": g not in ineligible,
			"checks": copy.deepcopy(ok) if g not in ineligible else [{"eligible": True, "detail": "ok"}, {"eligible": False, "detail": "second open failed"}]}
			for g in ev.ORDER}
		return {"record": "0181", "status": "available", "order": [g for g in ev.ORDER if g not in ineligible], "groups": groups, "identity_sha256": "a" * 64,
			"primaries": {k: v[1] for k, v in base.PRIMARY.items()}, "libraries": dict(ev.LIBRARIES)}

	@control("V1-availability-content-validation")
	def _():
		def load(change, ineligible=("E",)):
			m = manifest(ineligible)
			change(m)
			return ev.validate_availability(m, "a" * 64)
		assert load(lambda m: None)["order"] == ["R", "C", "D"] and load(lambda m: None, ())["order"] == ev.ORDER
		swap = lambda m, g, a, b: m["groups"][g]["argv"].__setitem__(5, m["groups"][g]["argv"][5].replace(a, b))
		return {"ineligible-group-in-order": refused(lambda: load(lambda m: m["order"].append("E"))),
			"eligible-diagnostic-dropped": refused(lambda: load(lambda m: m["order"].remove("D"))),
			"R-missing": refused(lambda: load(lambda m: m["order"].remove("R"))),
			"R-only": refused(lambda: load(lambda m: m.update(order=["R"]), ("C", "D", "E"))),
			"reordered": refused(lambda: load(lambda m: m.update(order=["R", "D", "C"]))),
			"group-A-present": refused(lambda: load(lambda m: m["groups"].update(A={"argv": base.perf_argv("A"), "eligible": True, "checks": copy.deepcopy(ok)}))),
			"group-B-in-order": refused(lambda: load(lambda m: m["order"].insert(1, "B"))),
			"0180-manifest": refused(lambda: ev.validate_availability(json.loads((base.DISCOVERY / "availability.json").read_text()), base.IDENTITY_SHA256)),
			"other-record": refused(lambda: load(lambda m: m.update(record="0180"))),
			"inconclusive-status": refused(lambda: load(lambda m: m.update(status="INCONCLUSIVE at discovery: no diagnostic group available"))),
			"identity-hash-zeroed": refused(lambda: load(lambda m: m.update(identity_sha256="0" * 64))),
			"identity-hash-absent": refused(lambda: load(lambda m: m.pop("identity_sha256"))),
			"flag-disagrees-with-checks": refused(lambda: load(lambda m: m["groups"]["E"].update(eligible=True))),
			"one-check-only": refused(lambda: load(lambda m: m["groups"]["C"]["checks"].pop())),
			"three-checks": refused(lambda: load(lambda m: m["groups"]["C"]["checks"].append({"eligible": True}))),
			"group-missing": refused(lambda: load(lambda m: m["groups"].pop("D"))),
			"R-ineligible": refused(lambda: load(lambda m: None, ("R",))),
			"weak-group-drift": refused(lambda: load(lambda m: swap(m, "C", "}:D", "}:W"))),
			"unpinned-drift": refused(lambda: load(lambda m: swap(m, "D", "}:D", "}"))),
			"scaling-drift": refused(lambda: load(lambda m: m["groups"]["R"]["argv"].remove("--no-scale"))),
			"atom-event-drift": refused(lambda: load(lambda m: swap(m, "E", "cpu_core/cpu-cycles", "cpu_atom/cpu-cycles"))),
			"encoding-drift": refused(lambda: load(lambda m: swap(m, "C", "event=0xc5", "event=0xc6"))),
			"drift-in-ineligible-group": refused(lambda: load(lambda m: m["groups"]["E"]["argv"].remove("--no-scale"))),
			"other-subjects": refused(lambda: load(lambda m: m["primaries"].update(cand="0" * 64))),
			"other-libraries": refused(lambda: load(lambda m: m["libraries"].update({"probes/startup-0179/common.py": "0" * 64})))}

	@control("V2-admission-binds-reviewed-bytes-libraries-and-current-host")
	def _():
		real = (ev.DISCOVERY, ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256, ev.identity_now, dict(ev.LIBRARIES))
		got = {}
		d = out / "synthetic-discovery"
		d.mkdir()
		base.start_phase(300)
		try:
			ident, _ = base.current_identity()
			(d / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
			m = manifest(())
			m["identity_sha256"] = base.sha(d / "identity.json")
			(d / "availability.json").write_text(json.dumps(m, indent=1) + "\n")
			ev.DISCOVERY = d
			got["pins-not-frozen"] = refused(lambda: ev.load_availability(d / "availability.json"))
			ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256 = base.sha(d / "availability.json"), base.sha(d / "identity.json")
			admitted, recorded, admission = ev.load_availability(d / "availability.json")
			assert admitted["order"] == ev.ORDER and recorded == ident and admission["perf_version_receipt"]["status"] == 0
			got["admitted"] = admission["identity_fields_compared"]
			other = out / "elsewhere"
			other.mkdir()
			for name in ("availability.json", "identity.json"):
				(other / name).write_bytes((d / name).read_bytes())
			got["same-bytes-other-path"] = refused(lambda: ev.load_availability(other / "availability.json"))
			got["0180-receipts"] = refused(lambda: ev.load_availability(base.DISCOVERY / "availability.json"))
			pins = (ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256)
			tampered = manifest(())
			tampered["identity_sha256"] = pins[1]
			tampered["order"].remove("E")
			(d / "availability.json").write_text(json.dumps(tampered, indent=1) + "\n")
			got["availability-bytes-changed"] = refused(lambda: ev.load_availability(d / "availability.json"))
			ev.AVAILABILITY_SHA256 = base.sha(d / "availability.json")
			got["eligible-group-dropped-even-if-pinned"] = refused(lambda: ev.load_availability(d / "availability.json"))
			(d / "availability.json").write_text(json.dumps(m, indent=1) + "\n")
			ev.AVAILABILITY_SHA256 = pins[0]
			(d / "identity.json").write_text(json.dumps({**ident, "kernel": "0.0.0"}, indent=1) + "\n")
			got["identity-bytes-changed"] = refused(lambda: ev.load_availability(d / "availability.json"))
			(d / "identity.json").unlink()
			got["identity-receipt-missing"] = refused(lambda: ev.load_availability(d / "availability.json"))
			(d / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
			assert ev.load_availability(d / "availability.json")[0]["order"] == ev.ORDER  # restored: admitted again

			def drifted(change):
				now = copy.deepcopy(ident)
				change(now)
				ev.identity_now = lambda: (now, {"status": 0})
				try:
					return refused(lambda: ev.load_availability(d / "availability.json"))
				finally:
					ev.identity_now = real[3]
			got["alias-drift"] = drifted(lambda i: i["cpu_core_event_aliases"].update({"instructions": "event=0xc1"}))
			got["format-drift"] = drifted(lambda i: i["cpu_core_format"].update({"umask": "config:8-23"}))
			got["perf-version-drift"] = drifted(lambda i: i.update(perf="perf version 7.1.0"))
			got["kernel-drift"] = drifted(lambda i: i.update(kernel="7.0.0-32-generic"))
			got["microcode-drift"] = drifted(lambda i: i["cpu4"].update(microcode="0x134"))
			got["cpu4-offline"] = drifted(lambda i: i.update(cpu4_online="0"))
			got["core-mask-drift"] = drifted(lambda i: i.update(cpu_core_cpus="0-3,6-15"))
			got["governor-drift"] = drifted(lambda i: i.update(cpu4_scaling_governor="performance"))
			got["field-removed"] = drifted(lambda i: i.pop("nmi_watchdog"))
			ev.LIBRARIES["probes/execution-cost-0180/events.py"] = "0" * 64
			got["library-hash-mismatch"] = refused(lambda: ev.load_availability(d / "availability.json"))
		finally:
			ev.LIBRARIES.clear()
			ev.LIBRARIES.update(real[4])
			ev.DISCOVERY, ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256, ev.identity_now = real[:4]
			base.PHASE["deadline"] = None
		return got

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("0181 controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
