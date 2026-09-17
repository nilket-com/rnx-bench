//! Prototype boundary. Counters and context assertions are observation hooks.
use std::sync::atomic::{AtomicUsize, Ordering};
static STARTED: AtomicUsize = AtomicUsize::new(0);
static FINISHED: AtomicUsize = AtomicUsize::new(0);
static JOINED: AtomicUsize = AtomicUsize::new(0);
static ACTIVE: AtomicUsize = AtomicUsize::new(0);
static MAX_ACTIVE: AtomicUsize = AtomicUsize::new(0);
static NO_CONTEXT: AtomicUsize = AtomicUsize::new(0);
struct Finished;
impl Drop for Finished {
    fn drop(&mut self) {
        ACTIVE.fetch_sub(1, Ordering::SeqCst);
        FINISHED.fetch_add(1, Ordering::SeqCst);
    }
}
pub fn run<T: Send>(call: impl FnOnce() -> T + Send) -> Result<T, String> {
    std::thread::scope(|scope| {
        let worker = std::thread::Builder::new()
            .name("rnx-polars-engine".into())
            .spawn_scoped(scope, move || {
                STARTED.fetch_add(1, Ordering::SeqCst);
                let active = ACTIVE.fetch_add(1, Ordering::SeqCst) + 1;
                MAX_ACTIVE.fetch_max(active, Ordering::SeqCst);
                let _finished = Finished;
                assert!(tokio::runtime::Handle::try_current().is_err());
                NO_CONTEXT.fetch_add(1, Ordering::SeqCst);
                call()
            })
            .map_err(|e| format!("cannot start Polars engine thread: {e}"))?;
        let result = worker.join();
        JOINED.fetch_add(1, Ordering::SeqCst);
        match result {
            Ok(value) => Ok(value),
            Err(panic) => std::panic::resume_unwind(panic),
        }
    })
}
pub fn counts() -> (usize, usize, usize, usize, usize, usize) {
    (
        STARTED.load(Ordering::SeqCst),
        FINISHED.load(Ordering::SeqCst),
        JOINED.load(Ordering::SeqCst),
        ACTIVE.load(Ordering::SeqCst),
        MAX_ACTIVE.load(Ordering::SeqCst),
        NO_CONTEXT.load(Ordering::SeqCst),
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn panic_is_joined_before_resuming_on_the_caller() {
        let panic = std::panic::catch_unwind(|| run(|| panic!("engine-panic-marker")));
        assert!(panic.is_err());
        assert_eq!(counts(), (1, 1, 1, 0, 1, 1));
    }
}
