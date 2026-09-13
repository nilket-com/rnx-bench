//! Deterministic model of hyper-util's GaiResolver: started spawn_blocking
//! lookup, with abort-on-drop. No actual DNS or public network is used.
use std::{sync::Arc, time::{Duration, Instant}, future::Future, pin::Pin, task::{Context, Poll}};
#[derive(Debug)]
struct SlowResolver;
struct Lookup(tokio::task::JoinHandle<std::io::Result<Vec<std::net::SocketAddr>>>);
impl Future for Lookup {
    type Output = Result<reqwest::dns::Addrs, Box<dyn std::error::Error + Send + Sync>>;
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        match Pin::new(&mut self.0).poll(cx) {
            Poll::Pending => Poll::Pending,
            Poll::Ready(Ok(Ok(addresses))) => Poll::Ready(Ok(Box::new(addresses.into_iter()))),
            Poll::Ready(Ok(Err(e))) => Poll::Ready(Err(e.into())),
            Poll::Ready(Err(e)) => Poll::Ready(Err(e.into())),
        }
    }
}
impl Drop for Lookup { fn drop(&mut self) { self.0.abort(); } }
impl reqwest::dns::Resolve for SlowResolver {
    fn resolve(&self, _: reqwest::dns::Name) -> reqwest::dns::Resolving {
        Box::pin(Lookup(tokio::task::spawn_blocking(|| {
            std::thread::sleep(Duration::from_secs(2));
            Err(std::io::Error::other("controlled slow DNS failure"))
        })))
    }
}
fn main() {
    let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    let client = reqwest::Client::builder().no_proxy().dns_resolver(Arc::new(SlowResolver)).build().unwrap();
    let start = Instant::now();
    let error = runtime.block_on(async { client.get("http://controlled.invalid/").timeout(Duration::from_millis(50)).send().await }).unwrap_err();
    println!("request timed out: {}; elapsed {:?}", error.is_timeout(), start.elapsed());
    drop(client);
    runtime.block_on(async { tokio::time::sleep(Duration::from_millis(10)).await; });
    println!("async tasks before runtime drop: {}; elapsed {:?}", runtime.metrics().num_alive_tasks(), start.elapsed());
    drop(runtime);
    println!("runtime drop finished; total elapsed {:?}", start.elapsed());
}
