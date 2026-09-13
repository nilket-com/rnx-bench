use rune::{Context, Diagnostics, Source, Sources, Vm};
use std::sync::Arc;
// Process-level phases, so hyperfine can compare like with like against rnx.
fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    if mode == "none" { return; }
    let context = Context::with_default_modules().unwrap();
    if mode == "context" { return; }
    let runtime = Arc::new(context.runtime().unwrap());
    if mode == "runtime" { return; }
    let mut sources = Sources::new();
    sources.insert(Source::memory("pub fn main() { 42 }").unwrap()).unwrap();
    let mut d = Diagnostics::new();
    let unit = rune::prepare(&mut sources).with_context(&context).with_diagnostics(&mut d).build().unwrap();
    if mode == "compile" { return; }
    let mut vm = Vm::new(runtime, Arc::new(unit));
    let v: i64 = rune::from_value(vm.call(["main"], ()).unwrap()).unwrap();
    println!("{v}");
}
