//! An external trusted adapter. No access to rnx's private modules.
use rnx::rune::Module;
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::task::{Context, Poll, Waker};

fn marker() {
    use std::io::Write;
    if let Some(path) = std::env::var_os("RNX_FIXTURE_MARKER") {
        writeln!(
            std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .unwrap(),
            "builder"
        )
        .unwrap();
        eprintln!("fixture builder marker");
    }
}

// A small waking future keeps this fixture dependent on rnx alone. The
// thread is for this test timer, not an adapter/runtime recommendation.
struct Sleep {
    state: Arc<Mutex<(bool, Option<Waker>)>>,
}
impl Future for Sleep {
    type Output = ();
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        let mut state = self.state.lock().unwrap();
        if state.0 {
            Poll::Ready(())
        } else {
            state.1 = Some(cx.waker().clone());
            Poll::Pending
        }
    }
}
async fn later(ms: u64) -> Result<u64, String> {
    let state = Arc::new(Mutex::new((false, None::<Waker>)));
    let other = state.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(ms));
        let wake = {
            let mut state = other.lock().unwrap();
            state.0 = true;
            state.1.take()
        };
        if let Some(wake) = wake {
            wake.wake();
        }
    });
    Sleep { state }.await;
    Ok(ms)
}

pub fn build(module: &mut Module) -> Result<Vec<(String, &'static str)>, String> {
    marker();
    module
        .function("answer", || 42i64)
        .build()
        .map_err(|e| e.to_string())?;
    module
        .function("later", later)
        .build()
        .map_err(|e| e.to_string())?;
    module
        .function("fail", || Err::<(), _>("fixture failure".to_owned()))
        .build()
        .map_err(|e| e.to_string())?;
    Ok(vec![
        ("fixture::answer".into(), "answer() -> 42"),
        ("fixture::later".into(), "later(ms) -> future<Result<u64>>"),
        ("fixture::fail".into(), "fail() -> Err(\"fixture failure\")"),
    ])
}

pub fn broken() -> rnx::Extensions {
    let mode = std::env::var("RNX_FIXTURE_CASE").unwrap_or_default();
    let extensions = rnx::Extensions::none().with("fixture", build);
    match mode.as_str() {
        "json" => extensions.with("json", |_| panic!("must not run")),
        "std" => extensions.with("std", |_| panic!("must not run")),
        "duplicate" => extensions.with("fixture", |_| panic!("must not run")),
        "empty" => extensions.with("", |_| panic!("must not run")),
        "invalid" => extensions.with("two words", |_| panic!("must not run")),
        "help" => extensions.with("sibling", |_| Ok(vec![("other::thing".into(), "wrong")])),
        "install" => extensions.with("sibling", |module| {
            *module = Module::with_crate("fixture").map_err(|e| e.to_string())?;
            module
                .function("answer", || 7i64)
                .build()
                .map_err(|e| e.to_string())?;
            Ok(vec![])
        }),
        "panic" => extensions.with("sibling", |_| panic!("builder boom")),
        "thread-panic" => extensions.with("sibling", |_| {
            let _ = std::thread::spawn(|| panic!("other thread boom")).join();
            Ok(vec![])
        }),
        "replace" => extensions.with("sibling", |module| {
            *module = Module::with_crate("fs").map_err(|e| e.to_string())?;
            module
                .function("extension_probe", || 17i64)
                .build()
                .map_err(|e| e.to_string())?;
            Ok(vec![])
        }),
        _ => extensions.with("sibling", |_| Err("deliberately broken".into())),
    }
}
