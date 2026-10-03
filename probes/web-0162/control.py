"""rnx 0162 R3: B's lifecycle control. One worker; a handler panic, a budget exhaustion and an
invalid response each return 500 with the invocation closed, and a healthy request on the same
worker follows each.

	python3 control.py   (starts and stops B with b/control.rn)"""
import http.client, json, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent


def get(path):
	conn = http.client.HTTPConnection("127.0.0.1", 18012, timeout=60)
	conn.request("GET", path)
	r = conn.getresponse()
	body = r.read()
	conn.close()
	return r.status, body


server = subprocess.Popen([str(HERE / "b/target/release/web0162-b"), str(HERE / "b/control.rn"), "127.0.0.1:18012"],
						  env={"WORKERS": "1"}, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
	time.sleep(1)
	sequence = [("/ok", 200), ("/panic", 500), ("/ok", 200), ("/loop", 500), ("/ok", 200), ("/refuse", 500), ("/ok", 200)]
	results = []
	for path, want in sequence:
		start = time.perf_counter()
		status, body = get(path)
		results.append((path, status, round((time.perf_counter() - start) * 1000, 1)))
		assert status == want, (path, status, body)
	assert server.poll() is None, "the server exited"
finally:
	server.terminate()
	_, err = server.communicate(timeout=10)
events = [json.loads(l) for l in err.splitlines() if l.startswith("{")]
for path, status, ms in results:
	print(f"{path}: {status} in {ms} ms")
for e in events:
	print(e)
assert [e["reason"].split(":")[0] for e in events] == ["vm", "vm", "status"], events
print("control ok: every failure returned 500 with its invocation closed, and the same worker served the next request")
