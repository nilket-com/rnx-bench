use rune::{Context, Diagnostics, Source, Sources, Vm};
use std::sync::Arc;
fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    if mode == "none" { return; }
    let mut context = Context::with_default_modules().unwrap();
    if mode != "context" {
        context.install(rune_modules::json::module(true).unwrap()).unwrap();
        context.install(rune_modules::fs::module(true).unwrap()).unwrap();
        context.install(rune_modules::time::module(true).unwrap()).unwrap();
        context.install(rune_modules::toml::module(true).unwrap()).unwrap();
        context.install(rune_modules::process::module(true).unwrap()).unwrap();
        context.install(rune_modules::rand::module(true).unwrap()).unwrap();
        context.install(rune_modules::base64::module(true).unwrap()).unwrap();
        if mode != "nohttp" { context.install(rune_modules::http::module(true).unwrap()).unwrap(); }
    }
    if mode == "context" || mode == "modules" || mode == "nohttp" { return; }
    // "run": also stand up a tokio runtime and drive an async call, the shape http::get needs.
    let runtime = Arc::new(context.runtime().unwrap());
    let mut sources = Sources::new();
    sources.insert(Source::memory("pub async fn main() { let x = time::Duration::from_millis(1); 42 }").unwrap()).unwrap();
    let mut d = Diagnostics::new();
    let unit = rune::prepare(&mut sources).with_context(&context).with_diagnostics(&mut d).build().unwrap();
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    let mut vm = Vm::new(runtime, Arc::new(unit));
    let v: i64 = rt.block_on(async { rune::from_value(vm.async_call(["main"], ()).await.unwrap()).unwrap() });
    println!("{v}");
}
