mod pool;
mod scheduling;
use rune::{Context, Source, Sources, Vm};
use std::sync::Arc;

fn compile(
    module: rune::Module,
    source: &str,
) -> (Arc<rune::runtime::RuntimeContext>, Arc<rune::Unit>) {
    let mut context = Context::with_config(false).unwrap();
    context.install(module).unwrap();
    let mut sources = Sources::new();
    sources.insert(Source::memory(source).unwrap()).unwrap();
    let mut diagnostics = rune::Diagnostics::new();
    let unit = rune::prepare(&mut sources)
        .with_context(&context)
        .with_diagnostics(&mut diagnostics)
        .build()
        .unwrap_or_else(|e| panic!("compile: {e}; {diagnostics:?}"));
    (Arc::new(context.runtime().unwrap()), Arc::new(unit))
}

// Exactly one whole budget, never resume after a halt. This does not propose
// fixing or bypassing Rune 0.14.2's nested-async resumption defect.
async fn execute(vm: &mut Vm, mode: i64, budget: usize) -> Result<String, String> {
    let mut execution = vm.execute(["main"], (mode,)).map_err(|e| e.to_string())?;
    match rune::runtime::budget::with(budget, execution.async_resume())
        .await
        .into_result()
    {
        Ok(rune::runtime::GeneratorState::Complete(v)) => Ok(format!("{v:?}")),
        Ok(_) => Err("unexpected generator yield".into()),
        Err(e) => Err(e.to_string()),
    }
}
fn runtime() -> tokio::runtime::Runtime {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
}
fn sockets() -> usize {
    std::fs::read_dir("/proc/self/fd")
        .unwrap()
        .filter_map(Result::ok)
        .filter_map(|e| std::fs::read_link(e.path()).ok())
        .filter(|p| p.to_string_lossy().starts_with("socket:["))
        .count()
}
fn main() {
    match std::env::args().nth(1).as_deref() {
        Some("scheduling") => scheduling::run(),
        Some("pool") => pool::run(&std::env::var("PROBE_DATABASE_URL").unwrap()),
        _ => panic!("expected scheduling or pool"),
    }
}
