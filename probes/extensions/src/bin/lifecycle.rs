//! Record 0053's external assembly fixture; no rnx-private API or executor.
use std::future::Future;
use std::pin::Pin;
use std::rc::Rc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::task::{Context, Poll};
static LIVE: AtomicUsize = AtomicUsize::new(0);
struct Pending {
    started: bool,
    panic: bool,
    _local: Rc<()>,
}
impl Future for Pending {
    type Output = Result<i64, String>;
    fn poll(mut self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<Self::Output> {
        if !self.started {
            self.started = true;
            LIVE.fetch_add(1, Ordering::Relaxed);
            eprintln!("lifecycle opened");
        }
        Poll::Pending
    }
}
impl Drop for Pending {
    fn drop(&mut self) {
        if self.started {
            LIVE.fetch_sub(1, Ordering::Relaxed);
            eprintln!("lifecycle closed");
            assert!(!self.panic, "injected lifecycle destructor panic");
        }
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(
        rnx::Extensions::none().with_lifecycle("fixture", |module, scope| {
            let ready = scope.clone();
            module
                .function("ready", move || ready.track(async { Ok(42i64) }))
                .build()
                .map_err(|e| e.to_string())?;
            module
                .function("pending", move |panic: bool| {
                    scope.track(Pending {
                        started: false,
                        panic,
                        _local: Rc::new(()),
                    })
                })
                .build()
                .map_err(|e| e.to_string())?;
            module
                .function("live", || LIVE.load(Ordering::Relaxed) as i64)
                .build()
                .map_err(|e| e.to_string())?;
            Ok(vec![
                (
                    "fixture::pending".into(),
                    "pending(panic_on_drop) -> tracked future",
                ),
                ("fixture::ready".into(), "ready() -> 42"),
            ])
        }),
    )
}
