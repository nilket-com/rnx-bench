#[cfg(feature = "stock-management")]
mod coordinates {
    include!(concat!(env!("OUT_DIR"), "/coordinates.rs"));
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    #[cfg(feature = "stock-management")]
    {
        let args = std::env::args_os().skip(1).collect::<Vec<_>>();
        if args.first().and_then(|a| a.to_str()) == Some("--probe-coordinates") {
            println!(
                "{}",
                serde_json::json!({"url":coordinates::URL,"rev":coordinates::REV,"state":coordinates::STATE,"source":coordinates::SOURCE})
            );
            return Ok(());
        }
        // Gate 1 only: this exercises the coordinate decision, not the REPL protocol.
        if args.first().and_then(|a| a.to_str()) == Some("--probe-dep") {
            if matches!(coordinates::STATE, "dirty" | "unknown") {
                eprintln!(
                    "dependency preparation refused: {} {} {}; export RNX_DEP_RUNTIME={:?}",
                    coordinates::URL,
                    coordinates::REV,
                    coordinates::STATE,
                    coordinates::SOURCE
                );
                std::process::exit(2);
            }
            println!(
                "Runtime: {} {} ({})",
                coordinates::URL,
                coordinates::REV,
                if coordinates::STATE == "unverified" {
                    "not yet confirmed reachable"
                } else {
                    "acquired"
                }
            );
            if !args.iter().any(|a| a == "--consent") {
                return Ok(());
            }
            let root = std::path::PathBuf::from(
                std::env::var_os("RNX_PROBE_REQUEST_DIR")
                    .ok_or("fixture request directory required")?,
            );
            std::fs::create_dir_all(root.join("src"))?;
            std::fs::write(
                root.join("Cargo.toml"),
                format!(
                    "[package]\nname=\"coordinate-request\"\nversion=\"0.0.0\"\nedition=\"2024\"\n[workspace]\n[dependencies]\nrnx={{git={:?},rev={:?},default-features=false}}\n",
                    coordinates::URL,
                    coordinates::REV
                ),
            )?;
            std::fs::write(root.join("src/main.rs"), "fn main() {}\n")?;
            let status = std::process::Command::new("cargo")
                .args(["metadata", "--format-version=1", "--manifest-path"])
                .arg(root.join("Cargo.toml"))
                .status()?;
            if !status.success() {
                eprintln!(
                    "acquisition refused; export RNX_DEP_RUNTIME={:?}",
                    coordinates::SOURCE
                );
                std::process::exit(3);
            }
            return Ok(());
        }
        if let Some(group) = args.first().and_then(|a| a.to_str()) {
            let selected = match group {
                "project" => Some(args[1..].to_vec()),
                "runtime" | "cache" => Some(args.clone()),
                _ => None,
            };
            if let Some(args) = selected {
                if let Err(e) = rnx_project::dispatch(args) {
                    eprintln!("rnx: {e}");
                    std::process::exit(rnx_project::failure_status());
                }
                return Ok(());
            }
        }
    }
    rnx::main_with(rnx::Extensions::none())
}
