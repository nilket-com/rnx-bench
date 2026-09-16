use rnx::{
    Extensions,
    rune::{
        self,
        runtime::{Object, Value},
    },
    server::{Failure, Invocation, Program},
};
use std::{
    future::Future,
    pin::Pin,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst},
    },
    task::{Context, Poll, Waker},
};
#[derive(Default)]
struct Stats {
    builds: AtomicUsize,
    contexts_dropped: AtomicUsize,
    started: AtomicUsize,
    dropped: AtomicUsize,
    release: AtomicBool,
    trigger: AtomicBool,
    panic_drop: bool,
    value: Option<i64>,
    waker: std::sync::Mutex<Option<Waker>>,
    trigger_waker: std::sync::Mutex<Option<Waker>>,
}
struct Token(Arc<Stats>);
impl Drop for Token {
    fn drop(&mut self) {
        self.0.contexts_dropped.fetch_add(1, SeqCst);
    }
}
struct Operation {
    stats: Arc<Stats>,
    started: bool,
}
impl Future for Operation {
    type Output = Result<i64, String>;
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        *self.stats.waker.lock().unwrap() = Some(cx.waker().clone());
        if !self.started {
            self.started = true;
            self.stats.started.fetch_add(1, SeqCst);
        }
        if self.stats.release.load(SeqCst) {
            Poll::Ready(Ok(self.stats.value.unwrap_or(41)))
        } else {
            Poll::Pending
        }
    }
}
impl Drop for Operation {
    fn drop(&mut self) {
        self.stats.dropped.fetch_add(1, SeqCst);
        if self.stats.panic_drop {
            panic!("drop observer panic");
        }
    }
}
fn extensions(stats: Arc<Stats>) -> Extensions {
    Extensions::none().with_lifecycle("probe", move |module, scope| {
        stats.builds.fetch_add(1, SeqCst);
        let token = Arc::new(Token(stats.clone()));
        let wait_stats = stats.clone();
        module
            .function("wait", move || {
                let _ = &token;
                scope.track(Operation {
                    stats: wait_stats.clone(),
                    started: false,
                })
            })
            .build()
            .map_err(|e| e.to_string())?;
        module
            .function("trigger", move || {
                let stats = stats.clone();
                std::future::poll_fn(move |cx| {
                    *stats.trigger_waker.lock().unwrap() = Some(cx.waker().clone());
                    if stats.trigger.load(SeqCst) {
                        Poll::Ready(())
                    } else {
                        Poll::Pending
                    }
                })
            })
            .build()
            .map_err(|e| e.to_string())?;
        Ok(vec![])
    })
}
fn request() -> Value {
    let mut object = Object::new();
    object
        .insert(
            rune::alloc::String::try_from("n").unwrap(),
            Value::from(1i64),
        )
        .unwrap();
    Value::try_from(object).unwrap()
}
fn response(value: Value) {
    let object = value.borrow_ref::<Object>().unwrap();
    assert_eq!(
        object.get("status").unwrap().as_integer::<i64>().unwrap(),
        200
    );
    assert_eq!(object.get("body").unwrap().as_integer::<i64>().unwrap(), 42);
}
fn poll<F: Future + ?Sized>(future: Pin<&mut F>) -> Poll<F::Output> {
    future.poll(&mut Context::from_waker(Waker::noop()))
}
fn invocation(program: &Program, stats: Arc<Stats>, name: &str) -> Invocation {
    program
        .prepare(
            extensions(stats),
            &format!("handlers::{name}"),
            request(),
            10000,
        )
        .unwrap()
}
fn pending<T>(result: Poll<T>) {
    assert!(result.is_pending());
}
fn ready<T>(result: Poll<T>) -> T {
    match result {
        Poll::Ready(x) => x,
        _ => panic!("not ready"),
    }
}
fn category<T>(result: Result<T, Failure>, expected: &str) {
    match result {
        Err(error) => assert_eq!(error.category(), expected),
        _ => panic!("expected {expected}"),
    }
}
fn counts(stats: &Stats, builds: usize, operations: usize) {
    assert_eq!(stats.builds.load(SeqCst), builds);
    assert_eq!(stats.contexts_dropped.load(SeqCst), builds);
    assert_eq!(stats.started.load(SeqCst), operations);
    assert_eq!(stats.dropped.load(SeqCst), operations);
}
fn drop_started(program: &Program, panic_drop: bool) {
    let stats = Arc::new(Stats {
        panic_drop,
        ..Stats::default()
    });
    let mut invocation = invocation(program, stats.clone(), "healthy");
    let mut run = Box::pin(invocation.run());
    pending(poll(run.as_mut()));
    assert_eq!(stats.started.load(SeqCst), 1);
    assert_eq!(stats.dropped.load(SeqCst), 0);
    drop(run);
    // No executor turn or second input between drop and either observation.
    assert_eq!(stats.dropped.load(SeqCst), 1);
    category(
        invocation.close(),
        if panic_drop { "cleanup" } else { "cancelled" },
    );
    counts(&stats, 1, 1);
}
fn isolated(program: &Program) {
    let failed = Arc::new(Stats {
        value: Some(917),
        ..Stats::default()
    });
    let healthy = Arc::new(Stats::default());
    let mut first = invocation(program, failed.clone(), "failed");
    let mut second = invocation(program, healthy.clone(), "healthy");
    let mut bad = Box::pin(first.run());
    let mut good = Box::pin(second.run());
    pending(poll(bad.as_mut()));
    pending(poll(good.as_mut()));
    assert_eq!(failed.started.load(SeqCst), 1);
    assert_eq!(healthy.started.load(SeqCst), 1);
    failed.trigger.store(true, SeqCst);
    failed
        .trigger_waker
        .lock()
        .unwrap()
        .as_ref()
        .unwrap()
        .wake_by_ref();
    category(ready(poll(bad.as_mut())), "vm");
    drop(bad);
    assert_eq!(failed.dropped.load(SeqCst), 1);
    assert_eq!(healthy.dropped.load(SeqCst), 0);
    pending(poll(good.as_mut()));
    healthy.release.store(true, SeqCst);
    healthy
        .waker
        .lock()
        .unwrap()
        .as_ref()
        .unwrap()
        .wake_by_ref();
    response(ready(poll(good.as_mut())).unwrap());
    drop(good);
    category(first.close(), "vm");
    second.close().unwrap();
    counts(&failed, 1, 1);
    counts(&healthy, 1, 1);
}
fn cross_worker(program: &Program) {
    let barrier = Arc::new(std::sync::Barrier::new(2));
    let failed = Arc::new(Stats {
        value: Some(917),
        ..Stats::default()
    });
    let healthy = Arc::new(Stats::default());
    std::thread::scope(|threads| {
        for (stats, is_bad) in [(failed.clone(), true), (healthy.clone(), false)] {
            let barrier = barrier.clone();
            threads.spawn(move || {
                let runtime = tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build()
                    .unwrap();
                let _enter = runtime.enter();
                let mut invocation = invocation(
                    program,
                    stats.clone(),
                    if is_bad { "failed" } else { "healthy" },
                );
                let mut run = Box::pin(invocation.run());
                pending(poll(run.as_mut()));
                assert_eq!(stats.started.load(SeqCst), 1);
                barrier.wait();
                if is_bad {
                    stats.trigger.store(true, SeqCst);
                    stats
                        .trigger_waker
                        .lock()
                        .unwrap()
                        .as_ref()
                        .unwrap()
                        .wake_by_ref();
                    category(ready(poll(run.as_mut())), "vm");
                }
                barrier.wait();
                if !is_bad {
                    assert_eq!(stats.dropped.load(SeqCst), 0);
                    pending(poll(run.as_mut()));
                    stats.release.store(true, SeqCst);
                    stats.waker.lock().unwrap().as_ref().unwrap().wake_by_ref();
                    response(ready(poll(run.as_mut())).unwrap());
                }
                drop(run);
                if is_bad {
                    category(invocation.close(), "vm");
                } else {
                    invocation.close().unwrap();
                }
                counts(&stats, 1, 1);
            });
        }
    });
}
fn main() {
    fn shareable<T: Send + Sync>() {}
    shareable::<Program>();
    let schema = Arc::new(Stats::default());
    let program = Program::compile(
        concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/main.rn"),
        extensions(schema.clone()),
    )
    .unwrap();
    counts(&schema, 1, 0);
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap();
    let _enter = runtime.enter();
    drop_started(&program, false);
    println!("PASS started-drop-close synchronous cancellation");
    drop_started(&program, true);
    println!("PASS destructor panic wins over cancellation");
    let unwind_stats = Arc::new(Stats::default());
    let mut unwinding = invocation(&program, unwind_stats.clone(), "healthy");
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let mut run = Box::pin(unwinding.run());
        pending(poll(run.as_mut()));
        assert_eq!(unwind_stats.started.load(SeqCst), 1);
        panic!("caller unwinds with a polled invocation");
    }));
    std::panic::set_hook(previous);
    assert!(result.is_err());
    assert_eq!(unwind_stats.dropped.load(SeqCst), 1);
    category(unwinding.close(), "cancelled");
    counts(&unwind_stats, 1, 1);
    println!("PASS caller unwind preserves closeable cancelled execution");
    isolated(&program);
    println!("PASS same-worker started-operation isolation and counts");
    cross_worker(&program);
    println!("PASS cross-worker started-operation isolation and counts");
    for budget in [0, usize::MAX] {
        let stats = Arc::new(Stats::default());
        category(
            program.prepare(
                extensions(stats.clone()),
                "handlers::healthy",
                request(),
                budget,
            ),
            "preparation",
        );
        counts(&stats, 0, 0);
    }
    let mut cpu = program
        .prepare(Extensions::none(), "handlers::cpu", request(), 100)
        .unwrap();
    category(ready(poll(Box::pin(cpu.run()).as_mut())), "vm");
    category(ready(poll(Box::pin(cpu.run()).as_mut())), "preparation");
    category(cpu.close(), "vm");
    println!("PASS budget bounds, halt and no resumption");
    let mut named = invocation(&program, Arc::new(Stats::default()), "named");
    let failure = ready(poll(Box::pin(named.run()).as_mut())).unwrap_err();
    assert!(failure.message().contains("missing"));
    assert!(failure.path().unwrap().ends_with("handlers.rn"));
    assert_eq!(failure.position().unwrap().0, 14);
    assert!(failure.excerpt().unwrap().contains("1.missing()"));
    category(named.close(), "vm");
    let mut exit = invocation(&program, Arc::new(Stats::default()), "exit");
    let value = ready(poll(Box::pin(exit.run()).as_mut())).unwrap();
    assert!(value.borrow_ref::<Result<Value, Value>>().unwrap().is_err());
    drop(value);
    exit.close().unwrap();
    println!("PASS module diagnostics and catchable server exit");
    let failure_stats = Arc::new(Stats::default());
    let extra = extensions(failure_stats.clone())
        .with("broken", |_| Err("fixture installation refusal".into()));
    category(
        program.prepare(extra, "handlers::healthy", request(), 1000),
        "preparation",
    );
    counts(&failure_stats, 1, 0);
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/invalid.rn");
    let failure = match Program::compile(path, Extensions::none()) {
        Err(failure) => failure,
        Ok(_) => panic!("invalid module compiled"),
    };
    assert_eq!(failure.category(), "preparation");
    assert!(failure.path().unwrap().ends_with("bad.rn"));
    assert!(failure.excerpt().unwrap().contains("absent"));
    println!("PASS partial-context retirement and owned compile diagnostics");
}
