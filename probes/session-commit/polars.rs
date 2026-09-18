use std::io::Write;
pub fn build(m: &mut rnx::rune::Module) -> Result<Vec<(String, &'static str)>, String> {
    let probe = std::env::var_os("RNX_INTERNAL_STARTUP_FD").is_some();
    if let Some(path) = std::env::var_os("STARTUP_EVENTS") {
        let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
        writeln!(f, "{} {}", std::process::id(), if probe {"probe"} else {"replacement"}).unwrap();
    }
    if !probe {
        match std::env::var("REPLACEMENT_MODE").as_deref() {
            Ok("error") => return Err("replacement-only builder refusal".into()),
            Ok("panic") => panic!("replacement-only builder panic"),
            _ => (),
        }
    }
    m.function("answer", || 73i64).build().map_err(|e| e.to_string())?;
    Ok(vec![])
}
