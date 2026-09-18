//! Test-only adapter around private core functions, not the product CLI.
mod artifact;
mod assembly;
mod cache_entry;
mod cache_identity;
mod cache_storage;
#[allow(dead_code)]
mod commands;
mod fingerprint;
mod generate;
mod graph;
mod handshake;
mod input;
mod inventory;
mod manifest;
mod wire;

use sha2::{Digest, Sha256};
use std::{path::PathBuf, process::Command};
#[derive(serde::Deserialize)]
struct Config {
	metadata: serde_json::Value,
	stage: PathBuf,
	invocation: PathBuf,
	home: PathBuf,
	expected: Option<String>,
	executable: PathBuf,
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
	let path = std::env::args_os().nth(1).ok_or("config required")?;
	let config: Config = serde_json::from_slice(&std::fs::read(path)?)?;
	let t = std::time::Instant::now();
	let inv = inventory::native(
		&serde_json::to_vec(&config.metadata)?,
		&config.stage,
		&config.invocation,
		&config.home,
		&mut fingerprint::Allowance::default(),
	)?;
	let inventory_ms = t.elapsed().as_secs_f64() * 1000.0;
	let bytes = serde_json::to_vec(&inv)?;
	let digest = format!("{:x}", Sha256::digest(&bytes));
	if let Some(expected) = config.expected {
		assert_eq!(digest, expected);
		eprintln!("INVENTORY_RESULT {digest} {inventory_ms}");
		use std::os::unix::process::CommandExt;
		return Err(Command::new(config.executable)
			.args(["--no-splash", "--color=never", "eval", "42"])
			.exec()
			.into());
	}
	println!(
		"{}",
		serde_json::to_string(&serde_json::json!({"digest":digest,"inventory":inv}))?
	);
	Ok(())
}
