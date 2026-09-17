//! Isolated gate-1 bridge only. No product preparation or startup probe yet.
use super::dep_wire as wire;
use std::{
	cell::RefCell,
	io::{Read, Write},
	os::{
		fd::AsRawFd,
		unix::{net::UnixStream, process::CommandExt},
	},
	process::{Command, Stdio},
	time::Duration,
};
thread_local! {static INSTALLED:RefCell<Vec<String>>=const{RefCell::new(Vec::new())};static NEXT:RefCell<Option<String>>=const{RefCell::new(None)};}
pub fn installed(names: Vec<String>) {
	INSTALLED.with(|v| *v.borrow_mut() = names);
}
fn event(s: &str) {
	if let Ok(p) = std::env::var("RNX_PROBE_EVENTS") {
		use std::fs::OpenOptions;
		if let Ok(mut f) = OpenOptions::new().append(true).create(true).open(p) {
			let _ = writeln!(f, "{s}");
		}
	}
}
pub fn describe_and_prepare(input: &str) -> Result<bool, String> {
	let association = std::env::var("RNX_INTERNAL_SESSION_V1").unwrap_or_default();
	let names_installed = INSTALLED.with(|v| v.borrow().join("\n"));
	if association.is_empty() && !names_installed.is_empty() {
		return Err("custom executable needs a project association".into());
	}
	let tool = if !association.is_empty() {
		wire::capsule(&association)?[&2].clone()
	} else if let Ok(path) = std::env::var("RNX_PROJECT_TOOL") {
		path
	} else {
		std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default())
			.map(|p| p.join("rnx-project"))
			.find(|p| p.is_file())
			.and_then(|p| p.canonicalize().ok())
			.and_then(|p| p.into_os_string().into_string().ok())
			.ok_or("cannot locate rnx-project")?
	};
	if !std::path::Path::new(&tool).is_absolute() {
		return Err("tool must be absolute".into());
	}
	let mut offline = false;
	let mut names = Vec::new();
	for word in input.split_whitespace().skip(1) {
		if word == "--offline" && !offline {
			offline = true;
		} else if word.starts_with('-') {
			return Err("unknown or duplicate option".into());
		} else {
			names.push(word);
		}
	}
	let names = names.join("\n");
	let (mut parent, child) = UnixStream::pair().map_err(|e| e.to_string())?;
	parent
		.set_read_timeout(Some(Duration::from_secs(5)))
		.map_err(|e| e.to_string())?;
	parent
		.set_write_timeout(Some(Duration::from_secs(5)))
		.map_err(|e| e.to_string())?;
	let fd = child.as_raw_fd();
	let mut cmd = Command::new(tool);
	cmd.env("RNX_INTERNAL_DEP_FD", fd.to_string())
		.stdin(Stdio::null())
		.stdout(Stdio::null())
		.stderr(Stdio::inherit());
	unsafe {
		cmd.pre_exec(move || {
			if libc::fcntl(fd, libc::F_SETFD, 0) < 0 {
				return Err(std::io::Error::last_os_error());
			}
			Ok(())
		});
	}
	let mut helper = cmd.spawn().map_err(|e| e.to_string())?;
	drop(child);
	let attempt = (|| {
		let f = wire::Fields::from([
			(1, names),
			(4, names_installed),
			(5, if offline { "offline" } else { "online" }.into()),
			(2, association),
			(
				3,
				std::env::current_exe()
					.map_err(|e| e.to_string())?
					.to_string_lossy()
					.into_owned(),
			),
		]);
		wire::write(&mut parent, 1, &f)?;
		let (k, description) = wire::read(&mut parent)?;
		if k == 8 {
			return Err(description.get(&1).cloned().unwrap_or_default());
		}
		if k != 2 {
			return Err("not a description".into());
		}
		wire::exact(&description, &[1, 2, 3, 4, 5, 6, 7])?;
		println!("{}", description[&2]);
		if description[&5].is_empty() {
			wire::write(&mut parent, 3, &wire::Fields::new())?;
			println!("already installed; session unchanged");
			return Ok(false);
		}
		println!(
			"Bindings will be lost. Saved history remains available with up-arrow; nothing is replayed. Continue? [y/N]"
		);
		std::io::stdout().flush().map_err(|e| e.to_string())?;
		// Prototype consent is supplied by the driver, so this gate does not
		// pretend to exercise rustyline's terminal consent/cancellation yet.
		if std::env::var("RNX_PROBE_CONSENT").as_deref() != Ok("yes") {
			wire::write(&mut parent, 3, &wire::Fields::new())?;
			return Ok(false);
		}
		// Deterministic fixture hook between describe and prepare.
		if let Ok(p) = std::env::var("RNX_PROBE_EDIT") {
			std::fs::write(p, "changed").map_err(|e| e.to_string())?;
		}
		wire::write(
			&mut parent,
			4,
			&wire::Fields::from([(1, description[&1].clone())]),
		)?;
		let (k, result) = wire::read(&mut parent)?;
		if k == 8 {
			return Err(result.get(&1).cloned().unwrap_or_default());
		}
		if k != 5 {
			return Err("not prepared".into());
		}
		wire::exact(&result, &[1])?;
		let mut tail = [0];
		if parent.read(&mut tail).map_err(|e| e.to_string())? != 0 {
			return Err("trailing readiness data".into());
		}
		let path = result[&1].clone();
		if !std::path::Path::new(&path).is_absolute() {
			return Err("replacement not absolute".into());
		}
		NEXT.with(|v| *v.borrow_mut() = Some(path));
		Ok(true)
	})();
	drop(parent);
	if attempt.is_err() {
		let _ = helper.kill();
	}
	let status = helper.wait().map_err(|e| e.to_string())?;
	if !status.success() {
		NEXT.with(|v| v.borrow_mut().take());
		return Err(attempt.err().unwrap_or_else(|| "helper failed".into()));
	}
	attempt
}
pub fn finish(result: crate::Result<()>) -> crate::Result<()> {
	// main_inner has returned: Session, editor, context and lifecycle dropped.
	event("entry stack returned");
	let next = NEXT.with(|v| v.borrow_mut().take());
	result?;
	if let Some(path) = next {
		event("before exec");
		let mut cmd = Command::new(path);
		cmd.env_remove("RNX_INTERNAL_DEP_FD")
			.env_remove("RNX_INTERNAL_SESSION_V1");
		let err = cmd.exec();
		return Err(format!("dependency restart exec failed after cleanup: {err}").into());
	}
	Ok(())
}
