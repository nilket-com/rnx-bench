"""rnx 0162, implementation C: the skeleton site in Flask, under gunicorn (gthread).
Routes dispatch on the raw request target (gunicorn's RAW_URI) so decoding, 405 `allow` and the
404 echo follow the probe's specification exactly; idiomatic Flask routing would differ in
`allow` (it adds OPTIONS) and in how it decodes invalid UTF-8."""
import pathlib, urllib.parse
from flask import Flask, Response, request

HERE = pathlib.Path(__file__).resolve().parent.parent / "fixtures"
CSS = (HERE / "site.css").read_text()
HOME = (HERE / "home.html").read_text()
HTML = "text/html; charset=utf-8"
app = Flask(__name__, static_folder=None)  # the CSS is served by the site route, as in A and B


def escape(s):
	return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def page(title, body):
	return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
			"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
			f"<title>{title} · nilket</title>\n<link rel=\"stylesheet\" href=\"/static/site.css\">\n</head>\n<body>\n"
			"<header><a class=\"brand\" href=\"/\">nilket</a><nav><a href=\"/\">Home</a>"
			"<a href=\"/hello/world\">Hello</a><a href=\"/contact\">Contact</a></nav></header>\n"
			f"<main>\n{body}\n</main>\n<footer>© 2026 nilket</footer>\n</body>\n</html>\n")


CONTACT = page("Contact", "<h1>Contact</h1>\n<form method=\"post\" action=\"/contact\">\n"
			   "<label>Name <input name=\"name\"></label>\n<label>Message <textarea name=\"message\"></textarea></label>\n"
			   "<button>Send</button>\n</form>")
BAD = page("Bad request", "<h1>Bad request</h1>")
NOT_ALLOWED = page("Method not allowed", "<h1>Method not allowed</h1>")


def respond(status, body, content_type=HTML, **headers):
	return Response(body, status, {"content-type": content_type, **headers})


def form(body):
	fields = {}
	for pair in body.split("&") if body else []:
		key, _, value = pair.partition("=")
		fields.setdefault(urllib.parse.unquote_plus(key, errors="strict"), urllib.parse.unquote_plus(value, errors="strict"))
	return fields


def site(_path=""):
	path = request.environ["RAW_URI"].split("?", 1)[0]
	method = request.method
	reading = method in ("GET", "HEAD")
	if path == "/":
		return respond(200, HOME) if reading else respond(405, NOT_ALLOWED, allow="GET, HEAD")
	if path == "/static/site.css":
		if not reading:
			return respond(405, NOT_ALLOWED, allow="GET, HEAD")
		return respond(200, CSS, "text/css; charset=utf-8", **{"cache-control": "public, max-age=3600"})
	if path == "/contact":
		if method == "POST":
			try:
				fields = form(request.get_data().decode("ascii"))
			except UnicodeDecodeError:
				return respond(400, BAD)
			body = f"<h1>Thanks, {escape(fields.get('name', ''))}</h1>\n<p>You wrote: {escape(fields.get('message', ''))}</p>"
			return respond(200, page("Thanks", body))
		return respond(200, CONTACT) if reading else respond(405, NOT_ALLOWED, allow="GET, HEAD, POST")
	segment = path[len("/hello/"):] if path.startswith("/hello/") else ""
	if segment and "/" not in segment:
		if not reading:
			return respond(405, NOT_ALLOWED, allow="GET, HEAD")
		try:
			name = urllib.parse.unquote(segment, errors="strict")
		except UnicodeDecodeError:
			return respond(400, BAD)
		return respond(200, page("Hello", f"<h1>Hello, {escape(name)}!</h1>\n<p>This page was made for you.</p>"))
	return respond(404, page("Not found", f"<h1>Not found</h1>\n<p>No page at {escape(path)}.</p>"))


site.provide_automatic_options = False
METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
app.add_url_rule("/", "root", site, methods=METHODS)
app.add_url_rule("/<path:_path>", "site", site, methods=METHODS)
