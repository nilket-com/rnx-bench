"""Shared pieces for rnx 0175: frozen environment, sources, bounded process groups, redaction-safe logging, the sentinel scan."""
import hashlib, json, lzma, os, pathlib, secrets, signal, subprocess, time

HERE = pathlib.Path(__file__).resolve().parent
FORK = pathlib.Path("/home/me/work/rune-w-0173")
# Base: every base-first test commit, production source = common parent 3e7d4da9. Candidate: the squashed fast path.
SOURCES = {"base": "eaa59fc208c136ead86f8c4fa565431ea18de88b", "cand": "863370da279031b369ebb0ac1c0d80cd9ca159f6"}
PRODUCTION_PARENT = "3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a"
E0 = {"PATH": "/usr/bin:/bin", "HOME": "/home/me", "LANG": "C.UTF-8"}
# Build environment: E0 plus the toolchain locations (no other inherited variable).
EB = {**E0, "PATH": "/home/me/.cargo/bin:/usr/bin:/bin", "CARGO_HOME": "/home/me/.cargo", "RUSTUP_HOME": "/home/me/.rustup",
	"CARGO_INCREMENTAL": "0"}


def sha(p):
	return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def text_sha(p):
	r = subprocess.run(["objcopy", "-O", "binary", "--only-section=.text", str(p), "/dev/stdout"], capture_output=True, check=True)
	return hashlib.sha256(r.stdout).hexdigest()


class Result:
	"""A finished (or deadline-killed) process: status, raw output and how it ended. Never raises for the child."""

	def __init__(self, argv, returncode, stdout, stderr, timed_out, interrupted, reaped, survivors):
		self.args, self.returncode, self.stdout, self.stderr = argv, returncode, stdout, stderr
		self.timed_out, self.interrupted, self.reaped, self.survivors = timed_out, interrupted, reaped, survivors

	def record(self):
		return {"argv": self.args, "status": self.returncode, "stdout": self.stdout, "stderr": self.stderr,
			"timed_out": self.timed_out, "interrupted": self.interrupted, "reaped": self.reaped, "group_survivors": self.survivors}


def kill_group(pid):
	"""SIGKILL every remaining member of a process group; absent groups are fine."""
	try:
		os.killpg(pid, signal.SIGKILL)
	except ProcessLookupError:
		pass


def live_members(pgid):
	"""Non-zombie processes in a process group, from /proc. A killed member stays in its group as a zombie until its
	(possibly adoptive) parent reaps it, so "the group exists" is not "the group is running"."""
	members = []
	for stat in pathlib.Path("/proc").glob("[0-9]*/stat"):
		try:
			fields = stat.read_text().rsplit(")", 1)[1].split()
		except (OSError, IndexError):
			continue
		if int(fields[2]) == pgid and fields[0] != "Z":
			members.append(int(stat.parent.name))
	return members


def settle(pgid, seconds=5.0):
	"""Live members still present after up to `seconds` of polling (empty once the killed group is gone)."""
	deadline = time.monotonic() + seconds
	while True:
		members = live_members(pgid)
		if not members or time.monotonic() >= deadline:
			return members
		time.sleep(0.05)


def group_alive(pgid, settle=5.0):
	"""True if any live (non-zombie) member remains after up to `settle` seconds."""
	deadline = time.monotonic() + settle
	while live_members(pgid):
		if time.monotonic() >= deadline:
			return True
		time.sleep(0.05)
	return False


def run_bounded(argv, timeout, env, stdin=None, cwd=None, scratch=None):
	"""Run argv as the leader of its own process group, output to files (no pipe a descendant could hold open).
	On every outcome (exit, deadline, interrupt or any other unwind) the whole group is killed and the leader reaped
	with a bounded wait; the partial output is always returned or attached to the propagating exception."""
	import tempfile
	with tempfile.TemporaryDirectory(dir=scratch) as d:
		out_path, err_path = pathlib.Path(d) / "stdout", pathlib.Path(d) / "stderr"
		timed_out = interrupted = False
		with out_path.open("wb") as out_f, err_path.open("wb") as err_f:
			p = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL, stdout=out_f, stderr=err_f,
				env=env, cwd=cwd, start_new_session=True)
		reaped = False
		try:
			if stdin is not None:
				try:
					p.stdin.write(stdin.encode())
					p.stdin.close()
				except BrokenPipeError:
					pass
			try:
				p.wait(timeout=timeout)
			except subprocess.TimeoutExpired:
				timed_out = True
		except BaseException as error:
			interrupted = True
			kill_group(p.pid)
			try:
				p.wait(timeout=10)
				reaped = True
			except subprocess.TimeoutExpired:
				pass
			error.partial = Result(argv, p.returncode, out_path.read_bytes().decode(errors="replace"),
				err_path.read_bytes().decode(errors="replace"), timed_out, True, reaped, settle(p.pid)).record()
			raise
		finally:
			if not interrupted:
				kill_group(p.pid)
				try:
					p.wait(timeout=10)
					reaped = True
				except subprocess.TimeoutExpired:
					pass
		return Result(argv, p.returncode, out_path.read_bytes().decode(errors="replace"), err_path.read_bytes().decode(errors="replace"),
			timed_out, False, reaped, settle(p.pid))


class LineReader:
	"""Newline-terminated lines from a nonblocking fd, each before a monotonic deadline. `seen` keeps every byte ever
	read (including a trailing partial line), so a failure can retain the protocol bytes."""

	def __init__(self, fd):
		os.set_blocking(fd, False)
		self.fd, self.seen, self.pending = fd, bytearray(), bytearray()

	def line(self, deadline):
		import select as _select
		while True:
			nl = self.pending.find(b"\n")
			if nl >= 0:
				line = bytes(self.pending[:nl + 1])
				del self.pending[:nl + 1]
				return line.decode(errors="replace")
			left = deadline - time.monotonic()
			if left <= 0 or not _select.select([self.fd], [], [], left)[0]:
				raise TimeoutError(f"no complete line before deadline; partial={bytes(self.pending)!r}")
			try:
				chunk = os.read(self.fd, 4096)
			except BlockingIOError:
				continue
			if not chunk:
				raise EOFError(f"stream closed; partial={bytes(self.pending)!r}")
			self.seen += chunk
			self.pending += chunk


def digest_tree(root, patterns):
	"""sha256 per file for the given glob patterns under root (sorted, relative paths)."""
	root = pathlib.Path(root)
	return {str(p.relative_to(root)): sha(p) for pattern in patterns for p in sorted(root.glob(pattern)) if p.is_file()}


def new_sentinel():
	"""A random value placed in this controller's own environment only; never written anywhere."""
	value = secrets.token_hex(16)
	os.environ["RNX0175_SENTINEL"] = value
	return value


def count(data, suffix, needles):
	"""Occurrences of the needles in data, also inside it when it is an .xz stream."""
	if suffix == ".xz":
		try:
			data = data + lzma.decompress(data)
		except lzma.LZMAError:
			pass
	return sum(data.count(x.encode()) for x in needles if x)


def scan(root, needles):
	"""Count occurrences of each needle in every file under root, decompressing .xz; returns {path: count}."""
	hits = {}
	for p in pathlib.Path(root).rglob("*"):
		if p.is_file():
			n = count(p.read_bytes(), p.suffix, needles)
			if n:
				hits[str(p)] = n
	return hits


class Ledger:
	"""Append-only JSONL command log. Records argv and the explicit environment passed, never os.environ."""

	def __init__(self, path):
		self.path = pathlib.Path(path)

	def write(self, **row):
		row["t"] = time.time()
		with self.path.open("a") as f:
			f.write(json.dumps(row) + "\n")
