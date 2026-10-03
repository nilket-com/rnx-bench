"""rnx 0162: every fixture against a live implementation, before any timing.

	python3 check.py http://127.0.0.1:PORT

Each case is sent over HTTP/1.1 (a fresh connection per case, with http.client). The status, the
compared headers (content-type, content-length, cache-control, allow: each present with its
value, or absent) and the body bytes must equal fixtures/cases.json. date, server, connection
and keep-alive are ignored by name; any other response header fails. Exit 1 on any mismatch."""
import http.client, json, pathlib, sys, urllib.parse

COMPARED = ("content-type", "content-length", "cache-control", "allow")
IGNORED = ("date", "server", "connection", "keep-alive")


def run(base):
	url = urllib.parse.urlsplit(base)
	cases = json.loads((pathlib.Path(__file__).parent / "fixtures/cases.json").read_text())
	failed = 0
	for case in cases:
		req, want = case["request"], case["response"]
		conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
		headers = {}
		body = None
		if "body" in req:
			body = req["body"].encode()
			headers["content-type"] = req["content_type"]
		conn.request(req["method"], req["target"], body=body, headers=headers)
		resp = conn.getresponse()
		got_body = resp.read().decode("utf-8", "replace")
		got = {k.lower(): v for k, v in resp.getheaders()}
		conn.close()
		problems = []
		if resp.status != want["status"]:
			problems.append(f"status {resp.status} != {want['status']}")
		for name in COMPARED:
			if got.get(name) != want["headers"].get(name):
				problems.append(f"{name}: {got.get(name)!r} != {want['headers'].get(name)!r}")
		extra = sorted(set(got) - set(COMPARED) - set(IGNORED))
		if extra:
			problems.append(f"unexpected headers {extra}")
		if got_body != want["body"]:
			problems.append(f"body differs ({len(got_body)} vs {len(want['body'])} chars)")
		label = f"{req['method']} {req['target']}" + (f" [{req['body']}]" if "body" in req else "")
		if problems:
			failed += 1
			print(f"FAIL {label}: " + "; ".join(problems))
	print(f"{len(cases) - failed}/{len(cases)} cases match")
	return failed == 0


if __name__ == "__main__":
	sys.exit(0 if run(sys.argv[1]) else 1)
