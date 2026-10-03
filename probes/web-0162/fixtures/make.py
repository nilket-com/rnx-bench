"""rnx 0162: the skeleton site's exact behaviour, and its request/response fixtures.

	python3 fixtures/make.py      (writes fixtures/site.css, fixtures/home.html, fixtures/cases.json)

This is the specification the three implementations (A axum, B axum + Rune via rnx::server,
C Flask) must each reproduce byte for byte. Compared response headers are exactly
content-type, content-length, cache-control and allow (present with the given value, or
absent); date, server, connection and keep-alive are transport-generated and ignored by name;
any other header fails a comparison.

Routes: GET/HEAD /, /static/site.css, /hello/{name}, /contact; POST /contact. HEAD returns the
GET status and compared headers (content-length is the GET body's) with an empty body. Another
method on a known path is 405 with `allow`; an unknown path is 404. /hello/{name} takes one
non-empty path segment, percent-decoded as UTF-8 ('+' stays '+'); invalid UTF-8 is 400.
POST /contact decodes application/x-www-form-urlencoded: '&'-separated pairs, '+' as space,
percent escapes as UTF-8 (invalid is 400), the first of duplicate fields, a missing field as
empty. Every echoed text is HTML-escaped: & < > " ' as &amp; &lt; &gt; &quot; &#39;. The 404
page echoes the raw request path (as received, not decoded), escaped. Query strings are ignored.
"""
import json, pathlib, urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
HTML = "text/html; charset=utf-8"
CSS_TYPE = "text/css; charset=utf-8"

CSS = """:root { color-scheme: light dark; --ink: #1d1d1f; --paper: #fbfbfd; --accent: #3b5bdb; }
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.6 system-ui, sans-serif; color: var(--ink); background: var(--paper); }
header, main, footer { max-width: 46rem; margin: 0 auto; padding: 1rem; }
header { display: flex; justify-content: space-between; align-items: baseline; }
.brand { font-weight: 700; font-size: 1.25rem; text-decoration: none; color: var(--ink); }
nav a { margin-left: 1rem; color: var(--accent); }
h1 { line-height: 1.2; }
form label { display: block; margin: 0.75rem 0; }
footer { color: #6e6e73; font-size: 0.875rem; }
"""


def escape(text):
	return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
			.replace('"', "&quot;").replace("'", "&#39;"))


def page(title, body):
	return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
			"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
			f"<title>{title} · nilket</title>\n<link rel=\"stylesheet\" href=\"/static/site.css\">\n</head>\n<body>\n"
			"<header><a class=\"brand\" href=\"/\">nilket</a><nav><a href=\"/\">Home</a>"
			"<a href=\"/hello/world\">Hello</a><a href=\"/contact\">Contact</a></nav></header>\n"
			f"<main>\n{body}\n</main>\n<footer>© 2026 nilket</footer>\n</body>\n</html>\n")


FEATURES = [
	("Rune scripts, Rust speed", "Write small programs in Rune and run them on a Rust host."),
	("Batteries included", "JSON, files, paths, time, text, environment and HTTP are built in."),
	("DataFrames", "Polars is available as an adapter, with tables that read well."),
	("Tensors and models", "Candle runs small models on the CPU, from tensors to text embeddings."),
	("Notebooks", "A Jupyter kernel runs Rune cells, with HTML tables for frames and tensors."),
	("Bounded by design", "Every displayed value, request body and instruction count has a limit."),
	("Servers", "A Rust host can run Rune handlers with per-request ownership and budgets."),
	("Offline first", "After setup nothing reaches the network unless a program asks it to."),
]


def home():
	items = "\n".join(f"<li><strong>{escape(t)}</strong> {escape(d)}</li>" for t, d in FEATURES)
	sections = "\n".join(
		f"<section>\n<h2>{escape(t)}</h2>\n<p>{escape(d)} " + escape(d) * 3 + "</p>\n</section>" for t, d in FEATURES)
	body = ("<h1>nilket</h1>\n<p>Tools for working with data in Rune, on a Rust foundation.</p>\n"
			f"<ul>\n{items}\n</ul>\n{sections}")
	return page("Home", body)


def contact_form():
	return page("Contact", "<h1>Contact</h1>\n<form method=\"post\" action=\"/contact\">\n"
				"<label>Name <input name=\"name\"></label>\n<label>Message <textarea name=\"message\"></textarea></label>\n"
				"<button>Send</button>\n</form>")


def thanks(name, message):
	return page("Thanks", f"<h1>Thanks, {escape(name)}</h1>\n<p>You wrote: {escape(message)}</p>")


def hello(name):
	return page("Hello", f"<h1>Hello, {escape(name)}!</h1>\n<p>This page was made for you.</p>")


def not_found(raw_path):
	return page("Not found", f"<h1>Not found</h1>\n<p>No page at {escape(raw_path)}.</p>")


BAD = page("Bad request", "<h1>Bad request</h1>")
NOT_ALLOWED = page("Method not allowed", "<h1>Method not allowed</h1>")


def response(status, body, content_type=HTML, extra=None, head=False):
	data = body.encode()
	headers = {"content-type": content_type, "content-length": str(len(data))}
	headers.update(extra or {})
	return {"status": status, "headers": headers, "body": "" if head else body}


def decode_form(body):
	"""The specification's form decoding: None for invalid UTF-8."""
	fields = {}
	for pair in body.split("&") if body else []:
		key, _, value = pair.partition("=")
		try:
			key = urllib.parse.unquote_plus(key, errors="strict")
			value = urllib.parse.unquote_plus(value, errors="strict")
		except UnicodeDecodeError:
			return None
		fields.setdefault(key, value)
	return fields


def expected(method, target, body=""):
	path = target.split("?", 1)[0]
	head = method == "HEAD"
	if path == "/":
		if method not in ("GET", "HEAD"):
			return response(405, NOT_ALLOWED, extra={"allow": "GET, HEAD"})
		return response(200, home(), head=head)
	if path == "/static/site.css":
		if method not in ("GET", "HEAD"):
			return response(405, NOT_ALLOWED, extra={"allow": "GET, HEAD"})
		return response(200, CSS, CSS_TYPE, {"cache-control": "public, max-age=3600"}, head)
	if path == "/contact":
		if method == "POST":
			fields = decode_form(body)
			if fields is None:
				return response(400, BAD)
			return response(200, thanks(fields.get("name", ""), fields.get("message", "")))
		if method not in ("GET", "HEAD"):
			return response(405, NOT_ALLOWED, extra={"allow": "GET, HEAD, POST"})
		return response(200, contact_form(), head=head)
	segment = path[len("/hello/"):] if path.startswith("/hello/") else None
	if segment and "/" not in segment:
		if method not in ("GET", "HEAD"):
			return response(405, NOT_ALLOWED, extra={"allow": "GET, HEAD"})
		try:
			name = urllib.parse.unquote(segment, errors="strict")
		except UnicodeDecodeError:
			return response(400, BAD, head=head)
		return response(200, hello(name), head=head)
	return response(404, not_found(path), head=head)


FORM = "application/x-www-form-urlencoded"
CASES = [
	("GET", "/", None, None), ("HEAD", "/", None, None), ("POST", "/", FORM, ""),
	("GET", "/static/site.css", None, None), ("HEAD", "/static/site.css", None, None),
	("GET", "/hello/world", None, None), ("HEAD", "/hello/world", None, None),
	("GET", "/hello/J%C3%BCrgen", None, None), ("GET", "/hello/a+b%20c", None, None),
	("GET", "/hello/%3Cscript%3Ealert(1)%3C%2Fscript%3E", None, None),
	("GET", "/hello/a%22b%27c%26d%3E", None, None), ("GET", "/hello/%FF", None, None),
	("GET", "/hello/world?x=1", None, None), ("GET", "/hello/a/b", None, None), ("GET", "/hello/", None, None),
	("DELETE", "/hello/world", None, None),
	("GET", "/missing", None, None), ("GET", "/missing%3Cx%3E/%22q", None, None),
	("GET", "/contact", None, None), ("DELETE", "/contact", None, None),
	("POST", "/contact", FORM, "name=Ada+Lovelace&message=Hello%2C+%3Cb%3Eworld%3C%2Fb%3E%21"),
	("POST", "/contact", FORM, "name=Ada"),
	("POST", "/contact", FORM, "name=First&name=Second&message=two+names"),
	("POST", "/contact", FORM, "name=%FF&message=x"),
	("POST", "/contact", FORM, "name=%22%27%26&message=%3C%2Fp%3E%3Cscript%3Ex%3C%2Fscript%3E"),
	("POST", "/contact", FORM, ""),
]


def main():
	(HERE / "site.css").write_text(CSS)
	(HERE / "home.html").write_text(home())
	cases = []
	for method, target, content_type, body in CASES:
		request = {"method": method, "target": target}
		if content_type is not None:
			request["content_type"] = content_type
			request["body"] = body
		cases.append({"request": request, "response": expected(method, target, body or "")})
	(HERE / "cases.json").write_text(json.dumps(cases, indent="\t", ensure_ascii=False) + "\n")
	print(f"{len(cases)} cases; home page {len(home().encode())} bytes")


if __name__ == "__main__":
	main()
