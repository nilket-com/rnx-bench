//! Injected only into an isolated rnx checkout as a private unit-test module.
use crate::{Context, Extensions, Scope, Vm, execute::Runtime, http, lifecycle::Lifecycle};
use serde_json::json;
use std::{
    cell::RefCell,
    collections::BTreeMap,
    future::{Future, poll_fn},
    io::{Read, Write},
    net::TcpListener,
    pin::Pin,
    rc::Rc,
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
        mpsc,
    },
    task::{Context as TaskContext, Poll},
    thread,
    time::{Duration, Instant},
};
type Held = Pin<Box<dyn Future<Output = Result<i64, String>>>>;
thread_local! { static HELD: RefCell<BTreeMap<i64,Held>> = RefCell::new(BTreeMap::new()); }
const SOURCE: &str = r#"
pub async fn main(id, mode, url) {
    probe::entered(id);
    // These are the real batteries, installed in every measured context.
    let n = json::parse("42")?;
    let p = path::join("a", "b");
    let args = env::args();
    if n != 42 || args.len() != 1 { panic("battery binding failed"); }
    if mode == 1 { time::sleep(40).await?; }
    if mode == 2 { loop {} }
    if mode == 3 {
        probe::retain(id, 10000);
        select { _ = probe::wait(id) => (), _ = time::sleep(5) => () }
        panic("handler failed");
    }
    if mode == 4 { probe::retain(id, 120); return probe::wait(id).await?; }
    if mode == 5 { return http::get(url).await?.body; }
    if mode == 6 {
        let f = http::get(url);
        select { _ = f => (), _ = time::sleep(30) => () }
        panic("handler failed");
    }
    n
}
"#;
#[derive(Default)]
struct Stats {
    builds: AtomicUsize,
    builders: AtomicUsize,
    retired: AtomicUsize,
    live: AtomicUsize,
    polls: AtomicUsize,
    build_us: AtomicUsize,
}
struct Delay {
    sleep: Pin<Box<tokio::time::Sleep>>,
    id: i64,
    stats: Arc<Stats>,
    started: bool,
}
impl Future for Delay {
    type Output = Result<i64, String>;
    fn poll(mut self: Pin<&mut Self>, cx: &mut TaskContext<'_>) -> Poll<Self::Output> {
        if !self.started {
            self.started = true;
            self.stats.live.fetch_add(1, Ordering::SeqCst);
        }
        self.stats.polls.fetch_add(1, Ordering::SeqCst);
        self.sleep.as_mut().poll(cx).map(|_| Ok(self.id))
    }
}
impl Drop for Delay {
    fn drop(&mut self) {
        if self.started {
            self.stats.live.fetch_sub(1, Ordering::SeqCst);
        }
    }
}
struct Bundle {
    runtime: Arc<rune::runtime::RuntimeContext>,
    life: Lifecycle,
    scope: Scope,
    http: http::State,
    stats: Arc<Stats>,
}
impl Bundle {
    fn new(stats: Arc<Stats>, started: mpsc::Sender<i64>) -> (Self, Context) {
        let begin = Instant::now();
        let extensions = Extensions::none().with_lifecycle("probe", {
            let stats = stats.clone();
            move |module, scope| {
                stats.builders.fetch_add(1, Ordering::SeqCst);
                module
                    .function("entered", move |id: i64| {
                        started.send(id).unwrap();
                    })
                    .build()
                    .unwrap();
                module
                    .function("retain", move |id: i64, ms: u64| {
                        let inner = Delay {
                            sleep: Box::pin(tokio::time::sleep(Duration::from_millis(ms))),
                            id,
                            stats: stats.clone(),
                            started: false,
                        };
                        HELD.with(|held| {
                            assert!(
                                held.borrow_mut()
                                    .insert(id, Box::pin(scope.track(inner)))
                                    .is_none()
                            );
                        });
                    })
                    .build()
                    .unwrap();
                module
                    .function("wait", |id: i64| async move {
                        poll_fn(|cx| {
                            HELD.with(|held| {
                                held.borrow_mut().get_mut(&id).unwrap().as_mut().poll(cx)
                            })
                        })
                        .await
                    })
                    .build()
                    .unwrap();
                Ok(vec![("probe::wait".into(), "assembly fixture")])
            }
        });
        let life = extensions.lifecycle().unwrap();
        let scope = life.scope("probe");
        let mut context = Context::with_default_modules().unwrap();
        crate::install_core(&mut context).unwrap();
        crate::fs::install(&mut context).unwrap();
        crate::path::install(&mut context).unwrap();
        crate::time::install(&mut context).unwrap();
        crate::text::install(&mut context).unwrap();
        crate::env::install(&mut context, Arc::from(["fixture".to_owned()])).unwrap();
        let http = http::State::default();
        crate::http::install(&mut context, &http, life.scope("http")).unwrap();
        extensions.install_with(&mut context, &life).unwrap();
        let runtime = Arc::new(context.runtime().unwrap());
        stats.builds.fetch_add(1, Ordering::SeqCst);
        stats
            .build_us
            .fetch_add(begin.elapsed().as_micros() as usize, Ordering::SeqCst);
        (
            Self {
                runtime,
                life,
                scope,
                http,
                stats,
            },
            context,
        )
    }
    async fn run(
        &self,
        unit: Arc<rune::Unit>,
        id: i64,
        mode: i64,
        url: String,
    ) -> Result<String, String> {
        self.life.begin().unwrap();
        let result = {
            let mut vm = Vm::new(self.runtime.clone(), unit);
            let mut execution = vm.execute(["main"], (id, mode, url)).unwrap();
            match rune::runtime::budget::with(10_000_000, execution.async_resume())
                .await
                .into_result()
            {
                Ok(rune::runtime::GeneratorState::Complete(v)) => crate::json::stringify(&v),
                Ok(_) => Err("yield".into()),
                Err(e) => Err(e.to_string()),
            }
        };
        self.life.finish(result.is_err()).unwrap();
        result
    }
    async fn retire(&self) {
        self.life.close().unwrap();
        assert_eq!(
            self.scope
                .track(async { Ok::<_, String>(1) })
                .await
                .unwrap_err(),
            "operation scope belongs to a retired context"
        );
        self.stats.retired.fetch_add(1, Ordering::SeqCst);
    }
}
fn emit(value: serde_json::Value) {
    let path = std::env::var("RNX_ASSEMBLY_RESULTS").unwrap();
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .unwrap();
    writeln!(file, "{value}").unwrap();
}
fn new_runtime() -> tokio::runtime::Runtime {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
}
fn count(stats: &Stats, expected: usize) {
    assert_eq!(stats.builds.load(Ordering::SeqCst), expected);
    assert_eq!(stats.builders.load(Ordering::SeqCst), expected);
    assert_eq!(stats.retired.load(Ordering::SeqCst), expected);
    assert_eq!(stats.live.load(Ordering::SeqCst), 0);
}
fn compiled() -> Arc<rune::Unit> {
    let stats = Arc::new(Stats::default());
    let (tx, _) = mpsc::channel();
    let (bundle, context) = Bundle::new(stats.clone(), tx);
    let begin = Instant::now();
    let unit = crate::compile(&context, SOURCE).unwrap();
    let compile_ms = begin.elapsed().as_secs_f64() * 1000.;
    new_runtime().block_on(bundle.retire());
    count(&stats, 1);
    emit(
        json!({"event":"schema","contexts":1,"builders":1,"units":1,"retired":1,"compile_ms":compile_ms}),
    );
    Arc::new(unit)
}
#[derive(Clone)]
struct Job {
    id: i64,
    mode: i64,
    at: Instant,
}
fn scheduling(unit: Arc<rune::Unit>) {
    for slots in [1, 4] {
        for workload in ["await", "cpu", "saturated"] {
            for sample in 0..3 {
                let stats = Arc::new(Stats::default());
                let (start_tx, start_rx) = mpsc::channel();
                let (done_tx, done_rx) = mpsc::channel();
                let (ready_tx, ready_rx) = mpsc::channel();
                let mut senders = Vec::new();
                let mut threads = Vec::new();
                let before = crate::memory::live().unwrap();
                crate::memory::reset_peak();
                for _ in 0..2 {
                    let (tx, mut rx) = tokio::sync::mpsc::channel::<Job>(16);
                    senders.push(tx);
                    let (stats, unit, started, done, ready) = (
                        stats.clone(),
                        unit.clone(),
                        start_tx.clone(),
                        done_tx.clone(),
                        ready_tx.clone(),
                    );
                    threads.push(thread::spawn(move || {
                        let rt = new_runtime();
                        let local = tokio::task::LocalSet::new();
                        local.block_on(&rt, async {
                            let serial = if slots == 1 {
                                Some(Rc::new(Bundle::new(stats.clone(), started.clone()).0))
                            } else {
                                None
                            };
                            ready.send(()).unwrap();
                            let sem = Arc::new(tokio::sync::Semaphore::new(slots));
                            let mut handles = Vec::new();
                            while let Some(job) = rx.recv().await {
                                let permit = sem.clone().acquire_owned().await.unwrap();
                                let bundle = serial.clone().unwrap_or_else(|| {
                                    Rc::new(Bundle::new(stats.clone(), started.clone()).0)
                                });
                                let (unit, done) = (unit.clone(), done.clone());
                                handles.push(tokio::task::spawn_local(async move {
                                    let outcome =
                                        bundle.run(unit, job.id, job.mode, String::new()).await;
                                    if job.mode == 2 {
                                        assert!(outcome.as_ref().unwrap_err().contains("limited"));
                                    } else {
                                        assert_eq!(outcome.as_ref().unwrap(), "42");
                                    }
                                    if slots != 1 {
                                        bundle.retire().await;
                                    }
                                    done.send((
                                        job.id,
                                        job.at.elapsed().as_secs_f64() * 1000.,
                                        outcome,
                                    ))
                                    .unwrap();
                                    drop(permit);
                                }));
                            }
                            for h in handles {
                                h.await.unwrap();
                            }
                            if let Some(b) = serial {
                                b.retire().await;
                            }
                        });
                        assert_eq!(rt.metrics().num_alive_tasks(), 0);
                    }));
                }
                for _ in 0..2 {
                    ready_rx.recv_timeout(Duration::from_secs(10)).unwrap();
                }
                let begin = Instant::now();
                let n = if workload == "await" {
                    17
                } else {
                    if workload == "cpu" { 2 } else { 3 }
                };
                if workload == "await" {
                    for id in 0..16 {
                        senders[id as usize % 2]
                            .blocking_send(Job {
                                id,
                                mode: 1,
                                at: Instant::now(),
                            })
                            .unwrap();
                    }
                    for _ in 0..2 {
                        start_rx.recv_timeout(Duration::from_secs(10)).unwrap();
                    }
                    senders[0]
                        .blocking_send(Job {
                            id: 99,
                            mode: 0,
                            at: Instant::now(),
                        })
                        .unwrap();
                } else {
                    senders[0]
                        .blocking_send(Job {
                            id: 0,
                            mode: 2,
                            at: Instant::now(),
                        })
                        .unwrap();
                    assert_eq!(start_rx.recv_timeout(Duration::from_secs(10)).unwrap(), 0);
                    if workload == "saturated" {
                        senders[1]
                            .blocking_send(Job {
                                id: 1,
                                mode: 2,
                                at: Instant::now(),
                            })
                            .unwrap();
                        assert_eq!(start_rx.recv_timeout(Duration::from_secs(10)).unwrap(), 1);
                    }
                    let target = if workload == "cpu" { 1 } else { 0 };
                    senders[target]
                        .blocking_send(Job {
                            id: 99,
                            mode: 0,
                            at: Instant::now(),
                        })
                        .unwrap();
                }
                let mut rows = Vec::new();
                for _ in 0..n {
                    let (id, ms, outcome) = done_rx.recv_timeout(Duration::from_secs(10)).unwrap();
                    rows.push(json!({"id":id,"latency_ms":ms,"outcome":outcome}));
                }
                let complete_ms = begin.elapsed().as_secs_f64() * 1000.;
                drop(senders);
                for t in threads {
                    t.join().unwrap();
                }
                let expected = if slots == 1 { 2 } else { n };
                count(&stats, expected);
                emit(
                    json!({"event":"scheduling","slots":slots,"workload":workload,"sample":sample,
            "requests":n,"contexts":expected,"builders":expected,"retired":expected,"units":0,
            "build_total_ms":stats.build_us.load(Ordering::SeqCst) as f64/1000.,"complete_ms":complete_ms,
            "requests_per_second":n as f64*1000./complete_ms,"rows":rows,
            "peak_increase_bytes":crate::memory::peak().saturating_sub(before),
            "retained_delta_bytes":crate::memory::live().unwrap() as i64-before as i64}),
                );
            }
        }
    }
}
fn lifecycle_isolation(unit: Arc<rune::Unit>) {
    // Same-thread multiplexing: failed B revokes its strongly retained inner;
    // started A remains pending in another lifecycle context and later completes.
    let stats = Arc::new(Stats::default());
    // Keep a receiver alive: the entered callback is an asserted event sink.
    let (tx, rx) = mpsc::channel();
    let _keep = rx;
    let (a, _) = Bundle::new(stats.clone(), tx.clone());
    let (b, _) = Bundle::new(stats.clone(), tx);
    let rt = new_runtime();
    rt.block_on(async {
        let mut good = Box::pin(a.run(unit.clone(), 10, 4, String::new()));
        poll_fn(|cx| {
            assert!(good.as_mut().poll(cx).is_pending());
            Poll::Ready(())
        })
        .await;
        let bad = b.run(unit.clone(), 20, 3, String::new()).await.unwrap_err();
        assert!(bad.contains("handler failed"));
        assert_eq!(stats.live.load(Ordering::SeqCst), 1);
        let cancelled =
            poll_fn(|cx| HELD.with(|h| h.borrow_mut().get_mut(&20).unwrap().as_mut().poll(cx)))
                .await;
        assert_eq!(cancelled.unwrap_err(), "operation cancelled");
        assert_eq!(good.await.unwrap(), "10");
        HELD.with(|h| h.borrow_mut().clear());
        a.retire().await;
        b.retire().await;
    });
    count(&stats, 2);
    emit(
        json!({"event":"same_worker_lifecycle","survivor":10,"failed_operation":"operation cancelled","contexts":2,"retired":2}),
    );
    let stats = Arc::new(Stats::default());
    let (started, rx) = mpsc::channel();
    let (go_tx, go_rx) = mpsc::channel();
    let st = stats.clone();
    let u = unit.clone();
    let started_a = started.clone();
    let a = thread::spawn(move || {
        let (a, _) = Bundle::new(st, started_a);
        let rt = new_runtime();
        rt.block_on(async {
            let mut work = Box::pin(a.run(u, 30, 4, String::new()));
            poll_fn(|cx| {
                assert!(work.as_mut().poll(cx).is_pending());
                Poll::Ready(())
            })
            .await;
            go_rx.recv_timeout(Duration::from_secs(10)).unwrap();
            assert_eq!(work.await.unwrap(), "30");
            HELD.with(|h| h.borrow_mut().clear());
            a.retire().await;
        });
    });
    assert_eq!(rx.recv_timeout(Duration::from_secs(10)).unwrap(), 30);
    let st = stats.clone();
    let b = thread::spawn(move || {
        let (b, _) = Bundle::new(st, started);
        new_runtime().block_on(async {
            assert!(
                b.run(unit, 40, 3, String::new())
                    .await
                    .unwrap_err()
                    .contains("handler failed")
            );
            assert_eq!(
                poll_fn(|cx| HELD.with(|h| h.borrow_mut().get_mut(&40).unwrap().as_mut().poll(cx)))
                    .await
                    .unwrap_err(),
                "operation cancelled"
            );
            HELD.with(|h| h.borrow_mut().clear());
            b.retire().await;
        });
        go_tx.send(()).unwrap();
    });
    b.join().unwrap();
    a.join().unwrap();
    count(&stats, 2);
    emit(
        json!({"event":"cross_worker_lifecycle","survivor":30,"failed_operation":"operation cancelled","contexts":2,"retired":2}),
    );
}
struct Fixture {
    url: String,
    events: mpsc::Receiver<&'static str>,
    reply: mpsc::Sender<()>,
    thread: thread::JoinHandle<()>,
}
impl Fixture {
    fn new() -> Self {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}/", listener.local_addr().unwrap());
        let (events_tx, events) = mpsc::channel();
        let (reply, release) = mpsc::channel();
        let thread = thread::spawn(move || {
            listener.set_nonblocking(true).unwrap();
            let end = Instant::now() + Duration::from_secs(10);
            let mut stream = loop {
                match listener.accept() {
                    Ok((s, _)) => break s,
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                        assert!(Instant::now() < end);
                        thread::sleep(Duration::from_millis(2));
                    }
                    Err(e) => panic!("{e}"),
                }
            };
            stream
                .set_read_timeout(Some(Duration::from_millis(10)))
                .unwrap();
            let mut bytes = Vec::new();
            let mut buf = [0; 4096];
            while !bytes.windows(4).any(|x| x == b"\r\n\r\n") {
                match stream.read(&mut buf) {
                    Ok(0) => panic!("early EOF"),
                    Ok(n) => bytes.extend_from_slice(&buf[..n]),
                    Err(e)
                        if matches!(
                            e.kind(),
                            std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
                        ) =>
                    {
                        assert!(Instant::now() < end)
                    }
                    Err(e) => panic!("{e}"),
                }
            }
            events_tx.send("request").unwrap();
            loop {
                assert!(Instant::now() < end);
                if release.try_recv().is_ok() {
                    stream
                        .write_all(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok",
                        )
                        .unwrap();
                    break;
                }
                match stream.read(&mut buf) {
                    Ok(0) => {
                        events_tx.send("clean EOF").unwrap();
                        break;
                    }
                    Ok(_) => panic!("unexpected body"),
                    Err(e)
                        if matches!(
                            e.kind(),
                            std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
                        ) => {}
                    Err(e) => panic!("read error, not EOF: {e}"),
                }
            }
        });
        Self {
            url,
            events,
            reply,
            thread,
        }
    }
}
async fn request_seen(f: &Fixture) {
    let end = Instant::now() + Duration::from_secs(5);
    loop {
        match f.events.try_recv() {
            Ok(e) => {
                assert_eq!(e, "request");
                return;
            }
            Err(mpsc::TryRecvError::Empty) => {
                assert!(Instant::now() < end);
                tokio::time::sleep(Duration::from_millis(2)).await;
            }
            Err(e) => panic!("{e}"),
        }
    }
}
fn http_same_worker(unit: Arc<rune::Unit>) {
    let stats = Arc::new(Stats::default());
    let (tx, _rx) = mpsc::channel();
    let (a, _) = Bundle::new(stats.clone(), tx.clone());
    let (b, _) = Bundle::new(stats.clone(), tx);
    let fa = Fixture::new();
    let fb = Fixture::new();
    let runtime = Runtime::new().unwrap();
    let mut good = Box::pin(a.run(unit.clone(), 50, 5, fa.url.clone()));
    let tasks_before = runtime.probe_inner().block_on(async {
        let mut seen = Box::pin(request_seen(&fa));
        poll_fn(|cx| {
            assert!(good.as_mut().poll(cx).is_pending());
            seen.as_mut().poll(cx)
        }).await;
        assert!(b.run(unit, 60, 6, fb.url.clone()).await.unwrap_err().contains("handler failed"));
        request_seen(&fb).await;
        // finish already revoked the failed execution. Owner retirement and
        // pool release are legal here, with a different owner's request live.
        b.retire().await;
        b.http.cancel();
        let deadline = Instant::now() + Duration::from_millis(500);
        loop {
            match fb.events.try_recv() {
                Ok(event) => { assert_eq!(event, "clean EOF"); break; }
                Err(mpsc::TryRecvError::Empty) => {
                    assert!(Instant::now() < deadline, "failed owner did not close");
                    tokio::time::sleep(Duration::from_millis(1)).await;
                }
                Err(e) => panic!("{e}"),
            }
        }
        assert!(matches!(fa.events.try_recv(), Err(mpsc::TryRecvError::Empty)));
        let tasks = runtime.probe_inner().metrics().num_alive_tasks();
        assert!(tasks > 0, "healthy owner must still have work");
        tasks
    });
    fa.reply.send(()).unwrap();
    let answer = runtime.probe_inner().block_on(good).unwrap();
    assert_eq!(answer, "\"ok\"");
    a.http.cancel();
    b.http.cancel();
    runtime.probe_inner().block_on(async {
        a.retire().await;
    });
    runtime.drain_shutdown().unwrap();
    let tasks_after = runtime.probe_inner().metrics().num_alive_tasks();
    assert_eq!(tasks_after, 0);
    fa.thread.join().unwrap();
    fb.thread.join().unwrap();
    count(&stats, 2);
    emit(
        json!({"event":"same_worker_http", "owner_cancel_inside_runtime":true,"failed_socket":"clean EOF","healthy_survived":answer,"tasks_before":tasks_before,"tasks_after":tasks_after}),
    );
}
fn http_cross_worker(unit: Arc<rune::Unit>) {
    let stats = Arc::new(Stats::default());
    let fa = Fixture::new();
    let fb = Fixture::new();
    let (ready_tx, ready_rx) = mpsc::channel();
    let (go_tx, go_rx) = mpsc::channel();
    let u = unit.clone();
    let st = stats.clone();
    let url = fa.url.clone();
    let a = thread::spawn(move || {
        let (tx, _rx) = mpsc::channel();
        let (a, _) = Bundle::new(st, tx);
        let runtime = Runtime::new().unwrap();
        let mut good = Box::pin(a.run(u, 70, 5, url));
        runtime.probe_inner().block_on(async {
            ready_tx.send(()).unwrap();
            loop {
                if go_rx.try_recv().is_ok() { break; }
                poll_fn(|cx| {
                    assert!(good.as_mut().poll(cx).is_pending());
                    Poll::Ready(())
                }).await;
                tokio::time::sleep(Duration::from_millis(1)).await;
            }
            assert_eq!(good.await.unwrap(), "\"ok\"");
        });
        a.http.cancel();
        runtime.probe_inner().block_on(a.retire());
        runtime.drain_shutdown().unwrap();
        assert_eq!(runtime.probe_inner().metrics().num_alive_tasks(), 0);
    });
    ready_rx.recv_timeout(Duration::from_secs(5)).unwrap();
    assert_eq!(
        fa.events.recv_timeout(Duration::from_secs(5)).unwrap(),
        "request"
    );
    let st = stats.clone();
    let url = fb.url.clone();
    let b = thread::spawn(move || {
        let (tx, _rx) = mpsc::channel();
        let (b, _) = Bundle::new(st, tx);
        let runtime = Runtime::new().unwrap();
        assert!(
            runtime
                .probe_inner()
                .block_on(b.run(unit, 80, 6, url))
                .unwrap_err()
                .contains("handler failed")
        );
        b.http.cancel();
        runtime.probe_inner().block_on(b.retire());
        runtime.drain_shutdown().unwrap();
        assert_eq!(runtime.probe_inner().metrics().num_alive_tasks(), 0);
    });
    b.join().unwrap();
    assert_eq!(
        fb.events.recv_timeout(Duration::from_secs(5)).unwrap(),
        "request"
    );
    assert_eq!(
        fb.events.recv_timeout(Duration::from_secs(5)).unwrap(),
        "clean EOF"
    );
    assert!(matches!(
        fa.events.try_recv(),
        Err(mpsc::TryRecvError::Empty)
    ));
    go_tx.send(()).unwrap();
    fa.reply.send(()).unwrap();
    a.join().unwrap();
    fa.thread.join().unwrap();
    fb.thread.join().unwrap();
    count(&stats, 2);
    emit(
        json!({"event":"cross_worker_http","failed_socket":"clean EOF","healthy_survived":true,"tasks_after":0,"retired":2}),
    );
}
#[test]
#[ignore = "isolated server assembly measurement, driven by run.py"]
fn assembly_gate() {
    let unit = compiled();
    scheduling(unit.clone());
    lifecycle_isolation(unit.clone());
    http_cross_worker(unit.clone());
    http_same_worker(unit);
}
