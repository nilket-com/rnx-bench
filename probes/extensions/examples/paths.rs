use rnx::rune::{self, Context, Module, Source, Sources, Vm};
use std::sync::Arc;
#[derive(rune::Any)]
#[rune(crate = rnx::rune, item = ::other)]
struct Elsewhere;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut module = Module::with_crate("fixture")?;
    module.function("nested::answer", || 42i64).build()?;
    let mut context = Context::with_default_modules()?;
    context.install(module)?;
    for path in ["fixture::nested::answer()", "nested::answer()"] {
        let mut sources = Sources::new();
        sources.insert(Source::memory(format!("pub fn main() {{ {path} }}"))?)?;
        match rune::prepare(&mut sources).with_context(&context).build() {
            Ok(unit) => {
                let mut vm = Vm::new(Arc::new(context.runtime()?), Arc::new(unit));
                println!(
                    "{path}: {}",
                    rune::from_value::<i64>(vm.call(["main"], ())?)?
                );
            }
            Err(error) => println!("{path}: refused: {error}"),
        }
    }
    let mut module = Module::with_crate("fixture")?;
    module.ty::<Elsewhere>()?;
    let mut types = Context::with_default_modules()?;
    match types.install(module) {
        Ok(()) => println!("type item ::other: installed"),
        Err(error) => println!("type item ::other: refused: {error}"),
    }
    for path in [
        "fixture::Elsewhere",
        "other::Elsewhere",
        "::other::Elsewhere",
    ] {
        let mut sources = Sources::new();
        sources.insert(Source::memory(format!("pub fn main() {{ () is {path} }}"))?)?;
        println!(
            "type name {path}: compiles={}",
            rune::prepare(&mut sources)
                .with_context(&types)
                .build()
                .is_ok()
        );
    }
    println!(
        "native type item: {}",
        <Elsewhere as rune::compile::Named>::ITEM
    );
    types.install(Module::with_crate("other")?)?;
    let mut sources = Sources::new();
    sources.insert(Source::memory("pub fn main() { () is other::Elsewhere }")?)?;
    println!(
        "other::Elsewhere after declaring other crate: compiles={}",
        rune::prepare(&mut sources)
            .with_context(&types)
            .build()
            .is_ok()
    );
    Ok(())
}
