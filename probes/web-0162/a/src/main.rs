//! rnx 0162, implementation A: the skeleton site in axum alone, the performance ceiling.
//! One fallback handler dispatches on the raw path so 405 `allow`, decoding and the 404 echo
//! follow the probe's specification exactly (axum's own method routing formats `allow`
//! differently). The home page and CSS are built once at start-up.
use axum::{
	body::{Body, to_bytes},
	extract::Request,
	http::{Method, header},
	response::Response,
};
use std::sync::OnceLock;

const HTML: &str = "text/html; charset=utf-8";
static CSS: OnceLock<String> = OnceLock::new();
static HOME: OnceLock<String> = OnceLock::new();

fn escape(s: &str) -> String {
	let mut out = String::with_capacity(s.len());
	for c in s.chars() {
		match c {
			'&' => out.push_str("&amp;"),
			'<' => out.push_str("&lt;"),
			'>' => out.push_str("&gt;"),
			'"' => out.push_str("&quot;"),
			'\'' => out.push_str("&#39;"),
			c => out.push(c),
		}
	}
	out
}

fn page(title: &str, body: &str) -> String {
	format!(
		"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n\
		<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\
		<title>{title} · nilket</title>\n<link rel=\"stylesheet\" href=\"/static/site.css\">\n</head>\n<body>\n\
		<header><a class=\"brand\" href=\"/\">nilket</a><nav><a href=\"/\">Home</a>\
		<a href=\"/hello/world\">Hello</a><a href=\"/contact\">Contact</a></nav></header>\n\
		<main>\n{body}\n</main>\n<footer>© 2026 nilket</footer>\n</body>\n</html>\n"
	)
}

fn respond(status: u16, body: String, content_type: &str, extra: &[(&str, &str)]) -> Response {
	let mut r = Response::builder().status(status).header(header::CONTENT_TYPE, content_type);
	for (k, v) in extra {
		r = r.header(*k, *v);
	}
	r.body(Body::from(body)).unwrap()
}

fn html(status: u16, body: String) -> Response {
	respond(status, body, HTML, &[])
}

fn not_allowed(allow: &str) -> Response {
	respond(405, page("Method not allowed", "<h1>Method not allowed</h1>"), HTML, &[("allow", allow)])
}

fn bad() -> Response {
	html(400, page("Bad request", "<h1>Bad request</h1>"))
}

fn decode(s: &str) -> Option<String> {
	percent_encoding::percent_decode_str(s).decode_utf8().ok().map(|c| c.into_owned())
}

fn form(body: &str) -> Option<Vec<(String, String)>> {
	let mut fields: Vec<(String, String)> = Vec::new();
	for pair in body.split('&').filter(|_| !body.is_empty()) {
		let (k, v) = pair.split_once('=').unwrap_or((pair, ""));
		let (k, v) = (decode(&k.replace('+', " "))?, decode(&v.replace('+', " "))?);
		if !fields.iter().any(|(name, _)| *name == k) {
			fields.push((k, v));
		}
	}
	Some(fields)
}

fn field<'a>(fields: &'a [(String, String)], name: &str) -> &'a str {
	fields.iter().find(|(k, _)| k == name).map_or("", |(_, v)| v.as_str())
}

async fn site(req: Request) -> Response {
	let path = req.uri().path().to_owned();
	let method = req.method().clone();
	let reading = method == Method::GET || method == Method::HEAD;
	match path.as_str() {
		"/" if reading => html(200, HOME.get().unwrap().clone()),
		"/" | "/static/site.css" if !reading => not_allowed("GET, HEAD"),
		"/static/site.css" => respond(
			200,
			CSS.get().unwrap().clone(),
			"text/css; charset=utf-8",
			&[("cache-control", "public, max-age=3600")],
		),
		"/contact" if method == Method::POST => {
			let Ok(bytes) = to_bytes(req.into_body(), 1 << 20).await else { return bad() };
			let Some(fields) = std::str::from_utf8(&bytes).ok().and_then(form) else { return bad() };
			let body = format!(
				"<h1>Thanks, {}</h1>\n<p>You wrote: {}</p>",
				escape(field(&fields, "name")),
				escape(field(&fields, "message"))
			);
			html(200, page("Thanks", &body))
		}
		"/contact" if reading => html(
			200,
			page(
				"Contact",
				"<h1>Contact</h1>\n<form method=\"post\" action=\"/contact\">\n\
				<label>Name <input name=\"name\"></label>\n<label>Message <textarea name=\"message\"></textarea></label>\n\
				<button>Send</button>\n</form>",
			),
		),
		"/contact" => not_allowed("GET, HEAD, POST"),
		p => match p.strip_prefix("/hello/").filter(|s| !s.is_empty() && !s.contains('/')) {
			Some(_) if !reading => not_allowed("GET, HEAD"),
			Some(segment) => match decode(segment) {
				Some(name) => html(
					200,
					page("Hello", &format!("<h1>Hello, {}!</h1>\n<p>This page was made for you.</p>", escape(&name))),
				),
				None => bad(),
			},
			None => html(404, page("Not found", &format!("<h1>Not found</h1>\n<p>No page at {}.</p>", escape(p)))),
		},
	}
}

fn main() {
	let fixtures = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../fixtures");
	CSS.set(std::fs::read_to_string(fixtures.join("site.css")).unwrap()).unwrap();
	HOME.set(std::fs::read_to_string(fixtures.join("home.html")).unwrap()).unwrap();
	let threads: usize = std::env::var("WORKERS").map_or(2, |v| v.parse().unwrap());
	let bind = std::env::args().nth(1).unwrap_or("127.0.0.1:18001".into());
	let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(threads).enable_all().build().unwrap();
	rt.block_on(async {
		let listener = tokio::net::TcpListener::bind(&bind).await.unwrap();
		let app = axum::Router::new().fallback(site);
		axum::serve(listener, app).await.unwrap();
	});
}
