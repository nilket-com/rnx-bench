#![allow(dead_code)]
mod artifact;
mod assembly;
mod cache_entry;
mod cache_identity;
mod cache_storage;
mod catalogue;
mod commands;
mod fingerprint;
mod generate;
mod graph;
mod handshake;
mod input;
mod inventory;
mod manifest;
mod maps;
#[path = "dep_wire.rs"]
mod protocol;
mod wire;
mod workflow;
use protocol::Fields;
use sha2::{Digest, Sha256};
use std::{
	fs,
	io::Write,
	os::{
		fd::{AsRawFd, FromRawFd},
		unix::{
			fs::{DirBuilderExt, OpenOptionsExt},
			net::UnixStream,
		},
	},
	path::{Path, PathBuf},
};
fn sha(b: impl AsRef<[u8]>) -> String {
	format!("{:x}", Sha256::digest(b))
}
fn regular(p: &Path) -> Result<Vec<u8>, String> {
	input::read(p, input::MANIFEST_LIMIT)
}
fn manifest(p: &Path) -> Result<manifest::Manifest, String> {
	manifest::Manifest::parse(&regular(p)?)
}
fn declaration(m: &manifest::Manifest) -> Result<String, String> {
	Ok(sha(
		serde_json::to_vec(&(&m.runtime, &m.native)).map_err(|e| e.to_string())?
	))
}
fn association(p: &Path, exe: &Path) -> Result<String, String> {
	let m = manifest(p)?;
	let base = p.parent().unwrap();
	let f = Fields::from([
		(
			1,
			p.canonicalize()
				.map_err(|e| e.to_string())?
				.to_string_lossy()
				.into_owned(),
		),
		(
			2,
			std::env::current_exe()
				.map_err(|e| e.to_string())?
				.to_string_lossy()
				.into_owned(),
		),
		(3, declaration(&m)?),
		(4, sha(regular(&base.join(".rnx/receipt.json"))?)),
		(5, assembly::executable_hash(exe)?),
		(6, sha(regular(&base.join("rnx.lock"))?)),
	]);
	Ok(protocol::hex(&protocol::encode(7, &f)?))
}
fn prospective(p: &Path) -> Result<PathBuf, String> {
	if !p.is_absolute()
		|| p.components()
			.any(|c| matches!(c, std::path::Component::ParentDir))
	{
		return Err("state path must be absolute without parent components".into());
	}
	let mut ancestor = p;
	let mut tail = Vec::new();
	while !ancestor.try_exists().map_err(|e| e.to_string())? {
		tail.push(ancestor.file_name().ok_or("state root")?.to_owned());
		ancestor = ancestor.parent().ok_or("state parent")?;
	}
	let mut out = ancestor.canonicalize().map_err(|e| e.to_string())?;
	for t in tail.into_iter().rev() {
		out.push(t);
	}
	Ok(out)
}
fn directory(p: &Path) -> Result<(), String> {
	match fs::symlink_metadata(p) {
		Ok(m) if m.is_dir() => Ok(()),
		Ok(_) => Err("managed path not directory".into()),
		Err(e) if e.kind() == std::io::ErrorKind::NotFound => fs::DirBuilder::new()
			.mode(0o700)
			.create(p)
			.map_err(|e| e.to_string()),
		Err(e) => Err(e.to_string()),
	}
}
fn describe(f: &Fields) -> Result<Fields, String> {
	protocol::exact(f, &[1, 2, 3, 4, 5])?;
	if !["online", "offline"].contains(&f[&5].as_str()) {
		return Err("bad offline mode".into());
	}
	let names = f[&1].lines().map(String::from).collect::<Vec<_>>();
	let entries = catalogue::select(&names)?;
	let (path, token, action, candidate) = if !f[&2].is_empty() {
		let a = protocol::capsule(&f[&2])?;
		let p = PathBuf::from(&a[&1]);
		let m = manifest(&p)?;
		if std::env::current_exe()
			.map_err(|e| e.to_string())?
			.to_string_lossy()
			!= a[&2]
		{
			return Err("association names another tool".into());
		}
		if m.native.keys().cloned().collect::<Vec<_>>().join("\n") != f[&4]
			|| declaration(&m)? != a[&3]
			|| sha(regular(&p.parent().unwrap().join(".rnx/receipt.json"))?) != a[&4]
			|| sha(regular(&p.parent().unwrap().join("rnx.lock"))?) != a[&6]
			|| assembly::executable_hash(Path::new(&f[&3]))? != a[&5]
		{
			return Err("stale session association; reopen the project session".into());
		}
		let candidate = catalogue::author(regular(&p)?, p.parent().unwrap(), &entries)?;
		(p.clone(), sha(regular(&p)?), "project", candidate)
	} else {
		if !f[&4].is_empty() {
			return Err("custom executable needs association".into());
		}
		let runtime = std::env::var("RNX_DEP_RUNTIME")
			.map_err(|_| "set export RNX_DEP_RUNTIME=/absolute/path/to/rnx")?;
		let runtime = PathBuf::from(runtime);
		if !runtime.is_absolute() {
			return Err("runtime must be absolute".into());
		}
		let root = prospective(Path::new(
			&std::env::var("XDG_STATE_HOME").map_err(|_| "prototype needs XDG_STATE_HOME")?,
		))?;
		let native_root = runtime.canonicalize().map_err(|e| e.to_string())?;
		if root.starts_with(&native_root) || native_root.starts_with(&root) {
			return Err("scratch and native roots contain one another".into());
		}
		let p = root.join("rnx/sessions/gate1-session/rnx.toml");
		let text = format!(
			"format=1\n[application]\nentry=\"main.rn\"\n[runtime]\npath={}\n",
			serde_json::to_string(&runtime).unwrap()
		);
		let candidate = catalogue::author(text.into_bytes(), p.parent().unwrap(), &entries)?;
		(
			p,
			sha(runtime.to_string_lossy().as_bytes()),
			"scratch",
			candidate,
		)
	};
	let cost = if candidate.added.iter().any(|n| n == "polars") {
		"Polars precedent: about 100 seconds with cached registry sources, about 1.5 GB retained; a hit skips compilation."
	} else {
		"Build/attach cost depends on the requested adapters and cache contents."
	};
	Ok(Fields::from([
		(1, sha(format!("{}:{token}:{:?}", path.display(), f))),
		(
			2,
			format!(
				"{action}: {}\nAdditions: {}\nAlready declared: {}\nCargo mode: {}\n{cost}",
				path.display(),
				candidate.added.join(", "),
				candidate.existing.join(", "),
				f[&5]
			),
		),
		(3, path.to_string_lossy().into_owned()),
		(4, action.into()),
		(5, candidate.added.join("\n")),
		(6, candidate.existing.join("\n")),
		(7, f[&5].clone()),
	]))
}
fn serve(s: &mut UnixStream) -> Result<(), String> {
	let (k, request) = protocol::read(s)?;
	if k != 1 {
		return Err("expected describe".into());
	}
	let description = describe(&request)?;
	protocol::write(s, 2, &description)?;
	let (k, approval) = protocol::read(s)?;
	if k == 3 {
		protocol::exact(&approval, &[])?;
		return Ok(());
	}
	if k != 4 {
		return Err("expected prepare".into());
	}
	protocol::exact(&approval, &[1])?;
	let now = describe(&request)?;
	if now != description || approval[&1] != description[&1] {
		return Err("description changed; redescribe and consent".into());
	}
	if description[&4] == "scratch" {
		let manifest = PathBuf::from(&description[&3]);
		let session = manifest.parent().unwrap();
		let sessions = session.parent().unwrap();
		let rnx = sessions.parent().unwrap();
		let root = rnx.parent().unwrap();
		directory(root)?;
		directory(rnx)?;
		directory(sessions)?;
		fs::DirBuilder::new()
			.mode(0o700)
			.create(session)
			.map_err(|e| format!("scratch reservation lost: {e}"))?;
		let mut f = fs::OpenOptions::new()
			.write(true)
			.create_new(true)
			.mode(0o600)
			.custom_flags(libc::O_NOFOLLOW)
			.open(manifest)
			.map_err(|e| e.to_string())?;
		f.write_all(b"# gate 1 scratch allocation only; not a product build\n")
			.map_err(|e| e.to_string())?;
	}
	// Child observation of seal-on-receive: the descriptor is not usable.
	let fd = s.as_raw_fd();
	let child = std::process::Command::new("/usr/bin/python3")
		.arg("-c")
		.arg(format!(
			"import os;\ntry: os.fstat({fd})\nexcept OSError: raise SystemExit(0)\nraise SystemExit(1)"
		))
		.status()
		.map_err(|e| e.to_string())?;
	if !child.success() {
		return Err("control descriptor leaked".into());
	}
	protocol::write(
		s,
		5,
		&Fields::from([(
			1,
			std::env::var("RNX_PROBE_REPLACEMENT").map_err(|_| "fixture replacement missing")?,
		)]),
	)
}
fn main() {
	let result = (|| -> Result<(), String> {
		let args = std::env::args().collect::<Vec<_>>();
		if args.get(1).is_some_and(|s| s == "associate") {
			println!("{}", association(Path::new(&args[2]), Path::new(&args[3]))?);
			return Ok(());
		}
		let fd = std::env::var("RNX_INTERNAL_DEP_FD")
			.map_err(|_| "private inherited socket missing")?
			.parse::<i32>()
			.map_err(|_| "bad fd")?;
		if fd < 3 {
			return Err("invalid control fd".into());
		}
		if unsafe { libc::fcntl(fd, libc::F_SETFD, libc::FD_CLOEXEC) } < 0 {
			return Err("cannot seal fd".into());
		}
		let mut s = unsafe { UnixStream::from_raw_fd(fd) };
		s.set_read_timeout(Some(std::time::Duration::from_secs(5)))
			.map_err(|e| e.to_string())?;
		if let Err(e) = serve(&mut s) {
			protocol::write(&mut s, 8, &Fields::from([(1, e)]))?;
		}
		Ok(())
	})();
	if let Err(e) = result {
		eprintln!("{e}");
		std::process::exit(1);
	}
}
