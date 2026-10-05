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


def run_bounded(argv, timeout, env, stdin=None, cwd=None):
	"""Run in its own process group; on deadline kill the whole group and reap it before raising."""
	p = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
		stderr=subprocess.PIPE, text=True, env=env, cwd=cwd, start_new_session=True)
	try:
		out, err = p.communicate(stdin, timeout=timeout)
	except subprocess.TimeoutExpired:
		os.killpg(p.pid, signal.SIGKILL)
		p.communicate()
		raise
	return subprocess.CompletedProcess(argv, p.returncode, out, err)


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
