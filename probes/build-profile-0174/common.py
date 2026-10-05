"""Shared pieces for rnx 0174: frozen environment, profiles, sources, redaction-safe logging, the sentinel scan."""
import hashlib, json, lzma, os, pathlib, secrets, subprocess, time

HERE = pathlib.Path(__file__).resolve().parent
FORK = pathlib.Path("/home/me/work/rune-w-0173")
SOURCES = {"base": "3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a", "s71": "30c53555c97b183dfada30cb563fcf5bedeb0d31",
	"s72": "7e748d020d763f330b64f2d33411e559de999231"}
PROFILES = {
	"p0": [],
	"p1": ["codegen-units = 1"],
	"p2": ['lto = "thin"', "codegen-units = 1"],
	"p3": ['lto = "fat"', "codegen-units = 1"],
}
E0 = {"PATH": "/usr/bin:/bin", "HOME": "/home/me", "LANG": "C.UTF-8"}
# Build environment: E0 plus the toolchain locations (no other inherited variable).
EB = {**E0, "PATH": "/home/me/.cargo/bin:/usr/bin:/bin", "CARGO_HOME": "/home/me/.cargo", "RUSTUP_HOME": "/home/me/.rustup",
	"CARGO_INCREMENTAL": "0"}


def sha(p):
	return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def text_sha(p):
	r = subprocess.run(["objcopy", "-O", "binary", "--only-section=.text", str(p), "/dev/stdout"], capture_output=True, check=True)
	return hashlib.sha256(r.stdout).hexdigest()


def set_profile(manifest, profile):
	"""Rewrite only the [profile.release] section of a manifest to the frozen profile (opt-level 3 kept)."""
	m = pathlib.Path(manifest)
	lines = m.read_text().splitlines()
	out, skip = [], False
	for line in lines:
		if line.strip() == "[profile.release]":
			skip = True
			continue
		if skip and line.startswith("["):
			skip = False
		if not skip:
			out.append(line)
	while out and not out[-1].strip():
		out.pop()
	out += ["", "[profile.release]", "opt-level = 3", *PROFILES[profile]]
	m.write_text("\n".join(out) + "\n")


def new_sentinel():
	"""A random value placed in this controller's own environment only; never written anywhere."""
	value = secrets.token_hex(16)
	os.environ["RNX0174_SENTINEL"] = value
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
