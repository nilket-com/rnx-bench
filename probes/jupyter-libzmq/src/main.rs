//! A bounded local test server, not a notebook kernel.
use hmac::{Hmac, KeyInit, Mac};
use serde_json::{Value, json};
use sha2::Sha256;
use std::{
    io::BufRead,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst},
    },
    time::Duration,
};
#[derive(Default)]
struct State {
    accepted: AtomicUsize,
    rejected: AtomicUsize,
    bad_sig: AtomicUsize,
    sent: AtomicUsize,
    blocked: AtomicUsize,
    parts: AtomicUsize,
}
fn emit(v: Value) {
    use std::io::Write;
    let mut o = std::io::stdout().lock();
    writeln!(o, "{v}").unwrap();
    o.flush().unwrap();
}
fn signature(key: &[u8], frames: &[Vec<u8>]) -> Vec<u8> {
    if key.is_empty() {
        return Vec::new();
    }
    let mut mac = Hmac::<Sha256>::new_from_slice(key).unwrap();
    for f in frames {
        mac.update(f);
    }
    hex::encode(mac.finalize().into_bytes()).into_bytes()
}
fn router(
    socket: zmq::Socket,
    key: Arc<Vec<u8>>,
    state: Arc<State>,
    publish: std::sync::mpsc::SyncSender<usize>,
    stop: Arc<AtomicBool>,
) {
    let mut message: Vec<Vec<u8>> = Vec::new();
    let mut bytes = 0;
    let mut discard = false;
    while !stop.load(SeqCst) {
        let part = match socket.recv_bytes(0) {
            Ok(p) => p,
            Err(zmq::Error::EAGAIN) => continue,
            Err(_) => break,
        };
        state.parts.fetch_add(1, SeqCst);
        bytes += part.len();
        let more = socket.get_rcvmore().unwrap();
        if bytes > 1024 * 1024 || message.len() >= 32 {
            discard = true;
        }
        if !discard {
            message.push(part);
        }
        if more {
            continue;
        }
        bytes = 0;
        if discard {
            state.rejected.fetch_add(1, SeqCst);
            message.clear();
            discard = false;
            continue;
        }
        let message = std::mem::take(&mut message);
        let Some(d) = message.iter().position(|f| f.as_slice() == b"<IDS|MSG>") else {
            state.rejected.fetch_add(1, SeqCst);
            continue;
        };
        if message.len() != d + 6 {
            state.rejected.fetch_add(1, SeqCst);
            continue;
        }
        let frames: Vec<Vec<u8>> = message.iter().skip(d + 2).map(|f| f.to_vec()).collect();
        let valid = if key.is_empty() {
            message.get(d + 1).unwrap().is_empty()
        } else {
            let mut mac = Hmac::<Sha256>::new_from_slice(&key).unwrap();
            for f in &frames {
                mac.update(f);
            }
            hex::decode(message.get(d + 1).unwrap())
                .ok()
                .is_some_and(|s| mac.verify_slice(&s).is_ok())
        };
        if !valid {
            state.bad_sig.fetch_add(1, SeqCst);
            continue;
        }
        let parsed: Result<Vec<Value>, _> =
            frames.iter().map(|f| serde_json::from_slice(f)).collect();
        let Ok(v) = parsed else {
            state.rejected.fetch_add(1, SeqCst);
            continue;
        };
        if v.iter().any(|v| !v.is_object()) {
            state.rejected.fetch_add(1, SeqCst);
            continue;
        }
        state.accepted.fetch_add(1, SeqCst);
        if let Some(n) = v[3]["publish"].as_u64() {
            let _ = publish.try_send((n as usize).min(20000));
        }
        let reply=vec![serde_json::to_vec(&json!({"msg_id":uuid::Uuid::new_v4().to_string(),"session":"transport-probe","username":"probe","date":"2026-09-14T00:00:00Z","msg_type":"probe_reply","version":"5.4"})).unwrap(),frames[0].clone(),b"{}".to_vec(),serde_json::to_vec(&json!({"status":"ok","echo":v[3]})).unwrap()];
        let mut out: Vec<_> = message.iter().take(d + 1).cloned().collect();
        out.push(signature(&key, &reply));
        out.extend(reply);
        if socket.send_multipart(out, 0).is_err() {
            break;
        }
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let ctx = zmq::Context::new();
    let state = Arc::new(State::default());
    let stop = Arc::new(AtomicBool::new(false));
    let key = Arc::new(if std::env::args().nth(1).as_deref() == Some("empty") {
        vec![]
    } else {
        b"local-probe-key".to_vec()
    });
    let (tx, rx) = std::sync::mpsc::sync_channel(8);
    let mut addresses = serde_json::Map::new();
    addresses.insert("libzmq".into(), json!(zmq::version()));
    let mut threads = vec![];
    for (name, kind) in [
        ("shell", zmq::ROUTER),
        ("control", zmq::ROUTER),
        ("stdin", zmq::ROUTER),
        ("hb", zmq::REP),
        ("iopub", zmq::PUB),
    ] {
        let socket = ctx.socket(kind)?;
        socket.set_maxmsgsize(1024 * 1024)?;
        socket.set_rcvhwm(64)?;
        socket.set_sndhwm(64)?;
        socket.set_linger(0)?;
        socket.set_rcvtimeo(20)?;
        socket.set_sndtimeo(100)?;
        socket.bind("tcp://127.0.0.1:*")?;
        addresses.insert(name.into(), json!(socket.get_last_endpoint()?.unwrap()));
        let st = state.clone();
        let done = stop.clone();
        let k = key.clone();
        let pubtx = tx.clone();
        if name == "iopub" {
            // Publisher moved below; each socket has a single owning thread.
            let rx = rx;
            threads.push(std::thread::spawn(move || {
                while !done.load(SeqCst) {
                    if let Ok(n) = rx.recv_timeout(Duration::from_millis(20)) {
                        for _ in 0..n {
                            if done.load(SeqCst) {
                                break;
                            }
                            match socket.send_multipart(
                                [b"probe".as_slice(), vec![b'x'; 16384].as_slice()],
                                0,
                            ) {
                                Ok(()) => {
                                    st.sent.fetch_add(1, SeqCst);
                                }
                                Err(_) => {
                                    st.blocked.fetch_add(1, SeqCst);
                                }
                            }
                        }
                    }
                }
            }));
            break;
        } else if name == "hb" {
            threads.push(std::thread::spawn(move || {
                while !done.load(SeqCst) {
                    if let Ok(m) = socket.recv_bytes(0) {
                        let _ = socket.send(m, 0);
                    }
                }
            }));
        } else {
            threads.push(std::thread::spawn(move || {
                router(socket, k, st, pubtx, done)
            }));
        }
    }
    emit(Value::Object(addresses));
    for line in std::io::stdin().lock().lines() {
        if line? == "stop" {
            break;
        }
        emit(
            json!({"parts_received":state.parts.load(SeqCst),"accepted":state.accepted.load(SeqCst),"rejected":state.rejected.load(SeqCst),"bad_signature":state.bad_sig.load(SeqCst),"pub_send_ok":state.sent.load(SeqCst),"pub_send_timeout_or_error":state.blocked.load(SeqCst)}),
        );
    }
    stop.store(true, SeqCst);
    for t in threads {
        t.join().unwrap();
    }
    drop(ctx);
    Ok(())
}
