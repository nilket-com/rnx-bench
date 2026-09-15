//! A bounded local test server, not a notebook kernel.
use hmac::{Hmac, KeyInit, Mac};
use serde_json::{Value, json};
use sha2::Sha256;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering::SeqCst},
    },
    time::Duration,
};
use tokio::io::{AsyncBufReadExt, BufReader};
use zeromq::{Socket, SocketRecv, SocketSend, ZmqMessage};
static LARGEST: AtomicUsize = AtomicUsize::new(0);
struct Alloc;
unsafe impl GlobalAlloc for Alloc {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        LARGEST.fetch_max(l.size(), SeqCst);
        unsafe { System.alloc(l) }
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        unsafe { System.dealloc(p, l) }
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        LARGEST.fetch_max(n, SeqCst);
        unsafe { System.realloc(p, l, n) }
    }
}
#[global_allocator]
static ALLOC: Alloc = Alloc;
#[derive(Default)]
struct State {
    accepted: AtomicUsize,
    rejected: AtomicUsize,
    bad_sig: AtomicUsize,
    sent: AtomicUsize,
    blocked: AtomicUsize,
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
async fn router(
    mut socket: zeromq::RouterSocket,
    key: Arc<Vec<u8>>,
    state: Arc<State>,
    publish: tokio::sync::mpsc::Sender<usize>,
) {
    while let Ok(message) = socket.recv().await {
        // Deliberately application-side checks, after the library received it.
        if message.len() > 32 || message.iter().map(|f| f.len()).sum::<usize>() > 1024 * 1024 {
            state.rejected.fetch_add(1, SeqCst);
            continue;
        }
        let Some(d) = message.iter().position(|f| f.as_ref() == b"<IDS|MSG>") else {
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
        out.push(signature(&key, &reply).into());
        out.extend(reply.into_iter().map(Into::into));
        if socket
            .send(ZmqMessage::try_from(out).unwrap())
            .await
            .is_err()
        {
            break;
        }
    }
}
#[tokio::main(flavor = "multi_thread", worker_threads = 2)]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let key = Arc::new(if std::env::args().nth(1).as_deref() == Some("empty") {
        Vec::new()
    } else {
        b"local-probe-key".to_vec()
    });
    let state = Arc::new(State::default());
    let mut shell = zeromq::RouterSocket::new();
    let a = shell.bind("tcp://127.0.0.1:0").await?;
    let mut control = zeromq::RouterSocket::new();
    let b = control.bind("tcp://127.0.0.1:0").await?;
    let mut stdin = zeromq::RouterSocket::new();
    let c = stdin.bind("tcp://127.0.0.1:0").await?;
    let mut hb = zeromq::RepSocket::new();
    let d = hb.bind("tcp://127.0.0.1:0").await?;
    let mut publisher = zeromq::PubSocket::new();
    let e = publisher.bind("tcp://127.0.0.1:0").await?;
    let (tx, mut rx) = tokio::sync::mpsc::channel(8);
    tokio::spawn(router(shell, key.clone(), state.clone(), tx.clone()));
    tokio::spawn(router(control, key.clone(), state.clone(), tx.clone()));
    tokio::spawn(router(stdin, key.clone(), state.clone(), tx));
    tokio::spawn(async move {
        while let Ok(m) = hb.recv().await {
            if hb.send(m).await.is_err() {
                break;
            }
        }
    });
    let stats = state.clone();
    tokio::spawn(async move {
        while let Some(n) = rx.recv().await {
            for _ in 0..n {
                let frames: Vec<bytes::Bytes> =
                    vec![b"probe".to_vec().into(), vec![b'x'; 16384].into()];
                let msg = ZmqMessage::try_from(frames).unwrap();
                match tokio::time::timeout(Duration::from_millis(250), publisher.send(msg)).await {
                    Ok(Ok(())) => {
                        stats.sent.fetch_add(1, SeqCst);
                    }
                    _ => {
                        stats.blocked.fetch_add(1, SeqCst);
                        break;
                    }
                }
            }
        }
    });
    emit(
        json!({"shell":a.to_string(),"control":b.to_string(),"stdin":c.to_string(),"hb":d.to_string(),"iopub":e.to_string()}),
    );
    let mut lines = BufReader::new(tokio::io::stdin()).lines();
    while let Some(line) = lines.next_line().await? {
        if line == "stop" {
            break;
        }
        let max = LARGEST.load(SeqCst);
        if line == "reset_alloc" {
            LARGEST.store(0, SeqCst);
        }
        emit(
            json!({"largest_allocation_request":max,"accepted":state.accepted.load(SeqCst),"rejected":state.rejected.load(SeqCst),"bad_signature":state.bad_sig.load(SeqCst),"pub_send_ok":state.sent.load(SeqCst),"pub_send_timeout_or_error":state.blocked.load(SeqCst)}),
        );
    }
    Ok(())
}
