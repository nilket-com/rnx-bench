"""rnx 0162 R2: the HTTP benchmark, after every implementation passes check.py.

	python3 bench.py OUT_DIR

Placement (i7-14700): each server is pinned to CPUs 2,4 (two physical P-cores, one thread each;
their siblings 3,5 idle); oha 1.16.0 to CPUs 8,10,12,14. W = 2 for every implementation:
A axum with 2 tokio worker threads; B 2 rnx worker threads plus its acceptor thread (all inside
the same two CPUs); C gunicorn 26.2.0, 2 `gthread` workers of 4 threads, --keep-alive 5.
HTTP/1.1 only. Per condition: a 3 s warm-up run (discarded), then 10 s measured; 3 repetitions,
interleaved A, B, C within each repetition. Conditions: routes `/` and `/hello/world` at
concurrency 1 and 32 with keep-alive; `/hello/world` at concurrency 1 without keep-alive.
A run counts only if every response is 200 (oha's status distribution) with no errors.
RSS: the sum over the server's whole process tree (C: the arbiter and its workers), from
/proc, at rest before load and in the middle of the first measured run of each condition.
Keep-alive at the wire: at start-up, a wire control sends three HTTP/1.1 requests on one socket
and reads three complete replies (reuse, not only occupancy); during each keep-alive run,
established server-side connections on the port are counted (ss) mid-run and must equal the
concurrency (occupancy).

Review of 0162 (R2): every gate fails closed. A run is accepted only if oha exits 0 with complete
JSON whose timing and count fields are present, finite and positive, its status distribution is
exactly 200, its error distribution is empty, and (with keep-alive) its connection sample is
present and equal to the concurrency. `python3 bench.py --controls` runs stubbed refusals.

	python3 bench.py OUT_DIR
	python3 bench.py --controls"""
import json, math, os, pathlib, socket, statistics, subprocess, sys, threading, time

HERE = pathlib.Path(__file__).resolve().parent
SERVER_CPUS, LOAD_CPUS = "2,4", "8,10,12,14"
PORTS = {"A": 18101, "B": 18102, "C": 18103}


class Refused(Exception):
	pass


def wire_reuse(port, requests=3):
	"""Three requests on one socket, each reply read whole by its content-length."""
	with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
		reader = s.makefile("rb")
		for i in range(requests):
			s.sendall(b"GET /hello/world HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
			status = reader.readline()
			if not status.startswith(b"HTTP/1.1 200"):
				raise Refused(f"request {i + 1} on one socket: {status!r}")
			length = None
			while (line := reader.readline()) not in (b"\r\n", b""):
				name, _, value = line.decode().partition(":")
				if name.lower() == "content-length":
					length = int(value)
			if length is None or len(reader.read(length)) != length:
				raise Refused(f"request {i + 1}: incomplete reply")


def start(name):
	port = PORTS[name]
	if name == "A":
		cmd, env = [str(HERE / "a/target/release/web0162-a"), f"127.0.0.1:{port}"], {"WORKERS": "2"}
	elif name == "B":
		cmd, env = [str(HERE / "b/target/release/web0162-b"), str(HERE / "b/site.rn"), f"127.0.0.1:{port}"], {"WORKERS": "2"}
	else:
		cmd = [str(HERE / "c/.venv/bin/gunicorn"), "-k", "gthread", "-w", "2", "--threads", "4", "--keep-alive", "5",
			   "-b", f"127.0.0.1:{port}", "--chdir", str(HERE / "c"), "app:app"]
		env = {"PATH": os.environ["PATH"]}
	proc = subprocess.Popen(["taskset", "-c", SERVER_CPUS, *cmd], env=env, stdin=subprocess.DEVNULL,
							stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	time.sleep(2)
	check = subprocess.run([sys.executable, str(HERE / "check.py"), f"http://127.0.0.1:{port}"], capture_output=True, text=True)
	if check.returncode != 0:
		proc.terminate()
		raise SystemExit(f"{name} failed the fixtures:\n{check.stdout}")
	try:
		wire_reuse(port)
	except Refused:
		proc.terminate()
		raise
	return proc


def tree_rss(pid):
	"""Resident KiB summed over pid and all its descendants."""
	children = {}
	for p in pathlib.Path("/proc").iterdir():
		if p.name.isdigit():
			try:
				ppid = int((p / "stat").read_text().rsplit(")", 1)[1].split()[1])
			except (OSError, IndexError):
				continue
			children.setdefault(ppid, []).append(int(p.name))
	total, stack = 0, [pid]
	while stack:
		q = stack.pop()
		try:
			for line in pathlib.Path(f"/proc/{q}/status").read_text().splitlines():
				if line.startswith("VmRSS:"):
					total += int(line.split()[1])
		except OSError:
			pass
		stack.extend(children.get(q, []))
	return total


def established(port):
	out = subprocess.run(["ss", "-Htn", "state", "established", f"( sport = :{port} )"], capture_output=True, text=True).stdout
	return len([l for l in out.splitlines() if l.strip()])


def oha(port, route, concurrency, seconds, keepalive):
	cmd = ["taskset", "-c", LOAD_CPUS, "oha", "--no-tui", "--output-format", "json", "-z", f"{seconds}s",
		   "-c", str(concurrency), "-w", f"http://127.0.0.1:{port}{route}"]
	if not keepalive:
		cmd.insert(-1, "--disable-keepalive")
	r = subprocess.run(cmd, capture_output=True, text=True)
	if r.returncode != 0:
		raise Refused(f"oha exited {r.returncode}: {r.stderr[-300:]}")
	try:
		return json.loads(r.stdout)
	except json.JSONDecodeError as e:
		raise Refused(f"oha's JSON is incomplete: {e}")


def validate(result, concurrency, keepalive, connections):
	"""The accepted row, or Refused: complete finite positive fields, only 200s, no errors, and the
	connection sample equal to the concurrency with keep-alive."""
	def number(value, what):
		if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
			raise Refused(f"{what} is {value!r}")
		return value
	try:
		summary, pct = result["summary"], result["latencyPercentiles"]
		codes, errors = result["statusCodeDistribution"], result["errorDistribution"]
	except (KeyError, TypeError) as e:
		raise Refused(f"missing field {e}")
	if not isinstance(codes, dict) or set(codes) != {"200"} or errors != {}:
		raise Refused(f"statuses {codes!r}, errors {errors!r}")
	rps = number(summary.get("requestsPerSec"), "requestsPerSec")
	p50 = number(pct.get("p50"), "p50")
	p99 = number(pct.get("p99"), "p99")
	successful = number(codes["200"], "successful requests")
	if keepalive and connections != concurrency:
		raise Refused(f"{connections!r} established connections for concurrency {concurrency}")
	return {"ok": True, "codes": codes, "errors": errors, "rps": rps, "successful": successful,
			"p50_ms": p50 * 1000, "p99_ms": p99 * 1000}


def measure(name, proc, route, concurrency, keepalive, first):
	port = PORTS[name]
	oha(port, route, concurrency, 3, keepalive)  # warm-up, discarded
	sample = {}

	def probe():
		time.sleep(5)
		sample["connections"] = established(port)
		if first:
			sample["rss_kib"] = tree_rss(proc.pid)
	t = threading.Thread(target=probe)
	t.start()
	result = oha(port, route, concurrency, 10, keepalive)
	t.join()
	return {**validate(result, concurrency, keepalive, sample.get("connections")), **sample}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	conditions = [("/", 1, True), ("/", 32, True), ("/hello/world", 1, True), ("/hello/world", 32, True),
				  ("/hello/world", 1, False)]
	results = []
	procs = {}
	try:
		for name in "ABC":
			procs[name] = start(name)
			results.append({"case": "rest", "impl": name, "rss_kib": tree_rss(procs[name].pid)})
		for rep in range(3):
			for route, concurrency, keepalive in conditions:
				for name in "ABC":
					r = measure(name, procs[name], route, concurrency, keepalive, rep == 0)
					row = {"case": "load", "rep": rep, "impl": name, "route": route, "concurrency": concurrency,
						   "keepalive": keepalive, **r}
					results.append(row)
					print(json.dumps(row), flush=True)
					# validate() has already refused anything incomplete, non-200 or mismatched
	finally:
		for p in procs.values():
			p.terminate()
			p.wait(timeout=15)
		(out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
	print("\nmedian over 3 repetitions (range):")
	for route, concurrency, keepalive in conditions:
		for name in "ABC":
			rows = [r for r in results if r["case"] == "load" and r["impl"] == name and r["route"] == route
					and r["concurrency"] == concurrency and r["keepalive"] == keepalive]
			rps = [r["rps"] for r in rows]
			p50 = statistics.median(r["p50_ms"] for r in rows)
			p99 = statistics.median(r["p99_ms"] for r in rows)
			print(f"{name} {route:13} c={concurrency:<2} keepalive={str(keepalive):5}: {statistics.median(rps):9.0f} req/s "
				  f"({min(rps):.0f}-{max(rps):.0f}); p50 {p50:.3f} ms; p99 {p99:.3f} ms; "
				  f"connections {rows[0].get('connections')}; rss {rows[0].get('rss_kib')} KiB")


def controls():
	"""Stubbed refusals: each malformed or failed run must be Refused, and a good one accepted."""
	good = {"summary": {"requestsPerSec": 100.0}, "latencyPercentiles": {"p50": 0.001, "p99": 0.002},
			"statusCodeDistribution": {"200": 1000}, "errorDistribution": {}}
	ok = True

	def expect(name, fn, refused):
		nonlocal ok
		try:
			fn()
			got = False
		except Refused as e:
			got = True
			name += f": {e}"
		good_verdict = got == refused
		ok &= good_verdict
		print(f"{'pass' if good_verdict else 'WRONG'}: {name}")

	def changed(**edits):
		r = json.loads(json.dumps(good))
		for path, value in edits.items():
			section, _, key = path.partition("__")
			if value is None:
				r[section].pop(key)
			else:
				r[section][key] = value
		return r
	expect("a complete good run", lambda: validate(good, 32, True, 32), False)
	expect("a missing p50", lambda: validate(changed(latencyPercentiles__p50=None), 32, True, 32), True)
	expect("a NaN p99", lambda: validate(changed(latencyPercentiles__p99=float("nan")), 32, True, 32), True)
	expect("zero requests per second", lambda: validate(changed(summary__requestsPerSec=0), 32, True, 32), True)
	expect("a 500 among the statuses", lambda: validate(changed(statusCodeDistribution__500=3), 32, True, 32), True)
	expect("an error reported", lambda: validate(changed(errorDistribution__timeout=1), 32, True, 32), True)
	expect("a missing summary", lambda: validate({k: v for k, v in good.items() if k != "summary"}, 32, True, 32), True)
	expect("a connection count below the concurrency", lambda: validate(good, 32, True, 31), True)
	expect("a missing connection sample", lambda: validate(good, 32, True, None), True)
	expect("no connection check without keep-alive", lambda: validate(good, 1, False, None), False)

	def failing_oha():
		saved = os.environ["PATH"]
		os.environ["PATH"] = "/nonexistent"
		try:
			oha(1, "/", 1, 1, True)
		except FileNotFoundError:
			raise Refused("oha could not run")
		finally:
			os.environ["PATH"] = saved
	expect("oha not runnable", failing_oha, True)
	expect("oha against a closed port (non-zero exit or errors)",
		   lambda: validate(oha(1, "/", 1, 1, True), 1, True, 1), True)
	return ok


if __name__ == "__main__":
	if sys.argv[1:] == ["--controls"]:
		sys.exit(0 if controls() else 1)
	main(sys.argv[1])
