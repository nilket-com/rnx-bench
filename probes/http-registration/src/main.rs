#![allow(dead_code, unexpected_cfgs)]
// Import the actual rnx module being measured. Network code is never called.
#[path = "../../../../rnx/src/http.rs"]
mod http;
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
mod host { pub struct HostFunction { pub path: String, pub doc: &'static str } }
mod execute { pub struct Runtime; impl Runtime { pub fn drain_http(&self) -> Result<(), String> { unreachable!() } } }
fn main() {
    let mut base = std::time::Duration::ZERO;
    let mut install = std::time::Duration::ZERO;
    for _ in 0..100 {
        let start = std::time::Instant::now();
        let mut context = rune::Context::with_default_modules().unwrap();
        base += start.elapsed();
        let state = http::State::default();
        let start = std::time::Instant::now();
        http::install(&mut context, &state).unwrap();
        install += start.elapsed();
    }
    println!("100 constructions, same process; drop excluded: default context mean {:.3} ms; HTTP install mean {:.3} ms", base.as_secs_f64()*10., install.as_secs_f64()*10.);
}
