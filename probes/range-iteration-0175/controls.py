"""rnx 0175 untimed lifecycle and retention controls (review R1-R4). No subject is timed for evidence.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 controls.py OUT_DIR

Each control injects one failure and checks that (a) the failed raw record was retained before any parse/assert,
(b) the failure stops the run, and (c) no later phase begins; the bounded-lifecycle controls check deadlines, partial
protocol bytes and process-group cleanup on interrupt with a descendant holding the output open.
"""
import json, os, pathlib, signal, subprocess, sys, time
import measure
from common import E0, run_bounded, group_alive, LineReader

RESULTS = {}


def control(name):
	def wrap(fn):
		began = time.monotonic()
		try:
			detail = fn()
			RESULTS[name] = {"pass": True, "detail": detail, "seconds": time.monotonic() - began}
		except Exception as error:
			RESULTS[name] = {"pass": False, "error": repr(error), "seconds": time.monotonic() - began}
		print(name, "PASS" if RESULTS[name]["pass"] else f"FAIL {RESULTS[name].get('error')}", flush=True)
		return fn
	return wrap


def rows(path):
	return [json.loads(l) for l in pathlib.Path(path).read_text().splitlines()]


def expect_stop(fn):
	try:
		fn()
	except measure.Stop as stop:
		return repr(stop)
	raise AssertionError("no Stop raised")


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	os.sched_setaffinity(0, {4})
	tmp = out / "tmp"
	tmp.mkdir()

	@control("R1-bad-status-retained")
	def _():
		sink_path = out / "bad-status.jsonl"
		stop = expect_stop(lambda: measure.perf(["/bin/false"], "", measure.Sink(sink_path), {"kind": "control"}))
		r = rows(sink_path)
		assert len(r) == 1 and r[0]["status"] == 1 and "raw_perf" not in r[0] and r[0]["argv"][-1] == "/bin/false", r
		return {"stop": stop, "retained_status": r[0]["status"]}

	@control("R1-malformed-counter-retained")
	def _():
		sink_path = out / "malformed.jsonl"
		fake = ["/bin/sh", "-c", 'printf \'{"event": "instructions:u", "counter-value": "x", "pcnt-running": "100"}\\n\' >&2; exec "$@"', "sh"]
		stop = expect_stop(lambda: measure.perf(["/bin/true"], "", measure.Sink(sink_path), {"kind": "control"}, perf_argv=fake))
		r = rows(sink_path)
		assert len(r) == 1 and r[0]["status"] == 0 and '"counter-value": "x"' in r[0]["stderr"], r
		return {"stop": stop, "retained_stderr": r[0]["stderr"]}

	@control("R1-incomplete-wall-receipt-retained")
	def _():
		sink_path = out / "receipt.jsonl"
		clock = tmp / "short-clock"
		clock.write_text("#!/bin/sh\nprintf 'EXEC 0\\n'\n")
		clock.chmod(0o755)
		stop = expect_stop(lambda: measure.resident(["/bin/true"], "", 2, tmp, measure.Sink(sink_path), {"kind": "control"}, clock=clock))
		r = rows(sink_path)
		assert len(r) == 1 and r[0]["stdout"] == "EXEC 0\n" and r[0]["plan"].startswith("2\n"), r
		return {"stop": stop, "retained_stdout": r[0]["stdout"]}

	@control("R1-timeout-retained-and-killed")
	def _():
		sink_path = out / "timeout.jsonl"
		sink = measure.Sink(sink_path)
		began = time.monotonic()
		row = measure.sample(["/bin/sh", "-c", "printf partial; sleep 30"], 1, sink, {"kind": "control"})
		sink.write(row)
		stop = expect_stop(lambda: measure.check_status(row, ""))
		elapsed = time.monotonic() - began
		r = rows(sink_path)
		assert r[0]["timed_out"] and r[0]["stdout"] == "partial" and r[0]["reaped"] and elapsed < 15, (r, elapsed)
		return {"stop": stop, "elapsed_s": elapsed, "partial_stdout": r[0]["stdout"]}

	@control("R2-partial-line-timeout")
	def _():
		p = subprocess.Popen(["/bin/sh", "-c", "printf REA >&2; sleep 30"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
			env=E0, start_new_session=True)
		reader = LineReader(p.stderr.fileno())
		began = time.monotonic()
		try:
			reader.line(time.monotonic() + 1)
			raise AssertionError("line returned")
		except TimeoutError as error:
			message = str(error)
		finally:
			measure.kill_group(p.pid)
			p.wait(timeout=10)
		elapsed = time.monotonic() - began
		assert bytes(reader.seen) == b"REA" and "REA" in message and elapsed < 5 and not group_alive(p.pid), (reader.seen, elapsed)
		return {"partial": bytes(reader.seen).decode(), "elapsed_s": elapsed}

	@control("R2-interrupt-with-held-pipe")
	def _():
		pid_file = tmp / "group.pid"

		def interrupt(signum, frame):
			raise KeyboardInterrupt

		old = signal.signal(signal.SIGALRM, interrupt)
		signal.alarm(1)
		began = time.monotonic()
		try:
			run_bounded(["/bin/sh", "-c", f"echo $$ > {pid_file}; printf held; sleep 30 & sleep 30"], 60, E0)
			raise AssertionError("not interrupted")
		except KeyboardInterrupt as error:
			partial = error.partial
		finally:
			signal.alarm(0)
			signal.signal(signal.SIGALRM, old)
		elapsed = time.monotonic() - began
		pgid = int(pid_file.read_text())
		assert partial["interrupted"] and partial["reaped"] and partial["stdout"] == "held" and elapsed < 15, (partial, elapsed)
		assert not group_alive(pgid), "process group survived the interrupt"
		return {"elapsed_s": elapsed, "partial": partial}

	@control("R3-changed-binary-refused-before-any-phase")
	def _():
		m = json.loads(measure.MANIFEST.read_text())
		m["binaries"]["cand-primary"] = "0" * 64
		tampered = tmp / "tampered.json"
		tampered.write_text(json.dumps(m))
		target = out / "refusal-run"
		stop = expect_stop(lambda: measure.main(target, manifest=tampered))
		files = sorted(str(p.relative_to(target)) for p in target.rglob("*"))
		assert files == ["refused.json"], files
		return {"stop": stop, "files": files, "refused": json.loads((target / "refused.json").read_text())}

	@control("R3-changed-fixture-refused")
	def _():
		m = json.loads(measure.MANIFEST.read_text())
		key = "range/range_signed.rn"
		m["inputs"][key] = "0" * 64
		tampered = tmp / "tampered-input.json"
		tampered.write_text(json.dumps(m))
		target = out / "refusal-input-run"
		stop = expect_stop(lambda: measure.main(target, manifest=tampered))
		assert sorted(p.name for p in target.iterdir()) == ["refused.json"]
		return {"stop": stop}

	@control("R1-later-phases-do-not-begin")
	def _():
		real = measure.controls

		def failing(label, sink):
			raise measure.Stop(("injected", label))

		measure.controls = failing
		target = out / "stopped-run"
		try:
			stop = expect_stop(lambda: measure.main(target))
		finally:
			measure.controls = real
		phases = [r["phase"] for r in rows(target / "phases.jsonl")]
		assert phases == ["rehearsal", "controls-start"], phases
		assert not (target / "correctness.json").exists() and not (target / "allocation.json").exists()
		return {"stop": stop, "phases": phases}

	@control("R4-allocation-qualification")
	def _():
		base = json.loads((measure.REPO / "results/range-iteration-0175/rehearsal1/measure/allocation.json").read_text())
		measure.alloc_gate(base)  # the rehearsal's real table passes
		stops = {}
		for name, key, delta in (("changed-context", "context", 2), ("floor-rise", "floor", 1), ("empty-context-rise", "empty-context", 1),
				("unrelated-rise", "run-fib", 2), ("manual-next-drop", "run-manual_next", -5), ("context-zero", "context", 0)):
			synthetic = json.loads(json.dumps(base))
			synthetic[key]["calls_delta"] = delta
			stops[name] = expect_stop(lambda: measure.alloc_gate(synthetic))
		return stops

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
