"""rnx 0179 untimed controls for what this record changes in the 0178 tooling: the single P0 pair's identity, the
WIN rule (context AND run-answer), the first-use workload being deciding, and the official wrapper's
scientific-STOP versus infrastructure-failure handling. No subject is executed: binaries are only hashed and
measure.main is mocked.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 controls0179.py OUT_DIR
"""
import json, math, pathlib, sys, time
import build, measure, official
from common import PAIRS, PROFILES, SOURCES, Result

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


def manifest():
	return json.loads(measure.MANIFEST.read_text())


def table(changes=None, wall_changes=None, band=0.05):
	"""Synthetic pmu/wall/allocation tables over the real workload list: base 1e6 instructions and 10 ms everywhere,
	the candidate moved by the given fractional changes (default 0)."""
	changes, wall_changes = changes or {}, wall_changes or {}
	pmu, walls = {}, {}
	for label, _, _ in measure.WORKLOADS:
		pmu[label] = {"instructions": {"base_median": 1e6, "cand_median": 1e6 * (1 + changes.get(label, 0))}}
		walls[label] = {"base_median_ms": 10.0, "cand_median_ms": 10.0 * (1 + wall_changes.get(label, 0)), "base_p10_p90_ms": band}
	return pmu, walls, {"context": {"calls_delta": -1785}}


def main(out):
	out = pathlib.Path(out).resolve()  # tampered receipts are addressed relative to the repository root
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	real_receipt = measure.REPO / manifest()["build_receipt"]["path"]

	def tampered(name, change_manifest=None, change_receipt=None):
		m = manifest()
		if change_receipt:
			b = json.loads(real_receipt.read_text())
			change_receipt(b)
			path = tmp / f"receipt-{name}.json"
			path.write_text(json.dumps(b))
			m["build_receipt"] = {"path": str(path.relative_to(measure.REPO)), "sha256": measure.sha(path)}
		if change_manifest:
			change_manifest(m)
		path = tmp / f"manifest-{name}.json"
		path.write_text(json.dumps(m))
		return path

	@control("I1-real-manifest-is-consistent")
	def _():
		_, bad = measure.verify_manifest(measure.MANIFEST)
		assert bad == [], bad
		assert PROFILES == {"p0": []} and PAIRS == [("p0", "cand")] and set(SOURCES) == {"base", "cand"}
		return "0 problems; one profile, one pair"

	@control("I1-altered-profile-refused")
	def _():
		def cgu1(m):
			m["profiles"] = {"p0": ["codegen-units = 1"]}
		def section(b):
			b["builds"]["p0-cand-primary"]["manifest_profile_section"] = "\nopt-level = 3\ncodegen-units = 1\n"
		def units(b):
			b["builds"]["p0-base-primary"]["codegen_units"] = "1 on every target invocation"
		got = {}
		_, got["definition"] = measure.verify_manifest(tampered("profile-definition", change_manifest=cgu1))
		assert any("profile definitions" in str(x) for x in got["definition"]), got
		for name, fn in (("section", section), ("units", units)):
			_, bad = measure.verify_manifest(tampered(f"profile-{name}", change_receipt=fn))
			assert any(x[0] == "row identity" for x in bad), (name, bad)
			got[name] = [x for x in bad if x[0] == "row identity"]
		return got

	@control("I1-missing-and-extra-artifact-names-refused")
	def _():
		def drop(m):
			del m["binaries"]["p0-cand-counter"]
		def extra(m):
			m["binaries"]["p1-base-primary"] = "0" * 64
		got = {}
		for name, fn in (("missing", drop), ("extra", extra)):
			_, bad = measure.verify_manifest(tampered(name, change_manifest=fn))
			assert any("artifact names" in str(x) for x in bad), (name, bad)
			got[name] = bad
		return got

	@control("I1-mismatched-row-identity-refused")
	def _():
		def relabel(b):
			b["builds"]["p0-cand-primary"]["source"] = "base"
		def wrong_kind(b):
			b["builds"]["p0-base-counter"]["kind"] = "primary"
		def wrong_rev(b):
			b["builds"]["p0-cand-allocation"]["rev"] = SOURCES["base"]
		got = {}
		for name, fn in (("relabel", relabel), ("kind", wrong_kind), ("rev", wrong_rev)):
			_, bad = measure.verify_manifest(tampered(name, change_receipt=fn))
			assert any(x[0] == "row identity" for x in bad), (name, bad)
			got[name] = [x for x in bad if x[0] == "row identity"]
		return got

	@control("I1-role-swapped-artifact-refused")
	def _():
		def swap_hash(m):
			m["binaries"]["p0-base-primary"], m["binaries"]["p0-cand-primary"] = m["binaries"]["p0-cand-primary"], m["binaries"]["p0-base-primary"]
		_, bad = measure.verify_manifest(tampered("swap-hash", change_manifest=swap_hash))
		assert ("binary", "p0-base-primary") in bad and ("binary", "p0-cand-primary") in bad, bad
		m = manifest()
		swap_hash(m)
		try:
			measure.bind_pair(m, "p0", "cand")
			raise AssertionError("bind_pair accepted role-swapped artifacts")
		except measure.Stop as stop:
			return {"verify": bad, "bind_pair": repr(stop)}

	@control("I1-only-the-frozen-pair-binds")
	def _():
		m = manifest()
		roles, hashes = measure.bind_pair(m, "p0", "cand")
		assert roles == {"base": "p0-base", "cand": "p0-cand"} and hashes == {"base": m["binaries"]["p0-base-primary"],
			"cand": m["binaries"]["p0-cand-primary"]}, (roles, hashes)
		refused = {}
		for pair in (("p1", "cand"), ("p0", "base"), ("p0", "s75")):
			try:
				measure.bind_pair(m, *pair)
				raise AssertionError(f"bind_pair accepted {pair}")
			except measure.Stop as stop:
				refused["-".join(pair)] = repr(stop)
		measure.bind_pair(m, "p0", "cand")
		return {"roles": roles, "refused": refused}

	@control("W1-both-first-use-workloads-are-deciding")
	def _():
		labels = [label for label, _, _ in measure.WORKLOADS]
		assert list(measure.FIRST_USE) == ["first-use-true", "first-use-false"]
		assert measure.WIN_INSTR == ["context", "run-answer"] and all(w in labels for w in measure.WIN_INSTR)
		win = {"context": -0.12, "run-answer": -0.11}
		got = {}
		for label, tail in measure.FIRST_USE.items():
			assert labels.count(label) == 1 and measure.EXPECT_BY_LABEL[label] == "FIRST-USE 42\n", label
			assert tail[0] == "first-use" and tail[1] == label.rsplit("-", 1)[1] and pathlib.Path(tail[2]).is_file(), tail
			d = measure.decide(*table({**win, label: 0.006}))
			assert d["decision"] == "STOP" and [r[:2] for r in d["regressions"]] == [(label, "instructions")], d
			d = measure.decide(*table(win, {label: 0.006}))
			assert d["decision"] == "STOP" and [r[:2] for r in d["regressions"]] == [(label, "wall")], d
			pmu, walls, alloc = table(win)
			del pmu[label]
			try:
				measure.decide(pmu, walls, alloc)
				raise AssertionError(f"decided without {label}")
			except measure.Stop as stop:
				got[label] = repr(stop)
		# the two modes use different fixtures and different stdio flags: neither stands in for the other
		assert measure.FIRST_USE["first-use-true"][2] != measure.FIRST_USE["first-use-false"][2]
		return got

	@control("I1-neutrality-and-edit-surface-bound")
	def _():
		def differs(m):
			m["neutrality"]["text_sha256"] = "0" * 64
		def unchecked(m):
			m["neutrality"]["accepted"] = False
		def unexplained(m):
			m["neutrality"]["comparison"]["problems"].append("section .rodata differs")
		def wider(m):
			m["candidate_diff"]["production_files"].append("crates/rune/src/runtime/vm.rs")
		got = {}
		for name, fn, needle in (("differs", differs, "neutrality control"), ("unchecked", unchecked, "neutrality control"),
				("unexplained", unexplained, "neutrality control"), ("wider", wider, "candidate edit surface")):
			_, bad = measure.verify_manifest(tampered(f"neutrality-{name}", change_manifest=fn))
			assert (needle,) in bad, (name, bad)
			got[name] = bad
		return got

	@control("W1-win-needs-both-startup-legs")
	def _():
		got = {}
		# The rule is change <= -0.10 on medians; the synthetic values sit clearly on either side (a base of 1e6 scaled by
		# exactly 0.9 is not exactly -10% in binary floating point, so the boundary itself is not a meaningful control).
		for name, changes, want in (("both", {"context": -0.1001, "run-answer": -0.1001}, "WIN"),
				("context-only", {"context": -0.30, "run-answer": -0.0999}, "NO-WIN"),
				("run-answer-only", {"context": -0.0999, "run-answer": -0.30}, "NO-WIN"),
				("neither", {}, "NO-WIN"),
				("large-gain-elsewhere", {"run-numeric": -0.5, "run-fib": -0.5}, "NO-WIN")):
			got[name] = measure.decide(*table(changes))["decision"]
			assert got[name] == want, (name, got[name], want)
		return got

	@control("W1-no-gain-overrides-a-failed-workload")
	def _():
		win = {"context": -0.4, "run-answer": -0.4}
		got = {}
		for name, changes, wall in (("instructions-0.5%", {**win, "run-while": 0.0051}, {}),
				("wall-beyond-band", win, {"run-fib": 0.0051}),
				("opposing-above-3%", {**win, "run-calls": -0.04}, {"run-calls": 0.04})):
			d = measure.decide(*table(changes, wall))
			assert d["decision"] == "STOP", (name, d["decision"])
			got[name] = {"regressions": d["regressions"], "disagreements": d["disagreements"]}
		at_limit = measure.decide(*table({**win, "run-while": 0.005}, {"run-fib": 0.005}))
		assert at_limit["decision"] == "WIN", at_limit["decision"]  # exactly 0.5% and exactly the band are not regressions
		return got

	@control("W1-non-finite-medians-do-not-decide")
	def _():
		got = {}
		for name, value in (("nan", math.nan), ("inf", math.inf), ("zero-base", 0.0)):
			pmu, walls, alloc = table({"context": -0.2, "run-answer": -0.2})
			if name == "zero-base":
				pmu["run-fib"]["instructions"]["base_median"] = value
			else:
				pmu["run-fib"]["instructions"]["cand_median"] = value
			try:
				d = measure.decide(pmu, walls, alloc)
				raise AssertionError((name, "decided", d["decision"]))
			except measure.Stop as stop:
				got[name] = repr(stop)
		return got

	@control("O1-scientific-stop-is-a-completed-result")
	def _():
		got = {}
		for decision in ("STOP", "NO-WIN", "WIN"):
			def fake(target, profile, source, decision=decision):
				target.mkdir(parents=True)
				(target / "measure.json").write_text(json.dumps({"decision": {"decision": decision,
					"regressions": [["mock", "instructions", 0.1]] if decision == "STOP" else [], "disagreements": []}}))
			real = official.measure.main
			official.measure.main = fake
			try:
				official.main(out / f"official-{decision}")
			finally:
				official.measure.main = real
			ledger = json.loads((out / f"official-{decision}/official.json").read_text())
			assert ledger["status"] == "complete" and ledger["decision"] == decision and ledger["pair"] == ["p0", "cand"], ledger
			got[decision] = ledger["status"]
		return got

	@control("O1-infrastructure-failure-stops-and-retains")
	def _():
		def fake(target, profile, source):
			target.mkdir(parents=True)
			(target / "partial.json").write_text('{"partial": true}')
			raise measure.Stop(("injected infrastructure failure", profile, source))
		real = official.measure.main
		official.measure.main = fake
		try:
			try:
				official.main(out / "official-stopped")
				raise AssertionError("official run completed despite the failure")
			except measure.Stop:
				pass
		finally:
			official.measure.main = real
		ledger = json.loads((out / "official-stopped/official.json").read_text())
		assert ledger["status"].startswith("STOPPED") and "injected" in ledger["failure"] and "decision" not in ledger, ledger
		assert (out / "official-stopped/p0-cand/partial.json").exists()
		return ledger["status"]

	@control("B1-diagnostic-cfg-guard")
	def _():
		declared = "Running `rustc --crate-name rune --check-cfg 'cfg(rune_nightly, rune_docsrs, rune_byte_code, rune_startup_inventory)' --cfg 'feature=\"alloc\"' -C opt-level=3`"
		assert build.diagnostic_cfg_uses(declared) == [], "the declaration alone must be accepted"
		real_log = pathlib.Path(measure.REPO / manifest()["build_receipt"]["path"]).parent / "build-p0-cand-primary.log"
		assert "rune_startup_inventory" in real_log.read_text() and build.diagnostic_cfg_uses(real_log.read_text()) == []
		got = {}
		for name, line in (("set", declared.replace(" -C opt", " --cfg rune_startup_inventory -C opt")),
				("set-quoted", declared.replace(" -C opt", " --cfg 'rune_startup_inventory' -C opt")),
				("rustflags", "RUSTFLAGS='--cfg rune_startup_inventory' " + declared),
				("set-without-declaration", "Running `rustc --crate-name rune --cfg rune_startup_inventory`"),
				("feature-like", declared.replace(" -C opt", " --cfg 'feature=\"rune_startup_inventory\"' -C opt"))):
			got[name] = build.diagnostic_cfg_uses(line)
			assert got[name], name
		return got

	@control("B1-build-lifecycle-gate-after-retention")
	def _():
		build.lifecycle_gate(Result(["mock"], 0, "", "", False, False, True, []), "clean")
		stops = {}
		for name, r in (("survivor", Result(["mock"], 0, "", "", False, False, True, [123456])),
				("unreaped", Result(["mock"], 0, "", "", False, False, False, [])),
				("timeout", Result(["mock"], 0, "", "", True, False, True, []))):
			try:
				build.lifecycle_gate(r, name)
				raise AssertionError(f"{name} accepted")
			except SystemExit as stop:
				stops[name] = repr(stop)
		real = build.run_bounded
		build.run_bounded = lambda *a, **k: Result(["mock-build"], 0, "built\n", "", False, False, True, [123456])
		d = out / "step"
		d.mkdir()
		ledger = build.Ledger(d / "commands.jsonl")
		try:
			try:
				build.step(d, ledger, "mock-build", ["mock-build"], {})
				raise AssertionError("step accepted a status-0 build with a survivor")
			except SystemExit as stop:
				stops["step"] = repr(stop)
		finally:
			build.run_bounded = real
		row = json.loads((d / "commands.jsonl").read_text().splitlines()[0])
		assert row["status"] == 0 and row["group_survivors"] == [123456] and (d / "mock-build.log").read_text() == "built\n", row
		return stops

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("0179 controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
