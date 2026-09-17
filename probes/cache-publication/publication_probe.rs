//! Isolated gate-one adapter. The imported modules are byte-identical to the
//! accepted product; this file is prototype policy, not a public cache API.
#![allow(dead_code)]
mod artifact;
mod cache_entry;
mod cache_identity;
mod cache_storage;
mod commands;
mod fingerprint;
mod generate;
mod graph;
mod input;
mod inventory;
mod manifest;
mod wire;
use sha2::{Digest, Sha256};
use std::{
	fs,
	path::{Path, PathBuf},
};
fn error(e: impl std::fmt::Display) -> String {
	e.to_string()
}
fn forbidden(dir: &Path, stage: bool) -> Result<(), String> {
	for name in [
		"Cargo.toml",
		".cargo/config",
		".cargo/config.toml",
		"rust-toolchain",
		"rust-toolchain.toml",
	] {
		if stage && name == "Cargo.toml" {
			continue;
		}
		let p = dir.join(name);
		match fs::symlink_metadata(&p) {
			Ok(_) => return Err(format!("unexpected managed Cargo input {}", p.display())),
			Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
			Err(e) => return Err(error(e)),
		}
	}
	// A .cargo symlink with absent target files must not bypass the checks.
	if let Ok(m) = fs::symlink_metadata(dir.join(".cargo"))
		&& !m.is_dir()
	{
		return Err(format!(
			"managed .cargo is not a directory: {}",
			dir.display()
		));
	}
	Ok(())
}
fn root(path: &Path) -> Result<PathBuf, String> {
	let root = path.canonicalize().map_err(error)?;
	private_directory(&root)?;
	Ok(root)
}
fn private_directory(path: &Path) -> Result<(), String> {
	use std::os::unix::fs::MetadataExt;
	let m = fs::symlink_metadata(path).map_err(error)?;
	if !m.is_dir() || m.uid() != unsafe { libc::geteuid() } || m.mode() & 0o022 != 0 {
		return Err(format!("not a private owned directory: {}", path.display()));
	}
	Ok(())
}
fn guard(root: &Path, stage: &Path, project: &Path) -> Result<(), String> {
	// Only the selected root may have a user symlink spelling. Below it, walk
	// lexical components rather than canonicalizing away a managed symlink.
	let relative = stage.strip_prefix(root).map_err(error)?;
	if relative.as_os_str().is_empty() {
		return Err("stage must be below cache root".into());
	}
	let mut cursor = root.to_owned();
	for component in relative.components() {
		let std::path::Component::Normal(part) = component else {
			return Err("non-normal managed path".into());
		};
		cursor.push(part);
		private_directory(&cursor)?;
		forbidden(&cursor, cursor == stage)?;
	}
	match fs::symlink_metadata(stage.join("src")) {
		Ok(_) => private_directory(&stage.join("src"))?,
		Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
		Err(e) => return Err(error(e)),
	}
	for name in ["Cargo.toml", "Cargo.lock", "src/main.rs"] {
		let path = stage.join(name);
		match fs::symlink_metadata(&path) {
			Ok(m) if !m.is_file() => {
				return Err(format!("managed input is not regular: {}", path.display()));
			}
			Ok(_) => (),
			Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
			Err(e) => return Err(error(e)),
		}
	}
	let cache_ancestors: Vec<_> = root.ancestors().collect();
	for dir in project.ancestors().filter(|p| !cache_ancestors.contains(p)) {
		for name in [
			".cargo/config",
			".cargo/config.toml",
			"rust-toolchain",
			"rust-toolchain.toml",
		] {
			let p = dir.join(name);
			match fs::symlink_metadata(&p) {
				Ok(_) => {
					return Err(format!(
						"project Cargo input {} is outside shared cache context {}",
						p.display(),
						root.display()
					));
				}
				Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
				Err(e) => return Err(error(e)),
			}
		}
	}
	Ok(())
}
fn policy(inv: &inventory::Inventory) -> Result<(), String> {
	for external in &inv.external {
		let Some(file) = &external.file else { continue };
		if !matches!(
			external.path.file_name().and_then(|s| s.to_str()),
			Some("config" | "config.toml")
		) {
			continue;
		}
		let bytes = input::read(&external.path, input::MANIFEST_LIMIT)?;
		if format!("{:x}", Sha256::digest(&bytes)) != file.sha256 {
			return Err("config changed".into());
		}
		let config: toml::Value =
			toml::from_str(std::str::from_utf8(&bytes).map_err(error)?).map_err(error)?;
		for key in config.as_table().ok_or("config is not a table")?.keys() {
			if !matches!(
				key.as_str(),
				"http" | "net" | "registry" | "registries" | "term"
			) {
				return Err(format!(
					"unsupported Cargo configuration key {key} in {}",
					external.path.display()
				));
			}
		}
	}
	Ok(())
}
fn run() -> Result<(), String> {
	let args: Vec<_> = std::env::args_os().skip(1).collect();
	if args.len() < 4 {
		return Err("prepare|audit|guard ROOT STAGE PROJECT [METADATA CARGO_HOME]".into());
	}
	let root = root(Path::new(&args[1]))?;
	let stage = Path::new(&args[2]);
	let project = Path::new(&args[3]);
	guard(&root, stage, project)?;
	match args[0].to_str() {
		Some("prepare") if args.len() == 4 => {
			let mut m = manifest::Manifest::read(&project.join("rnx.toml"))?;
			let canonical = |s: &str| -> Result<String, String> {
				project
					.join(s)
					.canonicalize()
					.map_err(error)?
					.into_os_string()
					.into_string()
					.map_err(|_| "non-Unicode native root".into())
			};
			if let Some(runtime) = &mut m.runtime {
				runtime.path = canonical(&runtime.path)?;
			}
			for native in m.native.values_mut() {
				native.path = canonical(&native.path)?;
			}
			let (cargo, main) = generate::wrapper(&m, project)?;
			fs::create_dir_all(stage.join("src")).map_err(error)?;
			fs::write(stage.join("Cargo.toml"), cargo).map_err(error)?;
			fs::write(stage.join("src/main.rs"), main).map_err(error)?;
			Ok(())
		}
		Some("preflight") if args.len() == 5 => {
			let metadata =
				wire::encode(&serde_json::json!({"workspace_root":stage,"packages":[]}))?;
			let inv = inventory::native(
				&metadata,
				stage,
				&root,
				Path::new(&args[4]),
				&mut fingerprint::Allowance::default(),
			)?;
			policy(&inv)?;
			println!("{}", String::from_utf8(wire::pretty(&inv)?).map_err(error)?);
			Ok(())
		}
		Some("identity" | "identity-shuffled") if args.len() == 8 => {
			use std::io::Write;
			let metadata = input::read(Path::new(&args[4]), input::DOCUMENT_LIMIT)?;
			let mut inv = inventory::native(
				&metadata,
				stage,
				&root,
				Path::new(&args[5]),
				&mut fingerprint::Allowance::default(),
			)?;
			policy(&inv)?;
			if args[0] == "identity-shuffled" {
				inv.packages.reverse();
				inv.trees.reverse();
				inv.external.reverse();
				for tree in &mut inv.trees {
					tree.files.reverse();
				}
			}
			let context: cache_identity::Context =
				serde_json::from_slice(&input::read(Path::new(&args[6]), input::DOCUMENT_LIMIT)?)
					.map_err(error)?;
			if context.cache_root.canonicalize().map_err(error)? != root
				|| context.cargo_home != Path::new(&args[5])
			{
				return Err("fixture context mismatch".into());
			}
			let lock = input::read(Path::new(&args[7]), input::DOCUMENT_LIMIT)?;
			let manifest = manifest::Manifest::read(&project.join("rnx.toml"))?;
			let identity =
				cache_identity::Identity::create(&manifest, project, context, inv, &lock)?;
			let decoded = cache_identity::Identity::decode(identity.bytes())?;
			if decoded.key() != identity.key() {
				return Err("identity round trip changed key".into());
			}
			std::io::stdout().write_all(&wire::pretty(&serde_json::json!({"key":identity.key(),"canonical":String::from_utf8(identity.bytes().to_vec()).map_err(error)?}))?).map_err(error)?;
			Ok(())
		}
		Some("audit") if args.len() == 6 => {
			let metadata = input::read(Path::new(&args[4]), input::DOCUMENT_LIMIT)?;
			let inv = inventory::native(
				&metadata,
				stage,
				&root,
				Path::new(&args[5]),
				&mut fingerprint::Allowance::default(),
			)?;
			policy(&inv)?;
			println!("{}", String::from_utf8(wire::pretty(&inv)?).map_err(error)?);
			Ok(())
		}
		Some("guard") if args.len() == 4 => Ok(()),
		_ => Err("invalid prototype arguments".into()),
	}
}

fn entry_run(args: &[std::ffi::OsString]) -> Result<(), String> {
	use std::io::Write;
	commands::install_signals()?;
	let identity = cache_identity::Identity::decode(&input::read(
		Path::new(&args[1]),
		input::DOCUMENT_LIMIT,
	)?)?;
	if args[0] == "ready-check" {
		let (path, digest) = cache_entry::ready(&identity)?;
		artifact::check(&path, &digest, None, true)?;
		return Ok(());
	}
	let project = Path::new(&args[3]);
	let guard = fs::OpenOptions::new()
		.read(true)
		.write(true)
		.create(true)
		.truncate(false)
		.open(project.join("fixture-project.lock"))
		.map_err(error)?;
	guard.try_lock().map_err(error)?;
	let read_project = || -> Result<Vec<Vec<u8>>, String> {
		["rnx.toml", "main.rn", "fixture-locked"]
			.iter()
			.map(|n| input::read(&project.join(n), input::DOCUMENT_LIMIT))
			.collect()
	};
	let before = read_project()?;
	let receipt = project.join("fixture-receipt.json");
	if receipt.exists() {
		fs::remove_file(&receipt).map_err(error)?;
	}
	let lock = input::read(Path::new(&args[2]), input::DOCUMENT_LIMIT)?;
	let entry = cache_entry::acquire(&identity, &lock, project, true, || {
		if read_project()? != before {
			Err("project sources/lock changed".into())
		} else {
			Ok(())
		}
	})?;
	if std::env::var_os("RNX_FIXTURE_ATTACH_FAIL").is_some() {
		return Err("injected attachment publication failure".into());
	}
	let bytes = wire::pretty(
		&serde_json::json!({"key":identity.key(),"path":entry.artifact.path(),"digest":entry.digest,"hit":entry.hit}),
	)?;
	let temp = project.join("fixture-receipt.new");
	let mut f = fs::File::create(&temp).map_err(error)?;
	f.write_all(&bytes).map_err(error)?;
	f.sync_all().map_err(error)?;
	drop(f);
	commands::check()?;
	fs::rename(&temp, &receipt).map_err(error)?;
	fs::File::open(project)
		.and_then(|f| f.sync_all())
		.map_err(error)?;
	println!("{}", String::from_utf8(bytes).map_err(error)?);
	Ok(())
}
fn main() {
	let args: Vec<_> = std::env::args_os().skip(1).collect();
	let result = if args
		.first()
		.is_some_and(|a| a == "entry" || a == "ready-check")
	{
		entry_run(&args)
	} else {
		run()
	};
	if let Err(e) = result {
		eprintln!("{e}");
		std::process::exit(if commands::interrupted() {
			commands::signal_status()
		} else {
			1
		});
	}
}
