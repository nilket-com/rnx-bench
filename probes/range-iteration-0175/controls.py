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

	def clean(stdout, status=0, calls=100):
		return {"status": status, "stdout": stdout, "stderr": f"ALLOC [{calls}, 1, 1, 1]\n", "timed_out": False, "interrupted": False,
			"reaped": True, "group_survivors": [], "argv": ["synthetic"], "calls": calls}

	@control("R1b-changed-counting-stdout-stops")
	def _():
		good = {"base": clean("3\n"), "cand": clean("3\n")}
		measure.alloc_row_gate("run-numeric", good, "3\n")  # the correct shape passes
		bad = {"base": clean("3\n"), "cand": clean("4\n")}
		return {"stop": expect_stop(lambda: measure.alloc_row_gate("run-numeric", bad, "3\n"))}

	@control("R1b-same-wrong-budget-status-stops")
	def _():
		measure.budget_row_gate("numeric-budget-tight", {"base": clean("", 1), "cand": clean("", 1)})  # expected halt passes
		measure.budget_row_gate("numeric-budget-default", {"base": clean("3\n", 0), "cand": clean("3\n", 0)})
		crash = {"base": clean("", 101), "cand": clean("", 101)}  # identical on both sides, still not credited
		completed_when_halt_expected = {"base": clean("3\n", 0), "cand": clean("3\n", 0)}
		return {"same_crash": expect_stop(lambda: measure.budget_row_gate("numeric-budget-tight", crash)),
			"wrong_completion": expect_stop(lambda: measure.budget_row_gate("numeric-budget-zero", completed_when_halt_expected))}

	@control("R2b-unreaped-and-survivor-stop")
	def _():
		unreaped = {**clean("3\n"), "reaped": False}
		survivor = {**clean("3\n"), "group_survivors": [123456]}
		stops = {"unreaped": expect_stop(lambda: measure.lifecycle(unreaped)),
			"survivor": expect_stop(lambda: measure.lifecycle(survivor)),
			"alloc_survivor": expect_stop(lambda: measure.alloc_row_gate("run-numeric", {"base": clean("3\n"), "cand": survivor}, "3\n")),
			"check_status_unreaped": expect_stop(lambda: measure.check_status(unreaped, "3\n"))}
		measure.lifecycle(clean("3\n"))
		fifo_ok = {"child_reaped": True, "child_survivors": [], "counter_reaped": True, "counter_survivors": [], "child_status": 0,
			"counter_status": -signal.SIGINT}
		measure.fifo_gate(fifo_ok)
		stops["fifo_counter_status"] = expect_stop(lambda: measure.fifo_gate({**fifo_ok, "counter_status": 0}))
		stops["fifo_child_survivor"] = expect_stop(lambda: measure.fifo_gate({**fifo_ok, "child_survivors": [123456]}))
		stops["fifo_counter_unreaped"] = expect_stop(lambda: measure.fifo_gate({**fifo_ok, "counter_reaped": False}))
		return stops

	@control("R3b-manifest-constants")
	def _():
		m = json.loads(measure.MANIFEST.read_text())
		stops = {}
		for name, change in (("sources", lambda x: x["sources"].update(cand="1" * 40)),
				("parent", lambda x: x.update(production_parent="2" * 40))):
			t = json.loads(json.dumps(m))
			change(t)
			path = tmp / f"tampered-{name}.json"
			path.write_text(json.dumps(t))
			_, bad = measure.verify_manifest(path)
			assert bad, name
			stops[name] = bad
		return stops

	@control("R2c-ack-boundaries")
	def _():
		cases = {"ack\n": True, "\0ack\n": True, "ack\n\0": True, "\0\0ack\n": True, "a\0ck\n": False, "nak\n": False,
			"ack": False, "\0": False}
		got = {repr(k): measure.ack_ok(k) for k in cases}
		assert got == {repr(k): v for k, v in cases.items()}, got
		return got

	@control("R2c-fifo-protocol")
	def _():
		mock = tmp / "mock-counter-child"
		mock.write_text("#!/bin/sh\necho READY >&2\nread line\ni=0\nwhile [ $i -lt 2000 ]; do i=$((i+1)); done\n"
			"echo DONE >&2\nread line\n")
		mock.chmod(0o755)
		sink_path = out / "fifo-protocol.jsonl"
		sink = measure.Sink(sink_path)
		counts = []
		for i in range(2):  # repeated enable/disable acknowledgements across two windows
			v, row = measure.fifo("mock", None, tmp, sink, {"kind": "control-fifo", "work": "mock", "index": i}, exe=mock)
			counts.append(v)
		r = rows(sink_path)
		assert len(r) == 2 and all(x["child_reaped"] and x["counter_reaped"] and not x["child_survivors"] and not x["counter_survivors"]
			and x["child_status"] == 0 and x["counter_status"] == -signal.SIGINT and len(x["acks"]) == 2 for x in r), r
		assert all(v > 0 for v in counts)
		return {"instructions": counts, "acks": [x["acks"] for x in r], "ack_bytes": [x["ack_bytes"] for x in r]}

	(out / "controls.json").write_text(json.dumps(RESULTS, indent=1) + "\n")
	failed = [k for k, v in RESULTS.items() if not v["pass"]]
	print("controls:", len(RESULTS) - len(failed), "/", len(RESULTS), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1])
