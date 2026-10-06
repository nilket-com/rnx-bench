"""rnx 0178 untimed controls for the callgrind diagnostic tooling (review R1): injected tool failures must be retained
and must never produce an "absent" symbol or an attribution table.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 callgrind_controls.py OUT_DIR
"""
import json, pathlib, signal, sys, time
import callgrind
from common import E0

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


def expect_failure(fn):
	try:
		fn()
	except callgrind.DiagnosticFailure as failure:
		return repr(failure)
	raise AssertionError("no DiagnosticFailure")


def script(path, body):
	path.write_text("#!/bin/sh\n" + body + "\n")
	path.chmod(0o755)
	return str(path)


def rows(out):
	return [json.loads(l) for l in (out / "commands.jsonl").read_text().splitlines()]


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	real = dict(callgrind.TOOLS)

	@control("nm-nonzero-is-failure-not-absent")
	def _():
		d = out / "nm-fail"
		d.mkdir()
		rec = callgrind.Recorder(d)
		callgrind.TOOLS["nm"] = script(tmp / "nm", "echo 'nm: broken' >&2; exit 1")
		try:
			failure = expect_failure(lambda: callgrind.symbol_table(rec, callgrind.measure.BIN / "p0-base-primary", "mock"))
		finally:
			callgrind.TOOLS.update(real)
		r = rows(d)
		assert len(r) == 1 and r[0]["status"] == 1 and "nm: broken" in r[0]["stderr"], r
		assert "absent" not in json.dumps(rec.summary)
		return {"failure": failure, "retained_status": r[0]["status"]}

	@control("annotate-nonzero-retained-and-fails")
	def _():
		d = out / "annotate-fail"
		d.mkdir()
		rec = callgrind.Recorder(d)
		callgrind.TOOLS["annotate"] = script(tmp / "annotate", "echo partial-table; echo 'annotate: broken' >&2; exit 2")
		try:
			failure = expect_failure(lambda: callgrind.annotate(rec, tmp / "missing.cg", "mock", "mock"))
		finally:
			callgrind.TOOLS.update(real)
		r = rows(d)
		assert len(r) == 1 and r[0]["status"] == 2 and r[0]["stdout"] == "partial-table\n", r
		assert (d / "annotate-exclusive.mock.mock.txt").read_text() == "partial-table\n"
		return {"failure": failure}

	@control("interrupted-command-partial-retained")
	def _():
		d = out / "interrupt"
		d.mkdir()
		rec = callgrind.Recorder(d)

		def interrupt(signum, frame):
			raise KeyboardInterrupt

		old = signal.signal(signal.SIGALRM, interrupt)
		signal.alarm(1)
		try:
			rec.tool(["/bin/sh", "-c", "printf part; sleep 30"], 60, E0, {"kind": "mock"})
			raise AssertionError("not interrupted")
		except KeyboardInterrupt:
			pass
		finally:
			signal.alarm(0)
			signal.signal(signal.SIGALRM, old)
		r = rows(d)
		assert len(r) == 1 and r[0]["interrupted"] and r[0]["stdout"] == "part" and "KeyboardInterrupt" in r[0]["exception"], r
		assert r[0]["reaped"] and not r[0]["group_survivors"], r
		return {"retained": {k: r[0][k] for k in ("stdout", "interrupted", "reaped", "group_survivors")}}

	@control("callgrind-summary-validation")
	def _():
		good = tmp / "good.cg"
		good.write_text("version: 1\nevents: Ir\nfn=main\n0 5\nsummary: 1234\n")
		assert callgrind.check_callgrind_file(good, 1234) == 1234
		cases = {}
		cases["missing"] = expect_failure(lambda: callgrind.check_callgrind_file(tmp / "absent.cg", 1234))
		(tmp / "noevent.cg").write_text("version: 1\nsummary: 1234\n")
		cases["no-ir-event"] = expect_failure(lambda: callgrind.check_callgrind_file(tmp / "noevent.cg", 1234))
		(tmp / "nosum.cg").write_text("version: 1\nevents: Ir\n")
		cases["no-summary"] = expect_failure(lambda: callgrind.check_callgrind_file(tmp / "nosum.cg", 1234))
		(tmp / "zero.cg").write_text("version: 1\nevents: Ir\nsummary: 0\n")
		cases["zero-summary"] = expect_failure(lambda: callgrind.check_callgrind_file(tmp / "zero.cg", 0))
		cases["mismatch"] = expect_failure(lambda: callgrind.check_callgrind_file(good, 999))
		cases["no-collected-total"] = expect_failure(lambda: callgrind.check_callgrind_file(good, None))
		return cases

	@control("tool-failure-leaves-no-attribution")
	def _():
		target = out / "failed-main"
		callgrind.TOOLS["nm"] = script(tmp / "nm2", "exit 3")
		try:
			try:
				callgrind.main(target)
				raise AssertionError("main succeeded with a failing nm")
			except callgrind.DiagnosticFailure as failure:
				message = repr(failure)
		finally:
			callgrind.TOOLS.update(real)
		summary = json.loads((target / "diagnostic.json").read_text())
		assert summary["status"] == "FAILED (inconclusive)" and summary["runs"] == {} and "symbols" not in json.dumps(summary["subjects"]), summary
		assert not list(target.glob("annotate-*")) and not list(target.glob("callgrind.out.*"))
		return {"failure": message, "status": summary["status"]}

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("callgrind controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
