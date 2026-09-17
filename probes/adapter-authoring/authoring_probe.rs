//! Gate 1 only: author candidate bytes on stdout; never publish a manifest.
#![allow(dead_code)]
mod cache_identity;
mod cache_storage;
mod fingerprint;
mod generate;
mod graph;
mod input;
mod inventory;
mod manifest;
mod wire;
use manifest::{Hook, Manifest, Native};
use std::{
	collections::BTreeMap,
	path::{Path, PathBuf},
};
fn error(e: impl std::fmt::Display) -> String {
	e.to_string()
}
fn canonical(path: &Path) -> Result<PathBuf, String> {
	path.canonicalize()
		.map_err(|e| format!("{}: {e}", path.display()))
}
fn cargo(root: &Path, expected: &str) -> Result<toml::Value, String> {
	let path = root.join("Cargo.toml");
	let bytes = input::read(&path, input::MANIFEST_LIMIT)?;
	let value: toml::Value =
		toml::from_str(std::str::from_utf8(&bytes).map_err(error)?).map_err(error)?;
	if value
		.get("package")
		.and_then(|p| p.get("name"))
		.and_then(|p| p.as_str())
		!= Some(expected)
	{
		return Err(format!(
			"{}: expected explicit package.name {expected}",
			path.display()
		));
	}
	Ok(value)
}
fn run() -> Result<(), String> {
	let args: Vec<_> = std::env::args().skip(1).collect();
	if args.len() < 2 || args.len() > 33 {
		return Err("MANIFEST NAME [NAME...] (1 to 32 distinct names)".into());
	}
	let path = canonical(Path::new(&args[0]))?;
	let base = path.parent().ok_or("manifest has no parent")?;
	let raw = input::read(&path, input::MANIFEST_LIMIT)?;
	let original = Manifest::parse(&raw)?;
	let runtime = original
		.runtime
		.as_ref()
		.ok_or("add requires an application with a runtime path")?;
	let root = canonical(&base.join(&runtime.path))?;
	cargo(&root, "rnx")?;
	let mut requested = BTreeMap::new();
	for name in &args[1..] {
		let (package, hook) = match name.as_str() {
			"polars" => ("rnx-polars", Hook::Plain),
			"postgres" => ("rnx-postgres", Hook::Lifecycle),
			_ => {
				return Err(format!(
					"unknown adapter {name}; available: polars, postgres"
				));
			}
		};
		if requested.insert(name.clone(), (package, hook)).is_some() {
			return Err(format!("duplicate adapter {name}"));
		}
	}
	let mut additions = BTreeMap::new();
	let mut existing = Vec::new();
	for (name, (package, hook)) in requested {
		let suffix = Path::new("adapters").join(&name);
		let adapter = canonical(&root.join(&suffix))?;
		let value = cargo(&adapter, package)?;
		let dep = value
			.get("dependencies")
			.and_then(|v| v.get("rnx"))
			.ok_or_else(|| format!("{name}: missing dependencies.rnx"))?;
		if dep.get("workspace").is_some()
			|| dep
				.get("package")
				.is_some_and(|v| v.as_str() != Some("rnx"))
		{
			return Err(format!("{name}: requires direct rnx path dependency"));
		}
		let dep = dep
			.get("path")
			.and_then(|v| v.as_str())
			.ok_or_else(|| format!("{name}: requires direct rnx path dependency"))?;
		if canonical(&adapter.join(dep))? != root {
			return Err(format!("{name}: adapter depends on a different runtime"));
		}
		let written = Path::new(&runtime.path).join(suffix);
		if canonical(&base.join(&written))? != adapter {
			return Err(format!(
				"{name}: written path does not reach validated adapter"
			));
		}
		let native = Native {
			path: written.to_str().ok_or("non-Unicode adapter path")?.into(),
			package: package.into(),
			builder: "build".into(),
			hook,
		};
		if let Some(old) = original.native.get(&name) {
			if canonical(&base.join(&old.path))? != adapter
				|| old.package != native.package
				|| old.builder != native.builder
				|| old.hook != native.hook
			{
				return Err(format!(
					"native namespace {name} already has a different declaration"
				));
			}
			existing.push(name);
		} else {
			additions.insert(name, native);
		}
	}
	#[derive(serde::Serialize)]
	struct Tables<'a> {
		native: &'a BTreeMap<String, Native>,
	}
	let mut candidate = String::from_utf8(raw).map_err(error)?;
	if !additions.is_empty() {
		let append = toml::to_string(&Tables { native: &additions }).map_err(error)?;
		if candidate.len() + 2 + append.len() > input::MANIFEST_LIMIT {
			return Err("candidate manifest exceeds 1048576 bytes".into());
		}
		candidate.push_str("\n\n");
		candidate.push_str(&append);
	}
	let parsed = Manifest::parse(candidate.as_bytes())
		.map_err(|e| format!("cannot append native tables; use explicit table layout: {e}"))?;
	let mut expected = original;
	expected.native.extend(additions.clone());
	if parsed != expected {
		return Err("append changed unrelated manifest meaning".into());
	}
	let wrapper = generate::wrapper(&parsed, base)?;
	let canonical_wrapper = generate::canonical_wrapper(&parsed, base)?;
	println!(
		"{}",
		serde_json::json!({"candidate":candidate,"manifest":parsed,"added":additions.keys().collect::<Vec<_>>(),"existing":existing,"wrapper":wrapper,"canonical_wrapper":canonical_wrapper})
	);
	Ok(())
}
fn main() {
	if let Err(e) = run() {
		eprintln!("authoring probe: {e}");
		std::process::exit(1);
	}
}
