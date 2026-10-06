"""rnx 0183 untimed controls for the Stage A driver (plan rnx 17d6d5a section 3; audit 2d3a11b). Synthetic summaries
and mocked sampling only: no subject runs and no hardware event is opened. The only real processes are
`perf --version` (identity) and, inside the replayed 0181/0180 control sets, one `sleep` child.

	python3 probes/frontend-0183/controls0183.py OUT_DIR      # from the repository root

Mocked official runs write synthetic raw rows; after checking them this script keeps their count, per-group counts
and sha256 and removes the synthetic file. Real discovery, rehearsal and official rows are always retained.
"""
import copy, json, math, os, pathlib, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import events0183 as ev  # noqa: E402
import controls_events as c80  # noqa: E402  (0180's control helpers, found via the library path)

base, ev81, perf_text, refused = ev.base, ev.ev81, c80.perf_text, c80.refused
c80_default = {"dsb2mite_penalty_cycles": 1.0e6}
RESULTS = {}
ENV = {"PATH": "/usr/bin:/bin", "HOME": "/home/me", "LANG": "C.UTF-8"}


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


def text(group, values=None, **kw):
	"""Synthetic perf JSON for R or F1 (0180's helper does not know the F1 counter's default)."""
	return perf_text(group, {**c80_default, **(values or {})}, **kw)


def q(diff, resolved, direction=None):
	direction = direction or ("up" if diff > 0 else "down" if diff < 0 else "none")
	return {"difference": diff, "resolved": resolved, "direction": direction, "base_median": 1000.0, "cand_median": 1000.0 + diff}


def summary(per_window, default=(100.0, True, 1000.0, True)):
	"""F1-group summary: per window (D_f1, f1_resolved, D_cycles, cycles_resolved); unspecified windows get `default`."""
	out = {}
	for w in ev.SIGNAL + ev.CONTRAST + ev.REPORTED:
		df, fr, dc, cr = per_window.get(w, default)
		out[w] = {"quantities": {ev.F1_EVENT: q(df, fr), "cycles": q(dc, cr)}}
	return out


def same(spec):
	return {w: spec for w in ev.SIGNAL}


def main(out):
	out = pathlib.Path(out).resolve()
	out.mkdir(parents=True, exist_ok=False)

	@control("L0-replay-of-the-0181-control-set")
	def _():
		target = out / "replay-0181"
		r = subprocess.run([sys.executable, str(base.REPO / "probes/execution-cost-0181/controls0181.py"), str(target)], capture_output=True, text=True,
			env=ENV, cwd=str(base.REPO), timeout=900)
		(out / "replay-0181.out").write_text(r.stdout + r.stderr)
		got = json.loads((target / "controls.json").read_text())
		assert r.returncode == 0 and len(got) == 23 and all(v["pass"] for v in got.values()), (r.returncode, [k for k, v in got.items() if not v["pass"]])
		return {"controls": len(got), "all_pass": True, "libraries": ev.library_gate()}

	@control("L1-altered-library-is-refused-before-it-is-imported")
	def _():
		got = {}
		for name, victim in (("unaltered", None), *((rel.rsplit("/", 1)[1], rel) for rel in ev.LIBRARIES)):
			root = out / f"library-copy-{name}"
			for rel in ("probes/frontend-0183/events0183.py", *ev.LIBRARIES):
				(root / rel).parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(base.REPO / rel, root / rel)  # copies only: the reviewed originals are never modified
			marker = root / "IMPORTED-ALTERED-LIBRARY"
			if victim:
				with (root / victim).open("a") as f:
					f.write(f"\nopen({str(marker)!r}, 'w').write('executed')\n")
			r = subprocess.run([sys.executable, "-c", "import events0183; print('imported', events0183.ORDER)"], capture_output=True, text=True, env=ENV,
				cwd=str(root / "probes/frontend-0183"), timeout=120)
			if victim:
				assert r.returncode != 0 and "refusing to import" in r.stderr and victim in r.stderr and not marker.exists(), (name, r.returncode, r.stderr[-200:])
			else:
				assert r.returncode == 0 and "imported ['R', 'F1']" in r.stdout and not marker.exists(), (r.returncode, r.stderr[-300:])
			got[name] = {"status": r.returncode, "marker_executed": marker.exists()}
			shutil.rmtree(root)
		assert all(base.sha(base.REPO / rel) == want for rel, want in ev.LIBRARIES.items())
		return got

	@control("G1-frozen-scope-and-untouched-library-definitions")
	def _():
		assert ev.ORDER == ["R", "F1"] and ev.EXCLUDED == {"F2": "not collected (unavailable)", "F3": "not collected (unavailable)"}
		spec = base.perf_argv("F1")[5]
		assert spec == "{cpu_core/instructions,name=instructions/u,cpu_core/cpu-cycles,name=cycles/u,cpu_core/event=0x61,umask=0x02,name=dsb2mite_penalty_cycles/u}:D", spec
		assert base.perf_argv("F1")[:4] == ["perf", "stat", "-j", "--no-scale"] and "0xc6" not in json.dumps([base.perf_argv(g) for g in ev.ORDER])
		assert "frontend=" not in spec and "cpu_atom" not in spec
		# The six 0180 definitions are exactly what a fresh import of the pinned file defines.
		r = subprocess.run([sys.executable, "-c", "import json, events; print(json.dumps(events.GROUPS))"], capture_output=True, text=True, env=ENV,
			cwd=str(base.REPO / "probes/execution-cost-0180"), timeout=60)
		fresh = json.loads(r.stdout)
		assert list(fresh) == ["R", "A", "B", "C", "D", "E"] and all(base.GROUPS[g] == fresh[g] for g in fresh) and list(base.GROUPS) == [*fresh, "F1"]
		return {"F1": base.perf_argv("F1"), "library_groups_unchanged": True}

	@control("C1-F1-row-defects-are-group-local-and-anchor-defects-global")
	def _():
		assert ev81.classify(text("F1"), "F1")[ev.F1_EVENT] > 0
		got = {}
		for case, kw in (("not-counted", {"override": {ev.F1_EVENT: {"counter-value": "<not counted>"}}}), ("nan", {"override": {ev.F1_EVENT: {"counter-value": "nan"}}}),
				("negative", {"override": {ev.F1_EVENT: {"counter-value": "-1.0"}}}), ("missing", {"drop": [ev.F1_EVENT]}),
				("running-99.9", {"override": {ev.F1_EVENT: {"pcnt-running": 99.9}}}), ("unit", {"override": {ev.F1_EVENT: {"unit": "msec"}}}),
				("runtime-nan", {"override": {ev.F1_EVENT: {"event-runtime": float("nan")}}})):
			got[f"local-{case}"] = refused(lambda: ev81.classify(text("F1", **kw), "F1"), ev.LocalInvalid)[:80]
		for anchor in ("instructions", "cycles"):
			for case, kw in (("not-counted", {"override": {anchor: {"counter-value": "<not counted>"}}}), ("missing", {"drop": [anchor]}),
					("running-99.9", {"override": {anchor: {"pcnt-running": 99.9}}}), ("inf", {"override": {anchor: {"counter-value": "inf"}}})):
				got[f"global-{anchor}-{case}"] = refused(lambda: ev81.classify(text("F1", **kw), "F1"), ev.Stop)[:60]
		got["global-malformed"] = refused(lambda: ev81.classify(text("F1") + '{"counter-value": \n', "F1"), ev.Stop)[:60]
		got["global-eventless"] = refused(lambda: ev81.classify(text("F1") + "{}\n", "F1"), ev.Stop)[:60]
		got["global-anchor-wins"] = refused(lambda: ev81.classify(text("F1", override={"cycles": {"pcnt-running": 99.9}, ev.F1_EVENT: {"counter-value": "nan"}}), "F1"), ev.Stop)[:60]
		got["zero-count-is-valid"] = ev81.classify(text("F1", {ev.F1_EVENT: 0.0}), "F1")[ev.F1_EVENT]
		return got

	@control("S1-every-window-status-and-its-boundaries")
	def _():
		cases = {  # name: ((D_f1, f1_resolved, D_cycles, cycles_resolved), expected status, expected r or None)
			"strong r=0.6": ((600.0, True, 1000.0, True), "strong", 0.6), "strong at exactly 0.5": ((500.0, True, 1000.0, True), "strong", 0.5),
			"intermediate just below 0.5": ((499.0, True, 1000.0, True), "intermediate", 0.499), "intermediate just above 0.1": ((101.0, True, 1000.0, True), "intermediate", 0.101),
			"weak at exactly 0.1": ((100.0, True, 1000.0, True), "weak", 0.1), "weak r=0.05": ((50.0, True, 1000.0, True), "weak", 0.05),
			"weak unresolved positive": ((900.0, False, 1000.0, True), "weak", 0.9), "weak unresolved negative": ((-900.0, False, 1000.0, True), "weak", -0.9),
			"weak zero difference": ((0.0, False, 1000.0, True), "weak", 0.0),
			"contrary resolved down": ((-600.0, True, 1000.0, True), "contrary", None),
			"undefined cycles unresolved": ((600.0, True, 1000.0, False), "undefined", None),
			"undefined cycles resolved down": ((600.0, True, -1000.0, True), "undefined", None),
			"undefined precedes contrary": ((-600.0, True, 1000.0, False), "undefined", None)}
		got = {}
		for name, (spec, want, r) in cases.items():
			status, detail = ev.window_status("valid", summary({"run-numeric": spec})["run-numeric"]["quantities"])
			assert status == want, (name, status, want)
			if r is not None:
				assert detail["r"] == r, (name, detail["r"], r)
			else:
				assert "r" not in detail, (name, detail)
			got[name] = status
		assert ev.window_status("not collected (unavailable)", {})[0] == "unavailable" and ev.window_status("invalid", {})[0] == "failed"
		assert 500.0 / 1000.0 == 0.5 and 100.0 / 1000.0 == 0.1  # the boundary fixtures sit exactly on the thresholds in binary floating point
		return got

	@control("S1-malformed-or-non-finite-summaries-stop")
	def _():
		good = summary({})["run-numeric"]["quantities"]
		got = {"unknown-state": refused(lambda: ev.window_status("maybe", good))}
		for name, change in (("f1-missing", lambda s: s.pop(ev.F1_EVENT)), ("cycles-missing", lambda s: s.pop("cycles")),
				("f1-undefined-status", lambda s: s.update({ev.F1_EVENT: {"status": "undefined (zero denominator in at least one sample)"}})),
				("nan-difference", lambda s: s[ev.F1_EVENT].update(difference=math.nan)), ("inf-difference", lambda s: s["cycles"].update(difference=math.inf)),
				("bool-difference", lambda s: s["cycles"].update(difference=True)), ("string-difference", lambda s: s[ev.F1_EVENT].update(difference="600")),
				("resolved-missing", lambda s: s[ev.F1_EVENT].pop("resolved")),
				("resolved-string", lambda s: s[ev.F1_EVENT].update(resolved="true")), ("resolved-int", lambda s: s["cycles"].update(resolved=1)),
				("resolved-none", lambda s: s[ev.F1_EVENT].update(resolved=None)),
				("direction-sideways", lambda s: s[ev.F1_EVENT].update(direction="sideways")), ("direction-missing", lambda s: s["cycles"].pop("direction")),
				("positive-difference-direction-down", lambda s: s[ev.F1_EVENT].update(direction="down")),
				("negative-difference-direction-up", lambda s: s[ev.F1_EVENT].update(difference=-600.0, direction="up")),
				("zero-difference-direction-up", lambda s: s[ev.F1_EVENT].update(difference=0.0, direction="up", resolved=False)),
				("resolved-with-zero-difference", lambda s: s[ev.F1_EVENT].update(difference=0.0, direction="none", resolved=True)),
				("cycles-direction-contradicts", lambda s: s["cycles"].update(direction="down"))):
			s = copy.deepcopy(good)
			change(s)
			got[name] = refused(lambda: ev.window_status("valid", s))
		# The reviewer's three reproducers, which the first form classified as weak, weak and contrary.
		for name, bad in (("reproducer-resolved-string", {"difference": 600, "resolved": "true", "direction": "up"}),
				("reproducer-direction-sideways", {"difference": 600, "resolved": True, "direction": "sideways"}),
				("reproducer-positive-down", {"difference": 600, "resolved": True, "direction": "down"})):
			s = copy.deepcopy(good)
			s[ev.F1_EVENT] = bad
			got[name] = refused(lambda: ev.window_status("valid", s))
		# The same validation guards the contrast and reported windows before any flag or report is formed.
		for name, window, key, change in (("contrast-resolved-string", "run-while", ev.F1_EVENT, {"resolved": "true"}),
				("contrast-direction-contradicts", "run-empty", ev.F1_EVENT, {"direction": "down"}), ("contrast-cycles-nan", "run-while", "cycles", {"difference": math.nan}),
				("reported-direction-sideways", "run-fib", ev.F1_EVENT, {"direction": "sideways"}), ("reported-cycles-resolved-int", "run-calls", "cycles", {"resolved": 1}),
				("contrast-quantity-missing", "run-while", ev.F1_EVENT, None)):
			full = summary({})
			if change is None:
				full[window]["quantities"].pop(key)
			else:
				full[window]["quantities"][key].update(change)
			got[name] = refused(lambda: ev.stage_a("valid", full))
		assert ev.stage_a("valid", summary({}))["disposition"] == "A-weakened"  # the unmodified summary is accepted
		return got

	@control("S1-every-disposition-and-precedence")
	def _():
		strong, weak, inter, contrary = (600.0, True, 1000.0, True), (50.0, True, 1000.0, True), (300.0, True, 1000.0, True), (-600.0, True, 1000.0, True)
		undefined = (600.0, True, 1000.0, False)
		mix = lambda a, b, c: dict(zip(ev.SIGNAL, (a, b, c)))
		cases = {"all strong": (mix(strong, strong, strong), "A-strengthened"), "all weak": (mix(weak, weak, weak), "A-weakened"),
			"all contrary": (mix(contrary, contrary, contrary), "A-weakened"), "weak and contrary": (mix(weak, contrary, weak), "A-weakened"),
			"all intermediate": (mix(inter, inter, inter), "A-mixed"), "strong on two": (mix(strong, strong, weak), "A-mixed"),
			"strong on one": (mix(strong, weak, weak), "A-mixed"), "strong and contrary": (mix(strong, contrary, strong), "A-mixed"),
			"strong and intermediate": (mix(strong, inter, strong), "A-mixed"),
			"undefined on one beats strong": (mix(strong, undefined, strong), "A-failed"), "undefined on one beats weak": (mix(weak, weak, undefined), "A-failed"),
			"undefined on all": (mix(undefined, undefined, undefined), "A-failed")}
		got = {}
		for name, (spec, want) in cases.items():
			a = ev.stage_a("valid", summary(spec))
			assert a["disposition"] == want, (name, a["disposition"], want)
			got[name] = a["disposition"]
		failed, unavailable = ev.stage_a("invalid", None), ev.stage_a("not collected (unavailable)", None)
		assert failed["disposition"] == "A-failed" and all(v["status"] == "failed" for v in failed["signal_windows"].values())
		assert unavailable["disposition"] == "A-unavailable" and all(v["status"] == "unavailable" for v in unavailable["signal_windows"].values())
		assert failed["contrast_flag"] == {**failed["contrast_flag"], "windows": {}, "any": False}
		got.update({"F1 invalid": failed["disposition"], "F1 unavailable": unavailable["disposition"]})
		return got

	@control("S1-no-locating-event-under-every-disposition")
	def _():
		strong, weak = (600.0, True, 1000.0, True), (50.0, True, 1000.0, True)
		got = {}
		for name, a in (("strengthened", ev.stage_a("valid", summary(same(strong)))), ("weakened", ev.stage_a("valid", summary(same(weak)))),
				("mixed", ev.stage_a("valid", summary({ev.SIGNAL[0]: strong, ev.SIGNAL[1]: weak, ev.SIGNAL[2]: weak}))), ("failed", ev.stage_a("invalid", None)),
				("unavailable", ev.stage_a("not collected (unavailable)", None))):
			assert a["locating_event"] is None and a["stage_b_proposal_permitted"] is False and "closes at Stage A" in a["closure"], (name, a["closure"])
			assert a["collection_states"]["F2"] == a["collection_states"]["F3"] == "not collected (unavailable)"
			got[name] = a["disposition"]
		# The selection rule itself, exercised with states this record never produces.
		rule = {"F3 valid": ({"F2": "valid", "F3": "valid"}, "F3"), "F3 unavailable, F2 valid": ({"F2": "valid", "F3": "not collected (unavailable)"}, "F2"),
			"F3 invalid is not replaced by F2": ({"F2": "valid", "F3": "invalid"}, None), "both unavailable": (ev.EXCLUDED, None),
			"F3 unavailable, F2 invalid": ({"F2": "invalid", "F3": "not collected (unavailable)"}, None)}
		for name, (states, want) in rule.items():
			assert ev.locating_event(states) == want, (name, ev.locating_event(states))
			got[name] = want
		# With hypothetical valid F2/F3 states the selector names an event, but this driver never permits a Stage B
		# proposal and says that general eligibility is not implemented, under every disposition.
		for spec in (same(weak), same(strong), {ev.SIGNAL[0]: strong, ev.SIGNAL[1]: weak, ev.SIGNAL[2]: weak}):
			hypothetical = ev.stage_a("valid", summary(spec), states={"F2": "valid", "F3": "valid"})
			assert hypothetical["locating_event"] == "F3" and hypothetical["stage_b_proposal_permitted"] is False and "not implemented" in hypothetical["closure"]
		return got

	@control("S1-contrast-flag-thresholds")
	def _():
		sig = same((600.0, True, 1000.0, True))
		sig[ev.SIGNAL[2]] = (400.0, True, 1000.0, True)  # smallest signal difference is 400, so the threshold is 200
		got = {}
		for name, spec, want in (("at threshold", (200.0, True, 10.0, False), True), ("above", (201.0, True, 10.0, False), True), ("below", (199.0, True, 10.0, False), False),
				("large but unresolved", (5000.0, False, 10.0, False), False), ("resolved down", (-500.0, True, 10.0, False), False)):
			a = ev.stage_a("valid", summary({**sig, "run-while": spec, "run-empty": (0.0, False, 0.0, False)}))
			flag = a["contrast_flag"]
			assert flag["windows"]["run-while"]["flagged"] is want and flag["windows"]["run-while"]["threshold"] == 200.0 and flag["any"] is want, (name, flag)
			assert a["disposition"] == "A-mixed"  # the flag never changes the disposition
			got[name] = flag["windows"]["run-while"]["flagged"]
		both = ev.stage_a("valid", summary({**sig, "run-while": (300.0, True, 1.0, False), "run-empty": (250.0, True, 1.0, False)}))
		assert both["contrast_flag"]["any"] and all(v["flagged"] for v in both["contrast_flag"]["windows"].values())
		assert set(both["reported_windows"]) == set(ev.REPORTED)
		return got

	# ---- mocked official runs -------------------------------------------------------------------------------------
	ref, outputs = base.references(), base.expected_stdout()

	def mocked(name, make_row, identity=None):
		real = (base.run_sample, base.stage, base.sha, base.pinned, base.os.sched_setaffinity, ev.load_availability, ev81.recheck_identity)
		state = {"subject": None, "n": 0, "groups": 0}

		def fake_stage(side):
			state["subject"] = side
			return base.PRIMARY[side][1]

		def fake_run(argv, sink, meta, deadline=120):
			state["n"] += 1
			return make_row(meta, state["n"])

		def fake_recheck(recorded):
			state["groups"] += 1
			if identity:
				identity(state["groups"])
			return {"status": 0, "mocked": True}
		real_sha = base.sha
		base.run_sample, base.stage, base.pinned, base.os.sched_setaffinity = fake_run, fake_stage, (lambda: None), (lambda *a: None)
		base.sha = lambda p: base.PRIMARY[state["subject"]][1] if pathlib.Path(p) == base.STAGE else real_sha(p)
		ev.load_availability = lambda path: ({"order": list(ev.ORDER)}, {}, {"mocked": True})
		ev81.recheck_identity = fake_recheck
		target, error = out / f"official-{name}", None
		try:
			ev.official(target, "unused")
		except BaseException as e:
			error = e
		finally:
			base.run_sample, base.stage, base.sha, base.pinned, base.os.sched_setaffinity, ev.load_availability, ev81.recheck_identity = real
			base.PHASE["deadline"] = None
		rows = [json.loads(l) for l in (target / "raw.jsonl").read_text().splitlines()] if (target / "raw.jsonl").exists() else []
		counts = {g: sum(1 for r in rows if r["group"] == g) for g in ev.ORDER if any(r["group"] == g for r in rows)}
		if rows:
			(target / "raw.summary.json").write_text(json.dumps({"rows": len(rows), "per_group": counts, "sha256": base.sha(target / "raw.jsonl")}) + "\n")
			(target / "raw.jsonl").unlink()
		return error, json.loads((target / "official.json").read_text()), counts

	def good(meta, f1=None, override=None, **row_changes):
		label, side, group = meta["workload"], meta["subject"], meta["group"]
		values = dict(ref[label][side])
		if group == "F1":
			values[ev.F1_EVENT] = (f1 or (lambda label, side: 1.0e6))(label, side)
		return {**meta, "argv": ["mock"], "status": 0, "stdout": outputs[label], "stderr": text(group, values, override=override), "timed_out": False,
			"interrupted": False, "reaped": True, "group_survivors": [], **row_changes}

	def penalty(fraction):
		"""Candidate F1 count = base + fraction of that window's 0179 cycle excess (signal windows); flat elsewhere."""
		def f(label, side):
			if side == "cand" and label in ev.SIGNAL:
				return 1.0e6 + fraction * (ref[label]["cand"]["cycles"] - ref[label]["base"]["cycles"])
			return 1.0e6
		return f

	@control("O1-complete-runs-reach-the-registered-dispositions")
	def _():
		got = {}
		for name, fraction, want in (("strengthened", 0.8, "A-strengthened"), ("weakened", 0.02, "A-weakened"), ("mixed", 0.3, "A-mixed"), ("flat", 0.0, "A-weakened")):
			error, report, counts = mocked(f"complete-{name}", lambda meta, n, fraction=fraction: good(meta, f1=penalty(fraction)))
			assert error is None and report["status"] == "COMPLETE" and counts == {"R": 140, "F1": 140}, (name, error, report["status"], counts)
			a = report["stage_a"]
			assert a["disposition"] == want and a["locating_event"] is None and "closes at Stage A" in a["closure"], (name, a["disposition"])
			assert all(not report["groups"][g]["anchor_failures"] for g in ev.ORDER)
			got[name] = {"disposition": a["disposition"], "r": {w: round(v.get("r", float("nan")), 3) for w, v in a["signal_windows"].items()}}
		return got

	@control("O1-F1-row-failure-is-partial-with-A-failed-and-no-summary")
	def _():
		seen = {"n": 0}

		def make(meta, n):
			if meta["group"] == "F1":
				seen["n"] += 1
				if seen["n"] == 41:
					return good(meta, override={ev.F1_EVENT: {"counter-value": "<not counted>"}})
			return good(meta)
		error, report, counts = mocked("f1-local-failure", make)
		assert error is None and report["status"] == "PARTIAL COUNTER-VALIDITY STOP" and counts == {"R": 140, "F1": 41}, (error, report["status"], counts)
		assert report["groups"]["F1"]["status"].startswith("FAILED") and "summary" not in report["groups"]["F1"] and report["groups"]["F1"]["rows_retained"] == 41
		assert report["stage_a"]["disposition"] == "A-failed" and report["stage_a"]["collection_states"]["F1"] == "invalid"
		return {"counts": counts, "disposition": report["stage_a"]["disposition"]}

	@control("O1-global-stops")
	def _():
		got = {}
		for name, group, change in (("anchor in F1", "F1", {"override": {"cycles": {"counter-value": "<not counted>"}}}), ("survivor in F1", "F1", {"group_survivors": [123456]}),
				("wrong output in F1", "F1", {"stdout": "nope\n"}), ("status 1 in R", "R", {"status": 1}), ("timeout in R", "R", {"timed_out": True})):
			seen = {"n": 0}

			def make(meta, n, group=group, change=change):
				if meta["group"] == group:
					seen["n"] += 1
					if seen["n"] == 6:
						return good(meta, **change)
				return good(meta)
			error, report, counts = mocked(f"global-{name.replace(' ', '-')}", make)
			want = {"R": 6} if group == "R" else {"R": 140, "F1": 6}
			assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP") and counts == want and "stage_a" not in report, (name, error, counts)
			got[name] = report["status"]

		def vanish(meta, n):
			label, side = meta["workload"], meta["subject"]
			row = good(meta)
			if meta["group"] == "F1" and side == "cand" and label != "run-empty":
				row["stderr"] = text("F1", {**ref[label][side], "cycles": ref[label]["base"]["cycles"]})
			return row
		error, report, counts = mocked("nonreproducing-F1", vanish)
		assert error is None and report["status"] == "GLOBAL STOP (NONREPRODUCING)" and counts == {"R": 140, "F1": 140} and "stage_a" not in report
		got["F1 anchors do not reproduce"] = report["status"]

		def drift(groups_started):
			if groups_started == 2:
				raise ev.Stop(("host identity differs from this record's discovery", {"kernel": ["a", "b"]}))
		error, report, counts = mocked("identity-drift", lambda meta, n: good(meta), identity=drift)
		assert isinstance(error, ev.Stop) and counts == {"R": 140} and "stage_a" not in report
		got["identity drift before F1"] = report["status"]

		def late(meta, n):
			if n == 140:
				base.PHASE["deadline"] = time.monotonic() - 1
			return good(meta)
		error, report, counts = mocked("deadline-between-groups", late)
		assert isinstance(error, ev.Stop) and counts == {"R": 140}
		got["deadline between groups"] = report["status"]
		return got

	@control("O1-sentinel-hit-or-scan-error-overrides-any-status")
	def _():
		leak = lambda meta, n: {**good(meta, f1=penalty(0.8)), "note": os.environ["RNX0179_SENTINEL"]} if n == 200 else good(meta, f1=penalty(0.8))
		error, report, _ = mocked("sentinel", leak)
		assert isinstance(error, ev.Stop) and report["status"].startswith("GLOBAL STOP (sentinel") and report["status_before_scan"] == "COMPLETE"
		real_scan = base.scan
		base.scan = lambda *a: (_ for _ in ()).throw(OSError("scan failed"))
		try:
			error2, report2, _ = mocked("scan-error", lambda meta, n: good(meta))
		finally:
			base.scan = real_scan
		assert isinstance(error2, ev.Stop) and report2["sentinel_scan"]["completed"] is False and report2["status"].startswith("GLOBAL STOP (sentinel")
		return {"hit": report["status"], "scan_error": report2["sentinel_scan"]}

	# ---- availability and admission -----------------------------------------------------------------------------
	ok = [{"eligible": True, "detail": "ok"}, {"eligible": True, "detail": "ok"}]

	def manifest():
		return {"record": "0183", "status": "available", "order": list(ev.ORDER),
			"groups": {g: {"argv": base.perf_argv(g), "eligible": True, "checks": copy.deepcopy(ok)} for g in ev.ORDER},
			"excluded": dict(ev.EXCLUDED), "identity_sha256": "a" * 64, "primaries": {k: v[1] for k, v in base.PRIMARY.items()}, "libraries": dict(ev.LIBRARIES)}

	@control("V1-availability-content-validation")
	def _():
		def load(change):
			m = manifest()
			change(m)
			return ev.validate_availability(m, "a" * 64)
		assert load(lambda m: None)["order"] == ev.ORDER
		swap = lambda m, g, a, b: m["groups"][g]["argv"].__setitem__(5, m["groups"][g]["argv"][5].replace(a, b))
		fe = "{cpu_core/instructions,name=instructions/u,cpu_core/cpu-cycles,name=cycles/u,cpu_core/event=0xc6,umask=0x01,frontend=0x11,name=fe_dsb_miss/u}:D"
		return {"F1-ineligible": refused(lambda: load(lambda m: (m["groups"]["F1"]["checks"][1].update(eligible=False), m["groups"]["F1"].update(eligible=False)))),
			"F1-dropped-from-order": refused(lambda: load(lambda m: m["order"].remove("F1"))), "reordered": refused(lambda: load(lambda m: m["order"].reverse())),
			"A-unavailable-status": refused(lambda: load(lambda m: m.update(status="A-unavailable: F1 not available at discovery"))),
			"other-record": refused(lambda: load(lambda m: m.update(record="0181"))),
			"0181-manifest": refused(lambda: ev.validate_availability(json.loads((ev81.DISCOVERY / "availability.json").read_text()), ev81.IDENTITY_SHA256)),
			"group-F3-added": refused(lambda: load(lambda m: m["groups"].update(F3={"argv": ["perf", "stat", "-j", "--no-scale", "-e", fe, "--"], "eligible": True, "checks": copy.deepcopy(ok)}))),
			"F3-in-order": refused(lambda: load(lambda m: m["order"].append("F3"))), "group-D-added": refused(lambda: load(lambda m: m["groups"].update(D={"argv": base.perf_argv("D"), "eligible": True, "checks": copy.deepcopy(ok)}))),
			"exclusion-removed": refused(lambda: load(lambda m: m.pop("excluded"))), "exclusion-changed": refused(lambda: load(lambda m: m["excluded"].update(F3="valid"))),
			"F1-event-swapped-for-frontend": refused(lambda: load(lambda m: m["groups"]["F1"]["argv"].__setitem__(5, fe))),
			"F1-encoding-drift": refused(lambda: load(lambda m: swap(m, "F1", "umask=0x02", "umask=0x01"))), "weak-group-drift": refused(lambda: load(lambda m: swap(m, "F1", "}:D", "}:W"))),
			"scaling-drift": refused(lambda: load(lambda m: m["groups"]["R"]["argv"].remove("--no-scale"))), "atom-drift": refused(lambda: load(lambda m: swap(m, "F1", "cpu_core/event", "cpu_atom/event"))),
			"one-check": refused(lambda: load(lambda m: m["groups"]["F1"]["checks"].pop())), "identity-hash-zeroed": refused(lambda: load(lambda m: m.update(identity_sha256="0" * 64))),
			"other-subjects": refused(lambda: load(lambda m: m["primaries"].update(base="0" * 64))),
			"other-libraries": refused(lambda: load(lambda m: m["libraries"].update({"probes/execution-cost-0181/events0181.py": "0" * 64})))}

	@control("V2-admission-binds-reviewed-bytes-libraries-and-current-host")
	def _():
		real = (ev.DISCOVERY, ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256, ev81.identity_now, dict(ev.LIBRARIES))
		got = {}
		d = out / "synthetic-discovery"
		d.mkdir()
		base.start_phase(300)
		try:
			ident, _ = base.current_identity()
			(d / "identity.json").write_text(json.dumps(ident, indent=1) + "\n")
			m = manifest()
			m["identity_sha256"] = base.sha(d / "identity.json")
			(d / "availability.json").write_text(json.dumps(m, indent=1) + "\n")
			ev.DISCOVERY = d
			for name, pins in (("both-pins-unset", (None, None)), ("availability-pin-unset", (None, base.sha(d / "identity.json"))),
					("identity-pin-unset", (base.sha(d / "availability.json"), None))):
				ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256 = pins
				got[name] = refused(lambda: ev.load_availability(d / "availability.json"))
				assert "availability review has not frozen" in got[name], got[name]
			ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256 = base.sha(d / "availability.json"), base.sha(d / "identity.json")
			admitted, recorded, admission = ev.load_availability(d / "availability.json")
			assert admitted["order"] == ev.ORDER and recorded == ident and admission["perf_version_receipt"]["status"] == 0
			other = out / "elsewhere"
			other.mkdir()
			for name in ("availability.json", "identity.json"):
				(other / name).write_bytes((d / name).read_bytes())
			got["same-bytes-other-path"] = refused(lambda: ev.load_availability(other / "availability.json"))
			got["0181-receipts"] = refused(lambda: ev.load_availability(ev81.DISCOVERY / "availability.json"))
			tampered = manifest()
			tampered["identity_sha256"] = ev.IDENTITY_SHA256
			tampered["excluded"]["F3"] = "valid"
			pinned_good = ev.AVAILABILITY_SHA256
			(d / "availability.json").write_text(json.dumps(tampered, indent=1) + "\n")
			got["availability-bytes-changed"] = refused(lambda: ev.load_availability(d / "availability.json"))
			ev.AVAILABILITY_SHA256 = base.sha(d / "availability.json")
			got["changed-exclusion-refused-even-if-pinned"] = refused(lambda: ev.load_availability(d / "availability.json"))
			(d / "availability.json").write_text(json.dumps(m, indent=1) + "\n")
			ev.AVAILABILITY_SHA256 = pinned_good

			def drifted(change):
				now = copy.deepcopy(ident)
				change(now)
				ev81.identity_now = lambda: (now, {"status": 0})
				try:
					return refused(lambda: ev.load_availability(d / "availability.json"))
				finally:
					ev81.identity_now = real[3]
			got["kernel-drift"] = drifted(lambda i: i.update(kernel="7.0.0-32-generic"))
			got["perf-version-drift"] = drifted(lambda i: i.update(perf="perf version 7.1.0"))
			got["microcode-drift"] = drifted(lambda i: i["cpu4"].update(microcode="0x134"))
			got["watchdog-drift"] = drifted(lambda i: i.update(nmi_watchdog="0"))
			got["format-drift"] = drifted(lambda i: i["cpu_core_format"].update({"umask": "config:8-23"}))
			ev.LIBRARIES["probes/execution-cost-0180/events.py"] = "0" * 64
			got["library-hash-mismatch"] = refused(lambda: ev.load_availability(d / "availability.json"))
		finally:
			ev.LIBRARIES.clear()
			ev.LIBRARIES.update(real[4])
			ev.DISCOVERY, ev.AVAILABILITY_SHA256, ev.IDENTITY_SHA256, ev81.identity_now = real[:4]
			base.PHASE["deadline"] = None
		return got

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("0183 controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
