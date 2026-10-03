"""rnx 0162 R3: B's per-phase cost on a short controlled sample, through the instrumented
host (PHASES=1), kept apart from the uninstrumented HTTP timings. One worker, sequential
requests on one keep-alive connection: 220 per route, the first 20 discarded as warm-up.

	python3 phases.py              the sample
	python3 phases.py --controls   the harness's own controls

Review of 0162 (R1): the server writes a phase event before each response, so its stderr goes
to a file, never an undrained pipe (a full pipe blocks the worker and the measurement then
depends on the pipe's capacity). The sample is refused unless there are exactly 660 valid,
finite phase records: 200 measured per route."""
import http.client, json, math, os, pathlib, statistics, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ROUTES = ["/", "/hello/world", "/static/site.css"]
PER_ROUTE, WARM = 220, 20
KEYS = ("prepare_us", "run_us", "convert_us", "close_us")


class Refused(Exception):
	pass


def server(port, stderr):
	return subprocess.Popen([str(HERE / "b/target/release/web0162-b"), str(HERE / "b/site.rn"), f"127.0.0.1:{port}"],
							env={"WORKERS": "1", "PHASES": "1"}, stdin=subprocess.DEVNULL,
							stdout=subprocess.DEVNULL, stderr=stderr)


def drive(port, timeout=30):
	time.sleep(1)
	conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
	for route in ROUTES:
		for _ in range(PER_ROUTE):
			conn.request("GET", route)
			r = conn.getresponse()
			r.read()
			if r.status != 200:
				raise Refused(f"{route}: status {r.status}")
	conn.close()


def summarize(lines):
	"""Exactly PER_ROUTE phase records per route, each complete and finite, or Refused."""
	events = []
	for line in lines:
		if line.startswith('{"event":"phases"'):
			e = json.loads(line)
			if not all(k in e and isinstance(e[k], (int, float)) and math.isfinite(e[k]) and e[k] >= 0 for k in KEYS):
				raise Refused(f"an incomplete or non-finite phase record: {line}")
			events.append(e)
	if len(events) != PER_ROUTE * len(ROUTES):
		raise Refused(f"{len(events)} phase records, expected {PER_ROUTE * len(ROUTES)}")
	out = {}
	for i, route in enumerate(ROUTES):
		measured = events[i * PER_ROUTE + WARM:(i + 1) * PER_ROUTE]
		assert len(measured) == PER_ROUTE - WARM
		out[route] = {k: round(statistics.median(e[k] for e in measured), 1) for k in KEYS}
	return out


def sample():
	with tempfile.TemporaryFile(mode="w+") as log:
		proc = server(18022, log)
		try:
			drive(18022)
		finally:
			proc.terminate()
			proc.wait(timeout=10)
		log.seek(0)
		lines = log.read().splitlines()
	for route, line in summarize(lines).items():
		print(f"{route}: median over {PER_ROUTE - WARM} requests (µs): {line}")


def controls():
	ok = True

	def expect(name, fn, refused):
		nonlocal ok
		try:
			fn()
			got = False
		except (Refused, TimeoutError, OSError) as e:
			got = True
			name += f": {type(e).__name__}: {str(e)[:80]}"
		good = got == refused
		ok &= good
		print(f"{'pass' if good else 'WRONG'}: {name}")
	good_line = '{"event":"phases","prepare_us":1.0,"run_us":1.0,"convert_us":1.0,"close_us":1.0}'
	full = [good_line] * (PER_ROUTE * len(ROUTES))
	expect("a complete stream is summarized", lambda: summarize(full), False)
	expect("a partial stream (one record short) is refused", lambda: summarize(full[:-1]), True)
	expect("a stream with an extra record is refused", lambda: summarize(full + [good_line]), True)
	expect("a non-finite record is refused", lambda: summarize(full[:-1] + [good_line.replace("1.0}", "NaN}")]), True)
	expect("a record missing a phase is refused", lambda: summarize(full[:-1] + ['{"event":"phases","prepare_us":1.0}']), True)

	# the hazard the file avoids: an undrained 4,096-byte pipe blocks the worker mid-sample
	def small_pipe():
		r, w = os.pipe()
		import fcntl
		fcntl.fcntl(w, 1031, 4096)  # F_SETPIPE_SZ
		proc = server(18023, w)
		os.close(w)
		try:
			drive(18023, timeout=5)
		finally:
			proc.kill()
			proc.wait(timeout=10)
			os.close(r)
	expect("an undrained 4,096-byte stderr pipe blocks the sample (the old harness's hazard)", small_pipe, True)
	return ok


if __name__ == "__main__":
	if sys.argv[1:] == ["--controls"]:
		sys.exit(0 if controls() else 1)
	sample()
