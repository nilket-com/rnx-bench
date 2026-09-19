//! Gate-1 wire candidates. Not selected by production commands.
use crate::{artifact, cache_identity, input, manifest, new_identity, wire};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, path::Path};
fn digest(s: &str) -> bool {
	s.len() == 64
		&& s.bytes()
			.all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
pub(crate) fn git_coordinate(url: &str, rev: &str) -> Result<(), String> {
	if !(url.starts_with("https://") || url.starts_with("file:///"))
		|| url.len() > 4096
		|| url.contains(['\0', '\n', '\r', '?', '#'])
		|| url.split("://").nth(1).is_none_or(str::is_empty)
	{
		return Err("unsupported Git URL".into());
	}
	if rev.len() != 40
		|| !rev
			.bytes()
			.all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
	{
		return Err("full lowercase 40-hex Git revision required".into());
	}
	Ok(())
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Location {
	#[serde(default, skip_serializing_if = "Option::is_none")]
	pub path: Option<String>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	pub git: Option<String>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	pub rev: Option<String>,
}
impl Location {
	fn validate(&self) -> Result<(), String> {
		match (&self.path, &self.git, &self.rev) {
			(Some(p), None, None) => input::path(p),
			(None, Some(g), Some(r)) => git_coordinate(g, r),
			_ => Err("exactly path or git plus rev required".into()),
		}
	}
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Native {
	#[serde(default, skip_serializing_if = "Option::is_none")]
	path: Option<String>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	git: Option<String>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	rev: Option<String>,
	package: String,
	builder: String,
	hook: manifest::Hook,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Declaration {
	format: u32,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	application: Option<manifest::Application>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	source: Option<manifest::Source>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	runtime: Option<Location>,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	executable: Option<manifest::Location>,
	#[serde(default, deserialize_with = "unique_map")]
	sources: BTreeMap<String, manifest::Location>,
	#[serde(default, deserialize_with = "unique_map")]
	native: BTreeMap<String, Native>,
}
impl Declaration {
	fn validate(&self) -> Result<(), String> {
		if self.format != 2 {
			return Err("expected declaration format 2".into());
		}
		// Reuse the existing semantic/limit validator after replacing only native
		// locations with inert paths; this projection is never persisted or hashed.
		if let Some(r) = &self.runtime {
			r.validate()?;
		}
		for n in self.native.values() {
			Location {
				path: n.path.clone(),
				git: n.git.clone(),
				rev: n.rev.clone(),
			}
			.validate()?;
		}
		let mut v = serde_json::to_value(self).map_err(|e| e.to_string())?;
		v["format"] = 1.into();
		if let Some(r) = &self.runtime {
			v["runtime"] = serde_json::json!({"path":r.path.as_deref().unwrap_or("/probe/git")});
		}
		for (name, n) in &self.native {
			v["native"][name] = serde_json::json!({"path":n.path.as_deref().unwrap_or("/probe/git"),"package":n.package,"builder":n.builder,"hook":n.hook});
		}
		let old: manifest::Manifest = serde_json::from_value(v).map_err(|e| e.to_string())?;
		old.validate()
	}
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct GitPackage {
	pub id: String,
	pub name: String,
	pub url: String,
	pub revision: String,
	pub checkout: String,
	pub manifest: String,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Lock {
	format: u32,
	declarations: Declaration,
	sources: wire::Handoff,
	inputs: wire::Inputs,
	git: Vec<GitPackage>,
	assembly: Assembly,
}
#[derive(Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
enum Assembly {
	Shared { identity: String },
	Executable { path: String, blake3: String },
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Receipt {
	format: u32,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	assembly_key: Option<String>,
	lock_blake3: String,
	executable_blake3: String,
	#[serde(default, skip_serializing_if = "Option::is_none")]
	stamp: Option<artifact::Stamp>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Ready {
	format: u32,
	key: String,
	identity: String,
	executable_blake3: String,
	artifact: String,
}
fn envelope(b: &[u8]) -> Result<u64, String> {
	if b.len() > input::DOCUMENT_LIMIT {
		return Err("document allowance".into());
	}
	let v: serde_json::Value = serde_json::from_slice(b).map_err(|e| e.to_string())?;
	v.get("format")
		.and_then(|v| v.as_u64())
		.ok_or("missing format".into())
}
fn parsed<T: serde::de::DeserializeOwned>(b: &[u8]) -> Result<T, String> {
	if b.len() > input::DOCUMENT_LIMIT {
		return Err("document allowance".into());
	}
	serde_json::from_slice(b).map_err(|e| e.to_string())
}
pub(crate) fn validate(kind: &str, b: &[u8]) -> Result<Vec<u8>, String> {
	match kind {
		"declaration" => {
			if b.len() > input::MANIFEST_LIMIT {
				return Err("manifest allowance".into());
			}
			let text = std::str::from_utf8(b).map_err(|e| e.to_string())?;
			let v: toml::Value = toml::from_str(text).map_err(|e| e.to_string())?;
			if v.get("format").and_then(|v| v.as_integer()) == Some(1) {
				let d: manifest::Manifest = toml::from_str(text).map_err(|e| e.to_string())?;
				d.validate()?;
				wire::encode(&d)
			} else {
				let d: Declaration = toml::from_str(text).map_err(|e| e.to_string())?;
				d.validate()?;
				wire::encode(&d)
			}
		}
		"identity" => match envelope(b)? {
			2 => {
				let d = cache_identity::Identity::decode(b)?;
				Ok(d.bytes().to_vec())
			}
			3 => {
				let d = new_identity::Identity::decode(b)?;
				Ok(d.bytes().to_vec())
			}
			_ => Err("unsupported identity format".into()),
		},
		"canonical-identity" => new_identity::canonical(b),
		"lock" => {
			if envelope(b)? == 3 {
				return wire::encode(&wire::Lock::decode(b)?);
			}
			let d: Lock = parsed(b)?;
			if d.format != 4 {
				return Err("expected lock format 4".into());
			}
			d.declarations.validate()?;
			d.sources.validate()?;
			if d.declarations.application.is_none() {
				return Err("lock needs application".into());
			}
			// Existing source/path inventory bounds remain enforced by the old lock
			// validator on a shape-only executable projection. Git binding is checked below.
			let mut shape = serde_json::to_value(&d).map_err(|e| e.to_string())?;
			shape.as_object_mut().unwrap().remove("git");
			shape["format"] = 3.into();
			shape["declarations"] = serde_json::json!({"format":1,"application":{"entry":"main.rn"},"executable":{"path":"/probe/executable"},"sources":{},"native":{}});
			shape["assembly"] = serde_json::json!({"kind":"executable","path":"/probe/executable","blake3":"0".repeat(64)});
			let old: wire::Lock = serde_json::from_value(shape).map_err(|e| e.to_string())?;
			old.validate()?;
			match &d.assembly {
				Assembly::Shared { identity } => {
					let i = new_identity::Identity::decode(identity.as_bytes())?;
					if d.declarations.runtime.is_none()
						|| d.inputs.native.as_ref() != Some(i.native())
						|| d.git != i.git()
					{
						return Err("identity/input binding mismatch".into());
					}
					bind(&d.declarations, i.wrapper().0)?;
				}
				Assembly::Executable { path, blake3 } => {
					if d.declarations.executable.is_none()
						|| !d.git.is_empty()
						|| !Path::new(path).is_absolute()
						|| !digest(blake3)
					{
						return Err("invalid override lock".into());
					}
				}
			}
			wire::encode(&d)
		}
		"receipt" => {
			if envelope(b)? == 4 {
				let _: artifact::Receipt = artifact::Receipt::decode(b)?;
				return Ok(b.to_vec());
			}
			let d: Receipt = parsed(b)?;
			if d.format != 5 {
				return Err("expected receipt 5".into());
			}
			let mut v = serde_json::to_value(&d).map_err(|e| e.to_string())?;
			v["format"] = 4.into();
			artifact::Receipt::decode(&wire::encode(&v)?)?;
			wire::encode(&d)
		}
		"ready" => {
			if envelope(b)? == 2 {
				return crate::cache_entry::probe_ready(b);
			}
			let d: Ready = parsed(b)?;
			if d.format != 3 {
				return Err("expected ready 3".into());
			}
			let i = new_identity::Identity::decode(d.identity.as_bytes())?;
			if d.key != i.key()
				|| !digest(&d.executable_blake3)
				|| d.artifact != format!("artifacts/{}", d.executable_blake3)
			{
				return Err("invalid ready binding".into());
			}
			wire::encode(&d)
		}
		_ => Err("unknown schema probe operation".into()),
	}
}
fn bind(d: &Declaration, wrapper: &str) -> Result<(), String> {
	let doc: toml::Value = toml::from_str(wrapper).map_err(|e| e.to_string())?;
	let deps = doc
		.get("dependencies")
		.and_then(|v| v.as_table())
		.ok_or("missing dependencies")?;
	let Some(runtime) = &d.runtime else {
		return Err("missing runtime".into());
	};
	let check = |l: &Location, dep: &toml::Value| -> Result<(), String> {
		match (&l.path, &l.git, &l.rev) {
			(Some(p), None, None) => {
				if Path::new(p).is_absolute() && dep.get("path").and_then(|v| v.as_str()) != Some(p)
				{
					return Err("path binding".into());
				}
			}
			(None, Some(g), Some(r)) => {
				if dep.get("git").and_then(|v| v.as_str()) != Some(g)
					|| dep.get("rev").and_then(|v| v.as_str()) != Some(r)
				{
					return Err("Git binding".into());
				}
			}
			_ => return Err("location binding".into()),
		}
		Ok(())
	};
	check(
		runtime,
		deps.get("rnx").ok_or("missing runtime dependency")?,
	)?;
	if deps.len() != d.native.len() + 1 {
		return Err("native dependency count".into());
	}
	for (n, (_, native)) in d.native.iter().enumerate() {
		let dep = deps
			.get(&format!("native_{n}"))
			.ok_or("missing native alias")?;
		if dep.get("package").and_then(|v| v.as_str()) != Some(&native.package) {
			return Err("native package binding".into());
		}
		check(
			&Location {
				path: native.path.clone(),
				git: native.git.clone(),
				rev: native.rev.clone(),
			},
			dep,
		)?;
	}
	Ok(())
}

fn unique_map<'de, D, T>(de: D) -> Result<BTreeMap<String, T>, D::Error>
where
	D: serde::Deserializer<'de>,
	T: Deserialize<'de>,
{
	struct Map<T>(std::marker::PhantomData<T>);
	impl<'de, T: Deserialize<'de>> serde::de::Visitor<'de> for Map<T> {
		type Value = BTreeMap<String, T>;
		fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
			f.write_str("up to 256 distinct declarations")
		}
		fn visit_map<A: serde::de::MapAccess<'de>>(
			self,
			mut map: A,
		) -> Result<Self::Value, A::Error> {
			let mut out = BTreeMap::new();
			while let Some(key) = map.next_key::<String>()? {
				if out.len() == 256 || out.contains_key(&key) {
					return Err(serde::de::Error::custom(
						"too many or duplicate declarations",
					));
				}
				out.insert(key, map.next_value()?);
			}
			Ok(out)
		}
	}
	de.deserialize_map(Map::<T>(std::marker::PhantomData))
}
