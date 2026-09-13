//! Lifecycle probe for rnx record 0034, decision 3. A current-thread runtime,
//! one reqwest client, a loopback fixture on a std thread. Questions:
//!  1. after a successful request, how many tasks stay alive (pool)?
//!  2. after cancelling a second request by drop, does the fixture see EOF
//!     without extra runtime turns? with a bounded drain?
//!  3. after dropping the client, does a bounded drain reach zero tasks and
//!     does the fixture see EOF on the idle pooled socket?
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::mpsc;
use std::time::{Duration, Instant};

enum Seen { Accepted(usize), Eof(usize, Duration), ReadError(usize, String) }

fn fixture(tx: mpsc::Sender<Seen>) -> u16 {
	let listener = TcpListener::bind("127.0.0.1:0").unwrap();
	let port = listener.local_addr().unwrap().port();
	std::thread::spawn(move || {
		for (n, stream) in listener.incoming().enumerate() {
			let mut stream: TcpStream = stream.unwrap();
			let tx = tx.clone();
			tx.send(Seen::Accepted(n)).unwrap();
			std::thread::spawn(move || {
				let t0 = Instant::now();
				let mut buf = [0u8; 4096];
				loop {
					let read = match stream.read(&mut buf) {
						Ok(0) => { tx.send(Seen::Eof(n, t0.elapsed())).unwrap(); return; }
						Ok(read) => read,
						Err(e) => { tx.send(Seen::ReadError(n, e.to_string())).unwrap(); return; }
					};
					let req = String::from_utf8_lossy(&buf[..read]);
					if req.starts_with("GET /hang") { continue; } // never answer, keep reading
					let _ = stream.write_all(b"HTTP/1.1 200 OK\r\ncontent-length: 2\r\n\r\nok");
				}
			});
		}
	});
	port
}

fn drain(rt: &tokio::runtime::Runtime, bound: Duration, label: &str) -> usize {
	let t0 = Instant::now();
	let n = rt.block_on(async {
		loop {
			let n = tokio::runtime::Handle::current().metrics().num_alive_tasks();
			if n == 0 || t0.elapsed() > bound { break n; }
			tokio::time::sleep(Duration::from_millis(5)).await;
		}
	});
	println!("{label}: drained to {n} alive tasks in {:?}", t0.elapsed());
	n
}

fn seen(rx: &mpsc::Receiver<Seen>, wait: Duration) -> Vec<String> {
	let mut out = vec![];
	while let Ok(s) = rx.recv_timeout(wait) {
		out.push(match s { Seen::Accepted(n) => format!("accepted #{n}"), Seen::Eof(n, d) => format!("clean eof #{n} after {d:?}"), Seen::ReadError(n, e) => format!("READ ERROR #{n}: {e}") });
	}
	out
}

fn main() {
	let (tx, rx) = mpsc::channel();
	let port = fixture(tx.clone());
	let (tx2, rx2) = mpsc::channel();
	let hang_port = fixture(tx2);
	let _ = &tx;
	let rt = tokio::runtime::Builder::new_current_thread().enable_time().enable_io().build().unwrap();
	let alive = || rt.metrics().num_alive_tasks();
	let mut client = Some(reqwest::Client::builder().build().unwrap());
	println!("tasks before any request: {}", alive());

	// 1. success
	let body = rt.block_on(client.as_ref().unwrap().get(format!("http://127.0.0.1:{port}/ok")).send()).unwrap();
	let text = rt.block_on(body.text()).unwrap();
	println!("success: {text:?}; tasks alive after block_on returned: {}", alive());
	println!("fixture: {:?}", seen(&rx, Duration::from_millis(50)));

	// 2. cancel by drop: race a hanging request against a 50ms sleep, drop the loser
	rt.block_on(async {
		let req = client.as_ref().unwrap().get(format!("http://127.0.0.1:{hang_port}/hang")).send();
		tokio::select! { _ = req => println!("hang answered?!"), _ = tokio::time::sleep(Duration::from_millis(50)) => println!("cancelled by drop") }
	});
	println!("tasks alive right after cancel (healthy socket #0 still pooled on the first fixture): {}", alive());
	println!("hang fixture, no extra turns, 100ms wait: {:?}", seen(&rx2, Duration::from_millis(100)));
	let n = drain(&rt, Duration::from_millis(100), "drain after cancel (client kept)");
	println!("hang fixture after drain: {:?}", seen(&rx2, Duration::from_millis(100)));
	println!("first fixture after drain (pooled socket must still be open): {:?}", seen(&rx, Duration::from_millis(100)));

	// 2b. reuse still works with the kept client
	let r = rt.block_on(client.as_ref().unwrap().get(format!("http://127.0.0.1:{port}/ok")).send()).unwrap();
	rt.block_on(r.text()).unwrap();
	println!("reuse after cancel ok; fixture: {:?}; tasks {}", seen(&rx, Duration::from_millis(50)), alive());

	// 3. drop client, drain
	client = None;
	let _ = client;
	println!("tasks alive right after client drop, before any turn: {}", alive());
	println!("fixture, no turns, 100ms: {:?}", seen(&rx, Duration::from_millis(100)));
	let n2 = drain(&rt, Duration::from_millis(100), "drain after client drop");
	println!("first fixture after drain: {:?}", seen(&rx, Duration::from_millis(100)));
	println!("hang fixture after drain: {:?}", seen(&rx2, Duration::from_millis(100)));
	println!("SUMMARY kept-client drain left {n}; dropped-client drain left {n2}");
}
