//! rnx 0162, implementation B: a prototype axum host whose every request runs a Rune handler
//! through rnx::server (record 0056), keeping the lifecycle of servers/http-postgres: the program
//! is compiled once; per request the axum handler builds an owned request and sends it through a
//! bounded queue (full: 503) to one of W worker threads, each a current-thread runtime with a
//! LocalSet and at most 4 active invocations, which prepares the invocation on its own thread,
//! runs it, converts the response to owned data while its values are valid, and closes it
//! explicitly on success and failure. No unsafe Send. Not product code.
//!
//!   WORKERS=2 [PHASES=1] web0162-b PROGRAM.rn [ADDRESS]
use axum::{
	body::{Body, to_bytes},
	extract::{Request, State},
	response::Response,
};
use rnx::{Extensions, rune, server::Program};
use std::{
	collections::BTreeMap,
	sync::{
		Arc,
		atomic::{AtomicUsize, Ordering},
	},
	thread,
	time::Instant,
};
use tokio::{
	sync::{mpsc, oneshot},
	task::{JoinSet, LocalSet},
};

const BUDGET: usize = 10_000_000;
const QUEUE: usize = 16;
const ACTIVE: usize = 4;
const LIMIT: usize = 1 << 20;

struct Input {
	method: String,
	path: String,
	query: Option<String>,
	headers: BTreeMap<String, Vec<Vec<u8>>>,
	body: Vec<u8>,
}
impl Input {
	/// The request value, built on the worker's thread (as servers/http-postgres does).
	fn rune(self) -> rune::Value {
		let key = |k: &str| rune::alloc::String::try_from(k).unwrap();
		let mut obj = rune::runtime::Object::new();
		obj.insert(key("method"), rune::to_value(self.method).unwrap()).unwrap();
		obj.insert(key("path"), rune::to_value(self.path).unwrap()).unwrap();
		let query = match self.query {
			Some(v) => rune::to_value(v).unwrap(),
			None => rune::to_value(()).unwrap(),
		};
		obj.insert(key("query"), query).unwrap();
		let mut headers = rune::runtime::Object::new();
		for (k, vs) in self.headers {
			let mut values = rune::runtime::Vec::new();
			for v in vs {
				values.push(rune::to_value(rune::runtime::Bytes::from_slice(v).unwrap()).unwrap()).unwrap();
			}
			headers.insert(key(&k), rune::to_value(values).unwrap()).unwrap();
		}
		obj.insert(key("headers"), rune::to_value(headers).unwrap()).unwrap();
		let body = rune::to_value(rune::runtime::Bytes::from_slice(self.body).unwrap()).unwrap();
		obj.insert(key("body"), body).unwrap();
		rune::to_value(obj).unwrap()
	}
}

struct Output {
	status: u16,
	headers: Vec<(String, Vec<u8>)>,
	body: Vec<u8>,
}

fn text_or_bytes(v: &rune::Value) -> Result<Vec<u8>, String> {
	if let Ok(s) = v.borrow_string_ref() {
		return Ok(s.as_bytes().to_vec());
	}
	Ok(v.borrow_ref::<rune::runtime::Bytes>().map_err(|e| e.to_string())?.to_vec())
}

/// The handler's #{status, headers, body} as owned data, while its values are valid.
fn decode(value: rune::Value) -> Result<Output, String> {
	let obj = value.borrow_ref::<rune::runtime::Object>().map_err(|e| e.to_string())?;
	if obj.len() != 3 || !["status", "headers", "body"].iter().all(|k| obj.get(*k).is_some()) {
		return Err("response fields".into());
	}
	let status = obj.get("status").unwrap().as_integer::<i64>().map_err(|e| e.to_string())?;
	if !(200..=599).contains(&status) {
		return Err("status".into());
	}
	let body = text_or_bytes(obj.get("body").unwrap())?;
	if body.len() > LIMIT {
		return Err("body".into());
	}
	let mut headers = Vec::new();
	let h = obj.get("headers").unwrap().borrow_ref::<rune::runtime::Object>().map_err(|e| e.to_string())?;
	for (k, vs) in h.iter() {
		for v in vs.borrow_ref::<rune::runtime::Vec>().map_err(|e| e.to_string())?.iter() {
			headers.push((k.as_str().to_owned(), text_or_bytes(v)?));
		}
	}
	Ok(Output { status: status as u16, headers, body })
}

fn failed() -> Output {
	Output { status: 500, headers: vec![], body: b"handler failed".to_vec() }
}

struct Job {
	input: Input,
	reply: oneshot::Sender<Output>,
}

async fn handle(n: usize, job: Job, program: Program, phases: bool) {
	let t0 = Instant::now();
	let mut invocation = match program.prepare(Extensions::none(), "main", job.input.rune(), BUDGET) {
		Ok(invocation) => invocation,
		Err(error) => {
			eprintln!("{{\"event\":\"prepare_error\",\"worker\":{n},\"category\":\"{}\"}}", error.category());
			if error.category() == "cleanup" {
				panic!("context cleanup failed");
			}
			let _ = job.reply.send(failed());
			return;
		}
	};
	let t1 = Instant::now();
	let ran = invocation.run().await;
	let t2 = Instant::now();
	let result = ran.map_err(|e| format!("{}: {}", e.category(), e.message())).and_then(decode);
	let t3 = Instant::now();
	let close = invocation.close();
	let t4 = Instant::now();
	let output = match (result, close) {
		(Ok(output), Ok(())) => output,
		(result, close) => {
			let reason = result.err().unwrap_or_default();
			let category = close.as_ref().err().map(|e| e.category()).unwrap_or("closed");
			eprintln!("{{\"event\":\"handler_error\",\"worker\":{n},\"reason\":{reason:?},\"close\":\"{category}\"}}");
			if category == "cleanup" {
				panic!("handler lifecycle state lost");
			}
			failed()
		}
	};
	if phases {
		let us = |a: Instant, b: Instant| (b - a).as_secs_f64() * 1e6;
		eprintln!(
			"{{\"event\":\"phases\",\"prepare_us\":{:.1},\"run_us\":{:.1},\"convert_us\":{:.1},\"close_us\":{:.1}}}",
			us(t0, t1),
			us(t1, t2),
			us(t2, t3),
			us(t3, t4)
		);
	}
	let _ = job.reply.send(output);
}

fn worker(n: usize, mut jobs: mpsc::Receiver<Job>, program: Program, phases: bool) {
	let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
	LocalSet::new().block_on(&rt, async move {
		let mut tasks = JoinSet::new();
		loop {
			tokio::select! {
				job = jobs.recv(), if tasks.len() < ACTIVE => match job {
					None => break,
					Some(job) => { tasks.spawn_local(handle(n, job, program.clone(), phases)); }
				},
				r = tasks.join_next(), if !tasks.is_empty() => { r.unwrap().unwrap(); }
			}
		}
		while let Some(r) = tasks.join_next().await {
			r.unwrap();
		}
	});
}

struct Hub {
	workers: Vec<mpsc::Sender<Job>>,
	next: AtomicUsize,
}

async fn site(State(hub): State<Arc<Hub>>, req: Request) -> Response {
	let (parts, body) = req.into_parts();
	let Ok(body) = to_bytes(body, LIMIT).await else {
		return Response::builder().status(413).body(Body::empty()).unwrap();
	};
	let mut headers: BTreeMap<String, Vec<Vec<u8>>> = BTreeMap::new();
	for (k, v) in parts.headers.iter() {
		headers.entry(k.as_str().to_owned()).or_default().push(v.as_bytes().to_vec());
	}
	let input = Input {
		method: parts.method.as_str().to_owned(),
		path: parts.uri.path().to_owned(),
		query: parts.uri.query().map(str::to_owned),
		headers,
		body: body.to_vec(),
	};
	let (reply, answer) = oneshot::channel();
	let mut job = Job { input, reply };
	let start = hub.next.fetch_add(1, Ordering::Relaxed);
	let mut sent = false;
	for i in 0..hub.workers.len() {
		match hub.workers[(start + i) % hub.workers.len()].try_send(job) {
			Ok(()) => {
				sent = true;
				break;
			}
			Err(mpsc::error::TrySendError::Full(j)) | Err(mpsc::error::TrySendError::Closed(j)) => job = j,
		}
	}
	if !sent {
		return Response::builder().status(503).body(Body::empty()).unwrap();
	}
	let out = answer.await.unwrap_or_else(|_| failed());
	let mut r = Response::builder().status(out.status);
	for (k, v) in out.headers {
		r = r.header(k, v);
	}
	r.body(Body::from(out.body)).unwrap()
}

fn main() {
	let mut args = std::env::args().skip(1);
	let program_path = args.next().expect("PROGRAM.rn");
	let bind = args.next().unwrap_or("127.0.0.1:18002".into());
	let threads: usize = std::env::var("WORKERS").map_or(2, |v| v.parse().unwrap());
	let phases = std::env::var("PHASES").is_ok();
	let program = Program::compile(&program_path, Extensions::none()).unwrap_or_else(|e| panic!("{e}"));
	let mut workers = Vec::new();
	for n in 0..threads {
		let (tx, rx) = mpsc::channel(QUEUE);
		let program = program.clone();
		thread::spawn(move || worker(n, rx, program, phases));
		workers.push(tx);
	}
	let hub = Arc::new(Hub { workers, next: AtomicUsize::new(0) });
	// the acceptor: axum on its own runtime, one thread (the Rune work runs on the workers)
	let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(1).enable_all().build().unwrap();
	rt.block_on(async {
		let listener = tokio::net::TcpListener::bind(&bind).await.unwrap();
		let app = axum::Router::new().fallback(site).with_state(hub);
		axum::serve(listener, app).await.unwrap();
	});
}
