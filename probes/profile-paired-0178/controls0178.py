"""rnx 0178 untimed controls for the profile-axis repairs (review of 10c99af3: R1 identity, R2 matrix, R3 build
lifecycle). No subject is executed: binaries are only hashed, measure.main/reproduce and run_bounded are mocked.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 controls0178.py OUT_DIR
"""
import json, pathlib, sys, time
import build, matrix, measure
from common import PAIRS, Result

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


def main(out):
	out = pathlib.Path(out)
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

	@control("R1-real-manifest-is-consistent")
	def _():
		_, bad = measure.verify_manifest(measure.MANIFEST)
		assert bad == [], bad
		return "0 problems"

	@control("R1-swapped-profile-definitions-refused")
	def _():
		def swap(m):
			m["profiles"] = {"p0": m["profiles"]["p1"], "p1": m["profiles"]["p0"]}
		_, bad = measure.verify_manifest(tampered("swap-profiles", change_manifest=swap))
		assert any("profile definitions" in str(x) for x in bad), bad
		target = out / "refusal-swapped-profiles"
		try:
			measure.main(target, "p1", "s75", manifest=tmp / "manifest-swap-profiles.json")
			raise AssertionError("main accepted swapped profiles")
		except measure.Stop:
			pass
		assert sorted(p.name for p in target.iterdir()) == ["refused.json"]
		return bad

	@control("R1-missing-and-extra-artifact-names-refused")
	def _():
		def drop(m):
			del m["binaries"]["p1-s75-counter"]
		def extra(m):
			m["binaries"]["p2-base-primary"] = "0" * 64
		got = {}
		for name, fn in (("missing", drop), ("extra", extra)):
			_, bad = measure.verify_manifest(tampered(name, change_manifest=fn))
			assert any("artifact names" in str(x) for x in bad), (name, bad)
			got[name] = bad
		return got

	@control("R1-mismatched-row-identity-refused")
	def _():
		def relabel(b):
			b["builds"]["p0-s75-primary"]["profile"] = "p1"
		def wrong_section(b):
			b["builds"]["p1-s76-primary"]["manifest_profile_section"] = "\nopt-level = 3\n"
		def wrong_rev(b):
			b["builds"]["p0-s76-counter"]["rev"] = "863370da279031b369ebb0ac1c0d80cd9ca159f6"
		got = {}
		for name, fn in (("relabel", relabel), ("section", wrong_section), ("rev", wrong_rev)):
			_, bad = measure.verify_manifest(tampered(name, change_receipt=fn))
			assert any(x[0] == "row identity" for x in bad), (name, bad)
			got[name] = [x for x in bad if x[0] == "row identity"]
		return got

	@control("R1-profile-swapped-artifact-refused")
	def _():
		def swap_hash(m):
			m["binaries"]["p0-s75-primary"], m["binaries"]["p1-s75-primary"] = m["binaries"]["p1-s75-primary"], m["binaries"]["p0-s75-primary"]
		_, bad = measure.verify_manifest(tampered("swap-hash", change_manifest=swap_hash))
		assert ("binary", "p0-s75-primary") in bad and ("binary", "p1-s75-primary") in bad, bad
		m = manifest()
		swap_hash(m)
		try:
			measure.bind_pair(m, "p0", "s75")
			raise AssertionError("bind_pair accepted a profile-swapped artifact")
		except measure.Stop as stop:
			return {"verify": bad, "bind_pair": repr(stop)}

	@control("R1-all-four-role-mappings-in-one-process")
	def _():
		m = manifest()
		seen = {}
		for profile, source in PAIRS + list(reversed(PAIRS)):
			roles, hashes = measure.bind_pair(m, profile, source)
			assert roles == {"base": f"{profile}-base", "cand": f"{profile}-{source}"}, roles
			assert hashes == {"base": m["binaries"][f"{profile}-base-primary"], "cand": m["binaries"][f"{profile}-{source}-primary"]}, hashes
			assert measure.PROFILE == profile and measure.artifact("cand", "counter").name == f"{profile}-{source}-counter"
			seen[f"{profile}-{source}"] = roles
		return seen

	@control("R2-matrix-scientific-stop-reaches-all-cells")
	def _():
		calls = []

		def fake(target, profile, source):
			calls.append((profile, source))
			target.mkdir(parents=True)
			decision = "STOP" if len(calls) == 1 else "NO-WIN"
			(target / "measure.json").write_text(json.dumps({"decision": {"decision": decision, "regressions": [["mock", "instructions", 0.1]] if decision == "STOP" else [], "disagreements": []}}))
		real = matrix.measure.main
		matrix.measure.main = fake
		try:
			matrix.main(out / "matrix-complete")
		finally:
			matrix.measure.main = real
		ledger = json.loads((out / "matrix-complete/matrix.json").read_text())
		assert calls == PAIRS and ledger["status"] == "complete", (calls, ledger)
		assert [p["decision"] for p in ledger["pairs"]] == ["STOP", "NO-WIN", "NO-WIN", "NO-WIN"]
		return {"order": calls, "decisions": [p["decision"] for p in ledger["pairs"]]}

	@control("R2-matrix-infrastructure-failure-stops-and-retains")
	def _():
		calls = []

		def fake(target, profile, source):
			calls.append((profile, source))
			target.mkdir(parents=True)
			if len(calls) == 3:
				(target / "partial.json").write_text('{"partial": true}')
				raise measure.Stop(("injected infrastructure failure", profile, source))
			(target / "measure.json").write_text(json.dumps({"decision": {"decision": "NO-WIN", "regressions": [], "disagreements": []}}))
		real = matrix.measure.main
		matrix.measure.main = fake
		try:
			try:
				matrix.main(out / "matrix-stopped")
				raise AssertionError("matrix completed despite the failure")
			except measure.Stop:
				pass
		finally:
			matrix.measure.main = real
		ledger = json.loads((out / "matrix-stopped/matrix.json").read_text())
		assert calls == PAIRS[:3], calls
		assert ledger["status"].startswith("STOPPED") and "injected" in ledger["failure"], ledger
		assert [p.get("decision") for p in ledger["pairs"]] == ["NO-WIN", "NO-WIN", None]
		assert (out / "matrix-stopped" / f"{PAIRS[2][0]}-{PAIRS[2][1]}" / "partial.json").exists()
		assert not (out / "matrix-stopped" / f"{PAIRS[3][0]}-{PAIRS[3][1]}").exists()
		return {"invoked": calls, "status": ledger["status"]}

	@control("R2-reproduction-dispatch-p0-only")
	def _():
		calls = []
		real = measure.reproduce
		measure.reproduce = lambda *args: calls.append(args) or {}
		try:
			m = manifest()
			got = {}
			for profile in ("p1", "p0"):
				measure.bind_pair(m, profile, "s75")
				target = out / f"repro-dispatch-{profile}"
				target.mkdir()
				res = {}
				result = measure.reproduction_phase(target, tmp, None, None, None, res)
				got[profile] = {"calls_so_far": len(calls), "returned": result, "file": json.loads((target / "base-reproduction.json").read_text())}
		finally:
			measure.reproduce = real
		assert got["p1"]["calls_so_far"] == 0 and got["p1"]["file"]["applicable"] is False, got
		assert got["p0"]["calls_so_far"] == 1, got
		return got

	@control("R3-build-lifecycle-gate-after-retention")
	def _():
		clean = Result(["mock"], 0, "", "", False, False, True, [])
		build.lifecycle_gate(clean, "clean")
		stops = {}
		for name, r in (("survivor", Result(["mock"], 0, "", "", False, False, True, [123456])),
				("unreaped", Result(["mock"], 0, "", "", False, False, False, [])),
				("timeout", Result(["mock"], 0, "", "", True, False, True, []))):
			try:
				build.lifecycle_gate(r, name)
				raise AssertionError(f"{name} accepted")
			except SystemExit as stop:
				stops[name] = repr(stop)
		# step(): the record is written to the ledger and log BEFORE the gate rejects a status-0 survivor.
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
	print("0178 controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
