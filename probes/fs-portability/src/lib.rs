#![allow(dead_code)]
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
mod host {
    // Registration signatures only: never invoked by this cross-check.
    pub(crate) fn exit(_: i64) -> Result<(), String> { unimplemented!("type-check-only exit stub") }
    pub(crate) fn stdin_read() -> Result<String, String> { unimplemented!("type-check-only stdin stub") }
    pub(crate) fn eprint(_: &str) -> Result<(), String> { unimplemented!("type-check-only stderr stub") }

    pub struct HostFunction { pub path: String, pub doc: &'static str }
    // Type-check the facade without pretending to exercise process supervision.
    pub(crate) fn configured_process(
        _: &str, _: rune::Value, _: u64, _: Option<Vec<u8>>,
        _: &crate::process::Launch, _: bool,
    ) -> Result<rune::Value, String> { unimplemented!("type-check-only supervisor stub") }
}
#[path = "../../../../rnx/src/fs.rs"] mod fs;
#[path = "../../../../rnx/src/fs_platform.rs"] mod fs_platform;
#[cfg(test)]
fn compile(context: &rune::Context, text: &str) -> Result<()> {
    let mut sources = rune::Sources::new();
    sources.insert(rune::Source::new("probe", text)?)?;
    rune::prepare(&mut sources).with_context(context).build()?;
    Ok(())
}
#[path = "../../../../rnx/src/env.rs"] mod env;

#[path = "../../../../rnx/src/path.rs"] mod path;

#[path = "../../../../rnx/src/time.rs"] mod time;

#[path = "../../../../rnx/src/process.rs"] mod process;

#[path = "../../../../rnx/src/io.rs"] mod io;
