#![allow(dead_code)]
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
mod host { pub struct HostFunction { pub path: String, pub doc: &'static str } }
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
