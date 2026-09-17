fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with("probe", |_module| {
        if let Some(path) = std::env::var_os("RNX_GATE2_BUILDER") {
            std::fs::write(path, b"builder ran").map_err(|e| e.to_string())?;
        }
        Ok(Vec::new())
    }))
}
