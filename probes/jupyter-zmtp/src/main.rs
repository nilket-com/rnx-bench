//! Bounded listening ZMTP 3.0 prototype for record 0048. Not a Jupyter kernel.
use hmac::{Hmac, KeyInit, Mac};
use serde_json::{Value, json};
use sha2::Sha256;
use std::{
    collections::HashMap,
    sync::{
        Arc, Mutex,
        atomic::{AtomicU64, AtomicUsize, Ordering::SeqCst},
    },
    time::Duration,
};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::{OwnedSemaphorePermit, Semaphore, mpsc, watch},
    time::{Instant, timeout, timeout_at},
};
const M: usize = 1024 * 1024;
type Res<T> = Result<T, Box<dyn std::error::Error + Send + Sync>>;
fn err(s: &str) -> Box<dyn std::error::Error + Send + Sync> {
    s.into()
}
fn emit(v: Value) {
    use std::io::Write;
    let mut w = std::io::stdout().lock();
    writeln!(w, "{v}").unwrap();
    w.flush().unwrap();
}
#[derive(Default)]
struct Stats {
    last_failure: Mutex<String>,
    received: AtomicUsize,
    rejected: AtomicUsize,
    accepted: AtomicUsize,
    bad: AtomicUsize,
    sent: AtomicUsize,
    closed: AtomicUsize,
    generated_collisions: AtomicUsize,
}
struct Packet {
    wire: Arc<Vec<u8>>,
    _bytes: OwnedSemaphorePermit,
    _count: OwnedSemaphorePermit,
    _global: Option<OwnedSemaphorePermit>,
}
struct Peer {
    id: Vec<u8>,
    generation: u64,
    tx: mpsc::Sender<Packet>,
    stop: watch::Sender<bool>,
    bytes: Arc<Semaphore>,
    count: Arc<Semaphore>,
    subs: Mutex<HashMap<Vec<u8>, u16>>,
}
struct Endpoint {
    name: &'static str,
    kind: &'static str,
    peers: Mutex<HashMap<Vec<u8>, Arc<Peer>>>,
    slots: Arc<Semaphore>,
    incoming: Arc<Semaphore>,
}
struct State {
    trace: Mutex<Vec<Value>>,
    stats: Stats,
    next: AtomicU64,
    publication: Arc<Semaphore>,
    endpoints: Vec<Arc<Endpoint>>,
    key: Vec<u8>,
}
struct Message {
    parts: Vec<Vec<u8>>,
    _credits: Vec<OwnedSemaphorePermit>,
}
fn sig(key: &[u8], parts: &[Vec<u8>]) -> Vec<u8> {
    if key.is_empty() {
        return vec![];
    }
    let mut mac = Hmac::<Sha256>::new_from_slice(key).unwrap();
    for p in parts {
        mac.update(p);
    }
    hex::encode(mac.finalize().into_bytes()).into_bytes()
}
fn encode(parts: &[Vec<u8>]) -> Res<Arc<Vec<u8>>> {
    let size = parts
        .iter()
        .try_fold(0usize, |n, p| n.checked_add(p.len())?.checked_add(9))
        .ok_or("wire overflow")?;
    if size > 2 * M {
        return Err(err("outgoing wire cap"));
    }
    let mut b = Vec::with_capacity(size);
    for (i, p) in parts.iter().enumerate() {
        let more = if i + 1 < parts.len() { 1 } else { 0 };
        if p.len() < 256 {
            b.extend([more, p.len() as u8]);
        } else {
            b.push(more | 2);
            b.extend((p.len() as u64).to_be_bytes());
        }
        b.extend(p);
    }
    Ok(Arc::new(b))
}
// Parse the u64 before converting to usize or allocating. A fixed nine-byte header.
async fn header<R: tokio::io::AsyncRead + Unpin>(r: &mut R) -> Res<(u8, u64)> {
    let flag = r.read_u8().await?;
    if flag & 0xf8 != 0 || flag & 5 == 5 {
        return Err(err("invalid flags"));
    }
    let n = if flag & 2 != 0 {
        r.read_u64().await?
    } else {
        r.read_u8().await? as u64
    };
    Ok((flag, n))
}
async fn body<R: tokio::io::AsyncRead + Unpin>(r: &mut R, n: u64, cap: usize) -> Res<Vec<u8>> {
    if n > cap as u64 {
        return Err(err("declared length exceeds cap"));
    }
    let n = usize::try_from(n)?;
    let mut b = Vec::new();
    b.try_reserve_exact(n)?;
    b.resize(n, 0);
    r.read_exact(&mut b).await?;
    Ok(b)
}
async fn message<R: tokio::io::AsyncRead + Unpin>(r: &mut R, ep: &Endpoint) -> Res<Message> {
    // Idle connections have no assembly deadline. Start after the first header byte.
    let first = r.read_u8().await?;
    let end = Instant::now() + Duration::from_secs(5);
    timeout_at(end, async {
        let mut parts = Vec::with_capacity(32);
        let mut credits = Vec::with_capacity(32);
        let mut total = 0usize;
        let mut first = Some(first);
        loop {
            let (f, n) = if let Some(f) = first.take() {
                if f & 0xf8 != 0 || f & 5 == 5 {
                    return Err(err("invalid flags"));
                }
                let n = if f & 2 != 0 {
                    r.read_u64().await?
                } else {
                    r.read_u8().await? as u64
                };
                (f, n)
            } else {
                header(r).await?
            };
            if f & 4 != 0 {
                let command = body(r, n, 8192).await?;
                return Err(err(&format!(
                    "unsupported traffic command: {}",
                    hex::encode(&command[..command.len().min(128)])
                )));
            }
            if parts.len() == 32 || n > (M - total) as u64 {
                return Err(err("multipart cap"));
            }
            let len = usize::try_from(n)?;
            let credit = ep.incoming.clone().acquire_many_owned(len as u32).await?;
            let b = body(r, n, M - total).await?;
            if b.capacity() != len {
                return Err(err("unexpected allocation capacity"));
            }
            credits.push(credit);
            total += len;
            parts.push(b);
            if f & 1 == 0 {
                return Ok(Message {
                    parts,
                    _credits: credits,
                });
            }
        }
    })
    .await?
}
fn metadata(kind: &str) -> Vec<u8> {
    let mut b = b"\x05READY\x0bSocket-Type".to_vec();
    b.extend((kind.len() as u32).to_be_bytes());
    b.extend(kind.as_bytes());
    b
}
async fn handshake(s: &mut TcpStream, ep: &Endpoint, st: &State) -> Res<Option<Vec<u8>>> {
    timeout(Duration::from_secs(2),async{
 let mut greeting=[0u8;64];greeting[0]=255;greeting[9]=127;greeting[10]=3;greeting[12..16].copy_from_slice(b"NULL");s.write_all(&greeting).await?;
 s.read_exact(&mut greeting).await?;trace(st,json!({"endpoint":ep.name,"peer_greeting":hex::encode(greeting)}));
 if greeting[0]!=255||greeting[9]!=127||greeting[10]<3||greeting[12..32]!=*b"NULL\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"||greeting[32]!=0{return Err(err("greeting"));}
 let ready=metadata(ep.kind);trace(st,json!({"endpoint":ep.name,"server_version":[3,0],"server_ready":hex::encode(&ready)}));s.write_all(&[4,ready.len() as u8]).await?;s.write_all(&ready).await?;
 let (f,n)=header(s).await?;if f&4==0{return Err(err("READY command required"));}let ready=body(s,n,8192).await?;
 trace(st,json!({"endpoint":ep.name,"peer_ready_prefix":hex::encode(&ready[..ready.len().min(512)])}));
 if !ready.starts_with(b"\x05READY"){return Err(err("READY required"));}
 let mut props=HashMap::new();let mut p=6;
 while p<ready.len(){if props.len()==64{return Err(err("metadata count"));}let n=ready[p] as usize;p+=1;if n==0||p+n+4>ready.len(){return Err(err("metadata name"));}
  let name=ready[p..p+n].iter().map(u8::to_ascii_lowercase).collect::<Vec<_>>();
  if !name.iter().all(|c|c.is_ascii_alphanumeric()||b"-_.+".contains(c)){return Err(err("metadata name"));}p+=n;
  let len=u32::from_be_bytes(ready[p..p+4].try_into()?) as usize;p+=4;if len>ready.len()-p{return Err(err("metadata length"));}
  if props.insert(name,ready[p..p+len].to_vec()).is_some(){return Err(err("duplicate metadata"));}p+=len;
 }
 let want=match ep.kind{"PUB"=>b"SUB".as_slice(),"REP"=>b"REQ".as_slice(),_=>b"DEALER".as_slice()};
 if props.get(b"socket-type".as_slice()).map(Vec::as_slice)!=Some(want){return Err(err("socket pairing"));}
 let id=props.remove(b"identity".as_slice());if id.as_ref().is_some_and(|id|id.len()>255){return Err(err("identity length"));}Ok(id.filter(|i|!i.is_empty()))
 }).await?
}
fn enqueue(peer: &Peer, wire: Arc<Vec<u8>>, global: Option<OwnedSemaphorePermit>) -> Res<()> {
    if *peer.stop.borrow() {
        return Err(err("closed generation"));
    }
    let bytes = peer
        .bytes
        .clone()
        .try_acquire_many_owned(wire.capacity() as u32)?;
    let count = peer.count.clone().try_acquire_owned()?;
    peer.tx
        .try_send(Packet {
            wire,
            _bytes: bytes,
            _count: count,
            _global: global,
        })
        .map_err(|_| err("reply admission"))?;
    Ok(())
}
fn publish(st: &State, parts: &[Vec<u8>]) -> Res<()> {
    let wire = encode(parts)?;
    let ep = &st.endpoints[4];
    let peers = ep.peers.lock().unwrap();
    let mut reserved = vec![];
    for peer in peers.values() {
        if *peer.stop.borrow() {
            continue;
        }
        if !peer
            .subs
            .lock()
            .unwrap()
            .keys()
            .any(|p| parts[0].starts_with(p))
        {
            continue;
        }
        let bytes = peer
            .bytes
            .clone()
            .try_acquire_many_owned(wire.capacity() as u32);
        let count = peer.count.clone().try_acquire_owned();
        if let (Ok(bytes), Ok(count)) = (bytes, count) {
            reserved.push((peer, bytes, count));
        } else {
            peer.stop.send_replace(true);
        }
    }
    // Reserve the whole fanout before any publication enters a writer queue.
    let mut globals = vec![];
    for _ in &reserved {
        globals.push(
            st.publication
                .clone()
                .try_acquire_many_owned(wire.capacity() as u32)?,
        );
    }
    for ((peer, bytes, count), global) in reserved.into_iter().zip(globals) {
        let _ = peer.tx.try_send(Packet {
            wire: wire.clone(),
            _bytes: bytes,
            _count: count,
            _global: Some(global),
        });
    }
    st.stats.sent.fetch_add(1, SeqCst);
    Ok(())
}
fn subscription(peer: &Peer, m: &Message) -> Res<()> {
    if m.parts.len() != 1 || m.parts[0].is_empty() || m.parts[0].len() > 257 {
        return Err(err("subscription"));
    }
    let command = m.parts[0][0];
    let key = &m.parts[0][1..];
    let mut subs = peer.subs.lock().unwrap();
    match command {
        1 => {
            if !subs.contains_key(key) && subs.len() == 128 {
                return Err(err("subscription count"));
            }
            let v = subs.entry(key.to_vec()).or_insert(0);
            *v = v.checked_add(1).ok_or("subscription overflow")?;
        }
        0 => {
            if let Some(n) = subs.get_mut(key) {
                *n -= 1;
                if *n == 0 {
                    subs.remove(key);
                }
            }
        }
        _ => return Err(err("subscription prefix")),
    };
    Ok(())
}
async fn application(st: &State, peer: &Peer, m: &Message, jobs: &mpsc::Sender<usize>) -> Res<()> {
    let parts = &m.parts;
    let Some(d) = parts.iter().position(|p| p == b"<IDS|MSG>") else {
        return Err(err("delimiter"));
    };
    if parts.len() != d + 6 {
        return Err(err("envelope"));
    }
    let frames = &parts[d + 2..];
    let valid = if st.key.is_empty() {
        parts[d + 1].is_empty()
    } else {
        let mut mac = Hmac::<Sha256>::new_from_slice(&st.key).unwrap();
        for p in frames {
            mac.update(p);
        }
        hex::decode(&parts[d + 1])
            .ok()
            .is_some_and(|s| mac.verify_slice(&s).is_ok())
    };
    if !valid {
        st.stats.bad.fetch_add(1, SeqCst);
        return Ok(());
    }
    let v: Vec<Value> = frames
        .iter()
        .map(|f| serde_json::from_slice(f))
        .collect::<Result<_, _>>()?;
    if v.iter().any(|v| !v.is_object()) {
        return Err(err("dictionary"));
    }
    st.stats.accepted.fetch_add(1, SeqCst);
    if let Some(n) = v[3]["publish"].as_u64() {
        jobs.try_send(n.min(20000) as usize)?;
    }
    let reply = vec![
        serde_json::to_vec(
            &json!({"msg_id":uuid::Uuid::new_v4().to_string(),"session":"zmtp-probe","username":"probe","date":"2026-09-15T00:00:00Z","msg_type":"probe_reply","version":"5.4"}),
        )?,
        frames[0].clone(),
        b"{}".to_vec(),
        serde_json::to_vec(&json!({"status":"ok","echo":v[3]}))?,
    ];
    let mut out = parts[..=d].to_vec();
    out.push(sig(&st.key, &reply));
    out.extend(reply);
    enqueue(peer, encode(&out)?, None)
}
async fn connection(
    mut s: TcpStream,
    ep: Arc<Endpoint>,
    st: Arc<State>,
    jobs: mpsc::Sender<usize>,
    _slot: OwnedSemaphorePermit,
    mut shutdown: watch::Receiver<bool>,
) -> Res<()> {
    if *shutdown.borrow() {
        return Ok(());
    }
    s.set_nodelay(true)?;
    let id = tokio::select! {r=handshake(&mut s,&ep,&st)=>r?,_=shutdown.changed()=>return Ok(())};
    if *shutdown.borrow() {
        return Ok(());
    }
    let (tx, mut rx) = mpsc::channel(64);
    let (stop, mut stopped) = watch::channel(false);
    let peer = {
        let mut peers = ep.peers.lock().unwrap();
        let mut generation = st
            .next
            .fetch_update(SeqCst, SeqCst, |v| v.checked_add(1))
            .map_err(|_| err("generation exhausted"))?;
        let id = if let Some(id) = id {
            if peers.contains_key(&id) {
                return Err(err("live duplicate identity"));
            }
            id
        } else {
            loop {
                let mut id = vec![0];
                id.extend(generation.to_be_bytes());
                if !peers.contains_key(&id) {
                    break id;
                }
                st.stats.generated_collisions.fetch_add(1, SeqCst);
                generation = st
                    .next
                    .fetch_update(SeqCst, SeqCst, |v| v.checked_add(1))
                    .map_err(|_| err("generation exhausted"))?;
            }
        };
        let peer = Arc::new(Peer {
            id: id.clone(),
            generation,
            tx,
            stop,
            bytes: Arc::new(Semaphore::new(if ep.kind == "PUB" { 2 * M } else { M })),
            count: Arc::new(Semaphore::new(if ep.kind == "PUB" { 64 } else { 32 })),
            subs: Mutex::new(HashMap::new()),
        });
        peers.insert(id, peer.clone());
        peer
    };
    let (mut read, mut write) = s.into_split();
    let read_loop = async {
        loop {
            let m = message(&mut read, &ep).await?;
            st.stats.received.fetch_add(1, SeqCst);
            match ep.kind {
                "PUB" => {
                    trace(
                        &st,
                        json!({"subscription_parts":m.parts.len(),"first_part_prefix":hex::encode(&m.parts[0][..m.parts[0].len().min(257)])}),
                    );
                    subscription(&peer, &m)?
                }
                "REP" => {
                    if m.parts.first().is_none_or(|p| !p.is_empty()) {
                        return Err(err("REQ envelope"));
                    }
                    enqueue(&peer, encode(&m.parts)?, None)?;
                }
                _ => application(&st, &peer, &m, &jobs).await?,
            };
            tokio::task::yield_now().await;
        }
        #[allow(unreachable_code)]
        Ok::<(), Box<dyn std::error::Error + Send + Sync>>(())
    };
    let write_loop = async {
        while let Some(p) = rx.recv().await {
            timeout(Duration::from_secs(5), write.write_all(&p.wire)).await??;
        }
        Ok::<(), Box<dyn std::error::Error + Send + Sync>>(())
    };
    let result = tokio::select! {r=read_loop=>r,r=write_loop=>r,_=stopped.changed()=>Ok(()),_=shutdown.changed()=>Ok(())};
    peer.stop.send_replace(true);
    {
        let mut peers = ep.peers.lock().unwrap();
        if peers
            .get(&peer.id)
            .is_some_and(|p| p.generation == peer.generation)
        {
            peers.remove(&peer.id);
        }
    }
    drop(rx);
    st.stats.closed.fetch_add(1, SeqCst);
    result
}
fn trace(st: &State, v: Value) {
    let mut t = st.trace.lock().unwrap();
    if t.len() < 64 {
        t.push(v);
    }
}
fn snapshot(st: &State) -> Value {
    json!({"last_failure":st.stats.last_failure.lock().unwrap().clone(),"wire_trace":st.trace.lock().unwrap().clone(),"next_generation":st.next.load(SeqCst),"accepted":st.stats.accepted.load(SeqCst),"bad_signature":st.stats.bad.load(SeqCst),"rejected":st.stats.rejected.load(SeqCst),"messages_received":st.stats.received.load(SeqCst),"pub_send_ok":st.stats.sent.load(SeqCst),"generated_collisions":st.stats.generated_collisions.load(SeqCst),"publication_reserved":16*M-st.publication.available_permits(),"endpoints":st.endpoints.iter().map(|e|{let peers=e.peers.lock().unwrap();json!({"name":e.name,"connections":8-e.slots.available_permits(),"incoming_reserved":8*M-e.incoming.available_permits(),"routes":peers.len(),"identities":peers.values().map(|p|json!({"id":hex::encode(&p.id),"generation":p.generation})).collect::<Vec<_>>(),"outgoing_reserved":peers.values().map(|p|(if e.kind=="PUB"{2*M}else{M})-p.bytes.available_permits()).sum::<usize>(),"subscriptions":peers.values().map(|p|p.subs.lock().unwrap().len()).sum::<usize>()})}).collect::<Vec<_>>()})
}
#[tokio::main(flavor = "multi_thread", worker_threads = 2)]
async fn main() -> Res<()> {
    let eps = [
        ("shell", "ROUTER"),
        ("control", "ROUTER"),
        ("stdin", "ROUTER"),
        ("hb", "REP"),
        ("iopub", "PUB"),
    ]
    .into_iter()
    .map(|(name, kind)| {
        Arc::new(Endpoint {
            name,
            kind,
            peers: Mutex::new(HashMap::new()),
            slots: Arc::new(Semaphore::new(8)),
            incoming: Arc::new(Semaphore::new(8 * M)),
        })
    })
    .collect();
    let st = Arc::new(State {
        trace: Mutex::new(vec![]),
        stats: Stats::default(),
        next: AtomicU64::new(1),
        publication: Arc::new(Semaphore::new(16 * M)),
        endpoints: eps,
        key: if std::env::args().nth(1).as_deref() == Some("empty") {
            vec![]
        } else {
            b"local-probe-key".to_vec()
        },
    });
    let (stop, shutdown) = watch::channel(false);
    let (jobs, mut pending) = mpsc::channel(8);
    let mut tasks = tokio::task::JoinSet::new();
    let mut addresses = serde_json::Map::new();
    for ep in &st.endpoints {
        let listener = TcpListener::bind("127.0.0.1:0").await?;
        addresses.insert(
            ep.name.into(),
            json!(format!("tcp://{}", listener.local_addr()?)),
        );
        let ep = ep.clone();
        let st = st.clone();
        let jobs = jobs.clone();
        let mut shutdown = shutdown.clone();
        tasks.spawn(async move{let mut children=tokio::task::JoinSet::new();loop{tokio::select!{_=shutdown.changed()=>break,Some(_)=children.join_next()=>{},accepted=listener.accept()=>{let Ok((s,_))=accepted else{break;};if let Ok(slot)=ep.slots.clone().try_acquire_owned(){let ep=ep.clone();let st=st.clone();let jobs=jobs.clone();let shutdown=shutdown.clone();children.spawn(async move{if let Err(e)=connection(s,ep,st.clone(),jobs,slot,shutdown).await{*st.stats.last_failure.lock().unwrap()=e.to_string().chars().take(512).collect();st.stats.rejected.fetch_add(1,SeqCst);}});}else{drop(s);st.stats.rejected.fetch_add(1,SeqCst);}}}}
   while children.join_next().await.is_some(){};
  });
    }
    let state = st.clone();
    let mut done = shutdown.clone();
    tasks.spawn(async move{loop{tokio::select!{_=done.changed()=>break,job=pending.recv()=>{let Some(n)=job else{break;};for _ in 0..n{if *done.borrow(){break;}let _=publish(&state,&[b"probe".to_vec(),vec![b'x';16384]]);tokio::task::yield_now().await;}}}}});
    emit(Value::Object(addresses));
    let mut lines = tokio::io::BufReader::new(tokio::io::stdin()).lines();
    while let Some(line) = lines.next_line().await? {
        if line == "stop" {
            break;
        }
        emit(snapshot(&st));
    }
    stop.send_replace(true);
    timeout(Duration::from_secs(5), async {
        while let Some(r) = tasks.join_next().await {
            r.unwrap();
        }
    })
    .await?;
    emit(json!({"shutdown":snapshot(&st)}));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn ep() -> Endpoint {
        Endpoint {
            name: "test",
            kind: "ROUTER",
            peers: Mutex::new(HashMap::new()),
            slots: Arc::new(Semaphore::new(8)),
            incoming: Arc::new(Semaphore::new(8 * M)),
        }
    }
    #[tokio::test]
    async fn split_headers_and_coalesced_frames() {
        for n in [0, 1, 255, 256, 4096] {
            let parts = vec![vec![42; n], vec![], b"tail".to_vec()];
            let wire = encode(&parts).unwrap();
            for split in 0..=9.min(wire.len()) {
                let (mut tx, mut rx) = tokio::io::duplex(16384);
                let w = wire.clone();
                tokio::spawn(async move {
                    tx.write_all(&w[..split]).await.unwrap();
                    tokio::task::yield_now().await;
                    tx.write_all(&w[split..]).await.unwrap();
                });
                let e = ep();
                let m = message(&mut rx, &e).await.unwrap();
                assert_eq!(m.parts, parts);
                drop(m);
                assert_eq!(e.incoming.available_permits(), 8 * M);
            }
        }
    }
    #[tokio::test]
    async fn caps_are_checked_before_body_or_narrowing() {
        for n in [M as u64 + 1, u32::MAX as u64, u64::MAX - 1, u64::MAX] {
            let mut wire = vec![2];
            wire.extend(n.to_be_bytes());
            let e = ep();
            assert!(message(&mut wire.as_slice(), &e).await.is_err());
            assert_eq!(e.incoming.available_permits(), 8 * M);
        }
        let e = ep();
        let mut wire = vec![0, 0];
        for _ in 0..32 {
            wire.splice(0..0, [1, 0]);
        }
        assert!(message(&mut wire.as_slice(), &e).await.is_err());
        let parts = vec![vec![]; 32];
        let encoded = encode(&parts).unwrap();
        assert_eq!(
            message(&mut encoded.as_slice(), &e)
                .await
                .unwrap()
                .parts
                .len(),
            32
        );
        let encoded = encode(&[vec![7; M]]).unwrap();
        let m = message(&mut encoded.as_slice(), &e).await.unwrap();
        assert_eq!(e.incoming.available_permits(), 7 * M);
        drop(m);
        assert_eq!(e.incoming.available_permits(), 8 * M);
    }
    #[tokio::test]
    async fn malformed_and_truncated_states_release_credits() {
        for f in [5, 7, 8, 128, 255] {
            let e = ep();
            assert!(message(&mut [f, 0].as_slice(), &e).await.is_err());
            assert_eq!(e.incoming.available_permits(), 8 * M);
        }
        let wire = encode(&[b"first".to_vec(), vec![3; 256]]).unwrap();
        for n in 0..wire.len() {
            let e = ep();
            assert!(message(&mut wire[..n].as_ref(), &e).await.is_err());
            assert_eq!(e.incoming.available_permits(), 8 * M);
        }
    }
    fn peer(limit: usize) -> (Arc<Peer>, mpsc::Receiver<Packet>) {
        let (tx, rx) = mpsc::channel(64);
        let (stop, _) = watch::channel(false);
        (
            Arc::new(Peer {
                id: vec![0],
                generation: 1,
                tx,
                stop,
                bytes: Arc::new(Semaphore::new(limit)),
                count: Arc::new(Semaphore::new(64)),
                subs: Mutex::new(HashMap::new()),
            }),
            rx,
        )
    }
    #[test]
    fn subscription_and_reply_credit_boundaries() {
        let (p, mut rx) = peer(2 * M);
        for n in 0..128 {
            let key = vec![1, n];
            subscription(
                &p,
                &Message {
                    parts: vec![key],
                    _credits: vec![],
                },
            )
            .unwrap();
        }
        assert!(
            subscription(
                &p,
                &Message {
                    parts: vec![vec![1, 128]],
                    _credits: vec![]
                }
            )
            .is_err()
        );
        for _ in 1..65535 {
            subscription(
                &p,
                &Message {
                    parts: vec![vec![1, 0]],
                    _credits: vec![],
                },
            )
            .unwrap();
        }
        assert!(
            subscription(
                &p,
                &Message {
                    parts: vec![vec![1, 0]],
                    _credits: vec![]
                }
            )
            .is_err()
        );
        let (p2, _rx2) = peer(M);
        subscription(
            &p2,
            &Message {
                parts: vec![vec![1; 257]],
                _credits: vec![],
            },
        )
        .unwrap();
        assert!(
            subscription(
                &p2,
                &Message {
                    parts: vec![vec![1; 258]],
                    _credits: vec![]
                }
            )
            .is_err()
        );
        let wire = Arc::new(vec![0; 2 * M]);
        enqueue(&p, wire.clone(), None).unwrap();
        assert!(enqueue(&p, Arc::new(vec![1]), None).is_err());
        assert_eq!(p.bytes.available_permits(), 0);
        drop(rx.try_recv().unwrap());
        assert_eq!(p.bytes.available_permits(), 2 * M);
        p.stop.send_replace(true);
        assert!(enqueue(&p, wire, None).is_err());
    }
    #[test]
    fn publication_preflight_and_closing_stale_generation() {
        let e = Arc::new(ep());
        let mut endpoints = vec![e.clone(); 5];
        endpoints[4] = e.clone();
        let st = State {
            trace: Mutex::new(vec![]),
            stats: Stats::default(),
            next: AtomicU64::new(1),
            publication: Arc::new(Semaphore::new(16 * M)),
            endpoints,
            key: vec![],
        };
        let (p, mut rx) = peer(2 * M);
        p.subs.lock().unwrap().insert(vec![], 1);
        e.peers.lock().unwrap().insert(vec![0], p.clone());
        let all = st
            .publication
            .clone()
            .try_acquire_many_owned((16 * M) as u32)
            .unwrap();
        assert!(publish(&st, &[b"abc".to_vec()]).is_err());
        assert!(rx.try_recv().is_err());
        assert_eq!(p.bytes.available_permits(), 2 * M);
        drop(all);
        publish(&st, &[b"abc".to_vec()]).unwrap();
        let packet = rx.try_recv().unwrap();
        assert!(st.publication.available_permits() < 16 * M);
        drop(packet);
        assert_eq!(st.publication.available_permits(), 16 * M);
        p.stop.send_replace(true);
        let (new, _) = peer(2 * M);
        e.peers.lock().unwrap().insert(vec![0], new.clone());
        assert!(enqueue(&p, encode(&[b"stale".to_vec()]).unwrap(), None).is_err());
        assert_eq!(new.bytes.available_permits(), 2 * M);
    }
}
