use rnx::rune;
use std::{
    future::Future,
    io::Write,
    pin::Pin,
    rc::Rc,
    sync::Arc,
    task::{Context, Poll},
};
fn event(s: &str) {
    let mut f = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(std::env::var("RNX_PROBE_EVENTS").unwrap())
        .unwrap();
    writeln!(f, "{} {s}", std::process::id()).unwrap();
}
struct ContextOwner;
impl Drop for ContextOwner {
    fn drop(&mut self) {
        event("context dropped");
    }
}
#[derive(rnx::rune::Any)]
struct ValueOwner;
impl Drop for ValueOwner {
    fn drop(&mut self) {
        event("value dropped");
    }
}
struct Pending {
    started: bool,
    panic: bool,
    _local: Rc<()>,
}
impl Future for Pending {
    type Output = Result<i64, String>;
    fn poll(mut self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<Self::Output> {
        event("poll");
        if std::path::Path::new(&std::env::var("RNX_PROBE_RELEASE").unwrap()).exists() {
            return Poll::Ready(Ok(73));
        }
        if !self.started {
            self.started = true;
            event("operation polled");
        }
        Poll::Pending
    }
}
impl Drop for Pending {
    fn drop(&mut self) {
        if self.started {
            event("operation dropped");
            assert!(!self.panic, "injected destructor failure");
        }
    }
}
thread_local! {static HELD:std::cell::RefCell<Option<Pin<Box<dyn Future<Output=Result<i64,String>>>>>>=const{std::cell::RefCell::new(None)};}
struct BadDrop;
impl Future for BadDrop {
    type Output = Result<i64, String>;
    fn poll(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<Self::Output> {
        Poll::Pending
    }
}
impl Drop for BadDrop {
    fn drop(&mut self) {
        panic!("probe cleanup injected failure")
    }
}
pub fn build(
    m: &mut rnx::rune::Module,
    scope: rnx::Scope,
) -> Result<Vec<(String, &'static str)>, String> {
    event("fixture builder");
    if std::env::var_os("RNX_INTERNAL_STARTUP_FD").is_some()
        && std::env::var("STARTUP_MODE").as_deref() == Ok("cleanup")
    {
        HELD.with(|v| *v.borrow_mut() = Some(Box::pin(scope.track(BadDrop))));
    }
    m.ty::<ValueOwner>().map_err(|e| e.to_string())?;
    m.function("value", || ValueOwner)
        .build()
        .map_err(|e| e.to_string())?;
    let owner = Arc::new(ContextOwner);
    m.function("owner", move || {
        let _ = &owner;
        42i64
    })
    .build()
    .map_err(|e| e.to_string())?;
    m.function("pending", move |panic: bool| {
        scope.track(Pending {
            started: false,
            panic,
            _local: Rc::new(()),
        })
    })
    .build()
    .map_err(|e| e.to_string())?;
    Ok(vec![])
}
