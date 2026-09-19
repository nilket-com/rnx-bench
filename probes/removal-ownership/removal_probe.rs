//! Isolated 0066 gate-one candidate. Not a product command or public API.
#[allow(dead_code)]
mod commands;
mod input;
use serde_json::{Value, json};
use std::{
	collections::HashSet,
	ffi::{CStr, CString, OsStr, OsString},
	fs::{File, OpenOptions},
	io::{Read, Write},
	os::{
		fd::{AsRawFd, FromRawFd},
		unix::{
			ffi::{OsStrExt, OsStringExt},
			fs::{MetadataExt, OpenOptionsExt},
		},
	},
	path::{Path, PathBuf},
	time::Duration,
};
type Result<T> = std::result::Result<T, String>;
fn error(e: impl std::fmt::Display) -> String {
	e.to_string()
}
fn io_error(label: &str) -> String {
	format!("{label}: {}", std::io::Error::last_os_error())
}
fn name(s: &OsStr) -> Result<CString> {
	CString::new(s.as_bytes()).map_err(error)
}
#[repr(C)]
struct How {
	flags: u64,
	mode: u64,
	resolve: u64,
}
const RESOLVE: u64 = 0x08 | 0x04 | 0x01; // BENEATH | NO_SYMLINKS | NO_XDEV
fn open(dir: &File, n: &OsStr, flags: i32, mode: u32) -> Result<File> {
	let n = name(n)?;
	let how = How {
		flags: (flags
			| libc::O_CLOEXEC
			| libc::O_NOFOLLOW
			| if flags & libc::O_PATH == 0 {
				libc::O_NONBLOCK
			} else {
				0
			}) as u64,
		mode: mode as u64,
		resolve: RESOLVE,
	};
	let injected = std::env::var("RNX_REMOVE_OPEN_ERRNO")
		.ok()
		.and_then(|v| v.parse::<i32>().ok());
	let fd = if injected.is_some() {
		-1
	} else {
		unsafe {
			libc::syscall(
				libc::SYS_openat2,
				dir.as_raw_fd(),
				n.as_ptr(),
				&how,
				std::mem::size_of::<How>(),
			) as i32
		}
	};
	if fd < 0 {
		let e = injected
			.map(std::io::Error::from_raw_os_error)
			.unwrap_or_else(std::io::Error::last_os_error);
		return Err(format!(
			"openat2 {:?}: {e}; guarded open refused, no fallback",
			n
		));
	}
	Ok(unsafe { File::from_raw_fd(fd) })
}
fn directory(d: &File, n: &OsStr) -> Result<File> {
	open(d, n, libc::O_RDONLY | libc::O_DIRECTORY, 0)
}
fn stat(d: &File, n: &OsStr) -> Result<Option<libc::stat>> {
	let n = name(n)?;
	let mut s = std::mem::MaybeUninit::<libc::stat>::uninit();
	if unsafe {
		libc::fstatat(
			d.as_raw_fd(),
			n.as_ptr(),
			s.as_mut_ptr(),
			libc::AT_SYMLINK_NOFOLLOW,
		)
	} != 0
	{
		let e = std::io::Error::last_os_error();
		if e.kind() == std::io::ErrorKind::NotFound {
			return Ok(None);
		}
		return Err(error(e));
	}
	Ok(Some(unsafe { s.assume_init() }))
}
fn private(f: &File, dir: bool) -> Result<()> {
	let m = f.metadata().map_err(error)?;
	if m.uid() != unsafe { libc::geteuid() }
		|| m.mode() & 0o022 != 0
		|| (if dir { !m.is_dir() } else { !m.is_file() })
	{
		return Err("not a private owned control object".into());
	}
	Ok(())
}
fn same(f: &File, s: &libc::stat) -> Result<()> {
	let m = f.metadata().map_err(error)?;
	if m.dev() != s.st_dev || m.ino() != s.st_ino {
		return Err("directory identity changed".into());
	}
	Ok(())
}
fn sync(f: &File) -> Result<()> {
	f.sync_all().map_err(error)
}
fn mkdir(d: &File, n: &str) -> Result<File> {
	let c = name(OsStr::new(n))?;
	if unsafe { libc::mkdirat(d.as_raw_fd(), c.as_ptr(), 0o700) } != 0
		&& std::io::Error::last_os_error().kind() != std::io::ErrorKind::AlreadyExists
	{
		return Err(io_error("mkdirat"));
	}
	let f = directory(d, OsStr::new(n))?;
	private(&f, true)?;
	Ok(f)
}
fn bounded_document(d: &File, n: &str, limit: usize) -> Result<Option<Value>> {
	if stat(d, OsStr::new(n))?.is_none() {
		return Ok(None);
	}
	let f = open(d, OsStr::new(n), libc::O_RDONLY, 0)?;
	private(&f, false)?;
	let mut b = vec![];
	f.take(limit as u64 + 1)
		.read_to_end(&mut b)
		.map_err(error)?;
	if b.len() > limit {
		return Err("document exceeds allowance".into());
	}
	Ok(Some(serde_json::from_slice(&b).map_err(error)?))
}
fn selected(root: &File) -> Result<Option<String>> {
	let Some(v) = bounded_document(root, "current.json", 65536)
		.map_err(|e| format!("uninterpretable runtime selection: {e}"))?
	else {
		return Ok(None);
	};
	let obj = v.as_object().ok_or("uninterpretable runtime selection")?;
	if obj.len() != 2 || !matches!(v["format"].as_u64(), Some(1 | 2)) {
		return Err("uninterpretable runtime selection".into());
	}
	let id = v["id"]
		.as_str()
		.filter(|v| valid_id(v))
		.ok_or("uninterpretable runtime selection")?;
	Ok(Some(id.into()))
}
fn valid_id(s: &str) -> bool {
	s.len() == 64
		&& s.bytes()
			.all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
#[derive(Default)]
struct Budget {
	nodes: u64,
	memory: u64,
	logical: u64,
	allocated: u64,
	seen: HashSet<(u64, u64)>,
}
impl Budget {
	fn charge(&mut self, bytes: usize) -> Result<()> {
		self.nodes += 1;
		self.memory = self
			.memory
			.checked_add(bytes as u64 + 128)
			.ok_or("accounting overflow")?;
		let limit = std::env::var("RNX_REMOVE_NODE_LIMIT")
			.ok()
			.and_then(|x| x.parse().ok())
			.unwrap_or(1_000_000);
		if self.nodes > limit || self.memory > 256 * 1024 * 1024 {
			return Err("traversal allowance exceeded".into());
		}
		commands::check()
	}
	fn account(&mut self, s: &libc::stat) -> Result<()> {
		if self.seen.insert((s.st_dev, s.st_ino)) {
			self.allocated = self
				.allocated
				.checked_add(
					(s.st_blocks as u64)
						.checked_mul(512)
						.ok_or("block overflow")?,
				)
				.ok_or("block overflow")?;
			if s.st_mode & libc::S_IFMT == libc::S_IFREG {
				self.logical = self
					.logical
					.checked_add(s.st_size as u64)
					.ok_or("byte overflow")?;
			}
		}
		Ok(())
	}
}
fn names(d: &File, b: &mut Budget) -> Result<Vec<OsString>> {
	// A fresh open description, rather than dup sharing a previous directory offset.
	let f = directory(d, OsStr::new("."))?;
	use std::os::fd::IntoRawFd;
	let fd = f.into_raw_fd();
	let dir = unsafe { libc::fdopendir(fd) };
	if dir.is_null() {
		unsafe { libc::close(fd) };
		return Err(io_error("fdopendir"));
	}
	let result = (|| {
		let mut out = vec![];
		loop {
			unsafe { *libc::__errno_location() = 0 };
			let e = unsafe { libc::readdir(dir) };
			if e.is_null() {
				if unsafe { *libc::__errno_location() } != 0 {
					return Err(io_error("readdir"));
				}
				break;
			}
			let n = unsafe { CStr::from_ptr((*e).d_name.as_ptr()) }.to_bytes();
			if n == b"." || n == b".." {
				continue;
			}
			b.charge(n.len())?;
			out.push(OsString::from_vec(n.to_vec()));
		}
		out.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
		Ok(out)
	})();
	unsafe { libc::closedir(dir) };
	result
}
fn walk(d: &File, b: &mut Budget, depth: usize, erase: bool, deleted: &mut u64) -> Result<()> {
	if depth > 128 {
		return Err("depth exceeds 128".into());
	}
	for n in names(d, b)? {
		commands::check()?;
		let s = stat(d, &n)?.ok_or("entry disappeared during walk")?;
		if s.st_uid != unsafe { libc::geteuid() } {
			return Err(format!("unowned data: {n:?}"));
		}
		b.account(&s)?;
		match s.st_mode & libc::S_IFMT {
			libc::S_IFDIR => {
				let child = directory(d, &n)?;
				same(&child, &s)?;
				walk(&child, b, depth + 1, erase, deleted)?;
				if erase {
					same(&child, &stat(d, &n)?.ok_or("directory disappeared")?)?;
					unlink(d, &n, true)?;
				}
			}
			libc::S_IFREG | libc::S_IFLNK => {
				// Open even regular leaves for metadata with the same mount guard.
				// O_PATH does not require file read/write permission or read contents.
				if s.st_mode & libc::S_IFMT == libc::S_IFREG {
					let f = open(d, &n, libc::O_PATH, 0)?;
					same(&f, &s)?;
				}
				if erase {
					unlink(d, &n, false)?;
					*deleted += 1;
					if *deleted == 1 {
						pause("during-delete")?;
					}
				}
			}
			_ => return Err(format!("special file refused: {n:?}")),
		}
	}
	if erase {
		sync(d)?
	}
	Ok(())
}
fn unlink(d: &File, n: &OsStr, dir: bool) -> Result<()> {
	let n = name(n)?;
	if unsafe {
		libc::unlinkat(
			d.as_raw_fd(),
			n.as_ptr(),
			if dir { libc::AT_REMOVEDIR } else { 0 },
		)
	} != 0
	{
		return Err(io_error("unlinkat"));
	}
	Ok(())
}
fn pause(phase: &str) -> Result<()> {
	if std::env::var("RNX_REMOVE_PAUSE").ok().as_deref() == Some(phase) {
		println!("{}", json!({"paused":phase}));
		std::io::stdout().flush().map_err(error)?;
		let release = std::env::var_os("RNX_REMOVE_RELEASE").ok_or("pause needs release file")?;
		while !Path::new(&release).exists() {
			commands::check()?;
			std::thread::sleep(Duration::from_millis(10));
		}
	}
	Ok(())
}
fn quote(p: &OsStr) -> String {
	format!("'{}'", p.to_string_lossy().replace('\'', "'\\''"))
}
struct Args {
	root: PathBuf,
	kind: String,
	id: Option<String>,
	list: bool,
	dry: bool,
	resume: bool,
	quiescent: bool,
}
fn args() -> Result<Args> {
	let mut a = std::env::args_os().skip(1);
	let kind = a
		.next()
		.ok_or("kind required")?
		.into_string()
		.map_err(|_| "kind")?;
	if !matches!(kind.as_str(), "cache" | "runtime") {
		return Err("kind required".into());
	}
	let action = a.next().ok_or("action required")?;
	let list = action == "list";
	if !list && action != "remove" {
		return Err("action required".into());
	}
	let id = if list {
		None
	} else {
		Some(
			a.next()
				.and_then(|v| v.into_string().ok())
				.filter(|v| valid_id(v))
				.ok_or("full ID required")?,
		)
	};
	let mut out = Args {
		root: PathBuf::new(),
		kind,
		id,
		list,
		dry: false,
		resume: false,
		quiescent: false,
	};
	let mut seen = HashSet::new();
	while let Some(v) = a.next() {
		if !seen.insert(v.clone()) {
			return Err("duplicate option".into());
		}
		match v.to_str() {
			Some("--root") => out.root = a.next().ok_or("root value")?.into(),
			Some("--dry-run") => out.dry = true,
			Some("--resume") => out.resume = true,
			Some("--quiescent") => out.quiescent = true,
			_ => return Err("unknown option".into()),
		}
	}
	if !out.root.is_absolute() {
		return Err("absolute explicit root required by prototype".into());
	}
	if list && (out.dry || out.resume || out.quiescent) {
		return Err("list flags".into());
	}
	if !list && !out.dry && !out.quiescent {
		return Err("requires --quiescent or --dry-run".into());
	}
	Ok(out)
}
fn run() -> Result<()> {
	let mut a = args()?;
	commands::install_signals()?;
	a.root = a.root.canonicalize().map_err(error)?;
	let root = OpenOptions::new()
		.read(true)
		.custom_flags(libc::O_CLOEXEC | libc::O_DIRECTORY | libc::O_NOFOLLOW)
		.open(&a.root)
		.map_err(error)?;
	private(&root, true)?;
	let entries = directory(&root, OsStr::new("entries"))?;
	private(&entries, true)?;
	let lock_parent = if a.kind == "cache" {
		if stat(&root, OsStr::new("install.lock"))?.is_some()
			|| stat(&root, OsStr::new("current.json"))?.is_some()
		{
			return Err("opposite runtime controls".into());
		}
		let f = directory(&root, OsStr::new("locks"))?;
		private(&f, true)?;
		Some(f)
	} else {
		if stat(&root, OsStr::new("locks"))?.is_some() {
			return Err("opposite cache controls".into());
		}
		let f = open(&root, OsStr::new("install.lock"), libc::O_RDONLY, 0)?;
		private(&f, false)?;
		None
	};
	if a.list {
		let current = if a.kind == "runtime" {
			selected(&root)?
		} else {
			None
		};
		let mut records = vec![];
		let mut budget = Budget::default();
		for location in ["entries", "removing"] {
			if stat(&root, OsStr::new(location))?.is_none() {
				continue;
			}
			let dir = directory(&root, OsStr::new(location))?;
			private(&dir, true)?;
			for n in names(&dir, &mut budget)? {
				let key = n
					.to_str()
					.filter(|v| valid_id(v))
					.ok_or("unexpected managed name")?;
				let entry = directory(&dir, &n)?;
				private(&entry, true)?;
				budget.seen.clear();
				let before = (budget.nodes, budget.logical, budget.allocated);
				walk(&entry, &mut budget, 0, false, &mut 0)?;
				records.push(json!({"id":key,"location":location,"selected":current.as_deref()==Some(key),"nodes":budget.nodes-before.0,"logical":budget.logical-before.1,"allocated":budget.allocated-before.2}));
			}
		}
		println!(
			"{}",
			json!({"root":a.root,"entries":records,"reference_claim":"none; no reader lease"})
		);
		return Ok(());
	}
	let key = a.id.as_ref().unwrap();
	let key_os = OsStr::new(key);
	let location = if a.resume { "removing" } else { "entries" };
	let _lock = if a.dry {
		None
	} else {
		let (parent, n, flags, mode) = if let Some(p) = &lock_parent {
			(
				p,
				format!("{key}.lock"),
				libc::O_RDWR | libc::O_CREAT,
				0o600,
			)
		} else {
			(&root, "install.lock".into(), libc::O_RDWR, 0)
		};
		let f = open(parent, OsStr::new(&n), flags, mode)?;
		private(&f, false)?;
		f.try_lock()
			.map_err(|e| format!("busy or invalid writer lock: {e}"))?;
		if std::env::var_os("RNX_REMOVE_TEST_LOCK_EXEC").is_some() {
			let m = f.metadata().map_err(error)?;
			let status = std::process::Command::new(std::env::current_exe().map_err(error)?)
				.args([
					"--inspect-lock-fd",
					&f.as_raw_fd().to_string(),
					&m.dev().to_string(),
					&m.ino().to_string(),
				])
				.status()
				.map_err(error)?;
			if !status.success() {
				return Err("writer lock inherited across exec".into());
			}
		}
		Some(f)
	};
	if a.kind == "runtime" && selected(&root)?.as_deref() == Some(key) {
		return Err("selected runtime refused".into());
	}
	if !a.resume && stat(&root, OsStr::new("removing"))?.is_some() {
		let d = directory(&root, OsStr::new("removing"))?;
		private(&d, true)?;
		if stat(&d, key_os)?.is_some() {
			return Err("pending removal exists; use --resume".into());
		}
	}
	let parent = directory(&root, OsStr::new(location))?;
	private(&parent, true)?;
	let target = directory(&parent, key_os)?;
	private(&target, true)?;
	let path = a.root.join(location).join(key);
	for own in [
		std::env::current_dir().map_err(error)?,
		std::env::current_exe().map_err(error)?,
	] {
		if own.starts_with(&path) {
			return Err("current executable or working directory is inside target".into());
		}
	}
	let initial = target.metadata().map_err(error)?;
	let mut budget = Budget::default();
	walk(&target, &mut budget, 0, false, &mut 0)?;
	if a.dry {
		println!(
			"{}",
			json!({"dry_run":true,"id":key,"location":location,"nodes":budget.nodes,"logical":budget.logical,"allocated":budget.allocated,"writer":"not reserved"})
		);
		return Ok(());
	}
	let command = format!(
		"{} {} remove {} --root {} --resume --quiescent",
		quote(std::env::current_exe().map_err(error)?.as_os_str()),
		a.kind,
		key,
		quote(a.root.as_os_str())
	);
	let mut committed = a.resume;
	let operation = (|| {
		pause("before-rename")?;
		let again = directory(&parent, key_os)?;
		let now = again.metadata().map_err(error)?;
		if initial.dev() != now.dev() || initial.ino() != now.ino() {
			return Err("target identity changed before commit".into());
		}
		let pending = if a.resume {
			parent
		} else {
			let pending = mkdir(&root, "removing")?;
			sync(&root)?;
			let key_c = name(key_os)?;
			if unsafe {
				libc::syscall(
					libc::SYS_renameat2,
					entries.as_raw_fd(),
					key_c.as_ptr(),
					pending.as_raw_fd(),
					key_c.as_ptr(),
					libc::RENAME_NOREPLACE,
				)
			} != 0
			{
				return Err(io_error("renameat2"));
			}
			committed = true;
			println!(
				"{}",
				json!({"committed":true,"pending":a.root.join("removing").join(key),"resume_command":command})
			);
			std::io::stdout().flush().map_err(error)?;
			let moved = directory(&pending, key_os)?;
			let m = moved.metadata().map_err(error)?;
			if m.dev() != initial.dev() || m.ino() != initial.ino() {
				return Err("target identity changed after rename".into());
			}
			pause("after-rename")?;
			sync(&entries)?;
			sync(&pending)?;
			pending
		};
		let mut deletion = Budget::default();
		let mut deleted = 0;
		walk(&target, &mut deletion, 0, true, &mut deleted)?;
		same(
			&target,
			&stat(&pending, key_os)?.ok_or("pending entry disappeared")?,
		)?;
		unlink(&pending, key_os, true)?;
		sync(&pending)?;
		println!(
			"{}",
			json!({"removed":key,"location":location,"deleted_leaves":deleted,"logical_before":budget.logical,"allocated_estimate_before":budget.allocated})
		);
		Ok(())
	})();
	operation.map_err(|e| {
		if committed {
			format!("pending removal may remain: {e}\n{command}")
		} else {
			format!("before commitment: {e}")
		}
	})
}
fn main() {
	let a: Vec<String> = std::env::args().collect();
	if a.get(1).map(String::as_str) == Some("--inspect-lock-fd") {
		let fd: i32 = a[2].parse().unwrap();
		let dev: u64 = a[3].parse().unwrap();
		let ino: u64 = a[4].parse().unwrap();
		let mut s = std::mem::MaybeUninit::<libc::stat>::uninit();
		let inherited = unsafe { libc::fstat(fd, s.as_mut_ptr()) } == 0 && {
			let s = unsafe { s.assume_init() };
			s.st_dev == dev && s.st_ino == ino
		};
		println!("{}", json!({"writer_lock_inherited":inherited}));
		std::process::exit(i32::from(inherited));
	}

	if let Err(e) = run() {
		eprintln!("removal prototype: {e}");
		std::process::exit(if commands::interrupted() {
			commands::signal_status()
		} else {
			1
		})
	}
}
