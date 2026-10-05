"""rnx 0174 product build cost: one clean `cargo install` of rnx at 785557a per profile (P0 P1 P2 P3, single observations).

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 install.py OUT_DIR

Each profile gets an isolated `git archive` copy of rnx at 785557a (only [profile.release] edited), a fresh empty
CARGO_TARGET_DIR and a fresh empty --root, -j 8, environment EB, default features, --locked --offline after one timed
`cargo fetch --locked`. Runs on the controller's original CPU set (recorded). The installed rnx uses its shipped Rune
0.14.2, not the fork: these figures describe product build cost only.
"""
import io, json, os, pathlib, shutil, subprocess, sys, tarfile, time
from common import HERE, EB, sha, text_sha, set_profile, Ledger

RNX = pathlib.Path("/home/me/work/rnx")
REV = "785557aa5e7d9e5c1daa07e9e8311fa8ae6c1d5a"
WORK = pathlib.Path("/home/me/work/rnx-0174-install")


def copy(dest):
	if dest.exists():
		shutil.rmtree(dest)
	dest.mkdir(parents=True)
	blob = subprocess.run(["git", "-C", str(RNX), "archive", "--format=tar", REV], capture_output=True, check=True, env=EB).stdout
	with tarfile.open(fileobj=io.BytesIO(blob)) as t:
		t.extractall(dest, filter="data")


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert len(os.sched_getaffinity(0)) == os.cpu_count(), "installs must start unpinned"
	ledger = Ledger(out / "commands.jsonl")
	rev = subprocess.run(["git", "-C", str(RNX), "rev-parse", REV], capture_output=True, text=True, check=True, env=EB).stdout.strip()
	rows = {"rnx": rev, "rustc": subprocess.run(["rustc", "-vV"], capture_output=True, text=True, env=EB).stdout}
	fetch_copy = WORK / "fetch"
	copy(fetch_copy)
	began = time.monotonic()
	f = subprocess.run(["cargo", "fetch", "--locked", "--manifest-path", str(fetch_copy / "Cargo.toml")], capture_output=True, text=True, env=EB)
	rows["fetch"] = {"status": f.returncode, "seconds": time.monotonic() - began}
	assert f.returncode == 0, f.stderr[-500:]
	bindir = HERE / "bin"
	bindir.mkdir(exist_ok=True)
	installs = []
	for profile in ("p0", "p1", "p2", "p3"):
		src, target, root = WORK / f"src-{profile}", WORK / f"tgt-{profile}", WORK / f"root-{profile}"
		copy(src)
		for d in (target, root):
			if d.exists():
				shutil.rmtree(d)
		set_profile(src / "Cargo.toml", profile)
		argv = ["cargo", "install", "-v", "--path", str(src), "--locked", "--offline", "-j", "8", "--root", str(root)]
		env = {**EB, "CARGO_TARGET_DIR": str(target)}
		began = time.monotonic()
		try:
			r = subprocess.run(argv, capture_output=True, text=True, timeout=3600, env=env)
			status, log = r.returncode, r.stdout + r.stderr
		except subprocess.TimeoutExpired as e:
			status, log = "timeout", (e.stdout or b"").decode(errors="replace") + (e.stderr or b"").decode(errors="replace")
		elapsed = time.monotonic() - began
		(out / f"install-{profile}.log").write_text(log)
		ledger.write(kind="install", profile=profile, argv=argv, env=env, status=status, seconds=elapsed)
		row = {"profile": profile, "status": status, "seconds": elapsed, "build_affinity": sorted(os.sched_getaffinity(0)),
			"manifest_profile": (src / "Cargo.toml").read_text().split("[profile.release]", 1)[1]}
		if status == 0:
			exe = root / "bin/rnx"
			shutil.copy2(exe, bindir / f"rnx-{profile}")
			row.update(sha256=sha(exe), text_sha256=text_sha(exe), bytes=exe.stat().st_size)
		installs.append(row)
		shutil.rmtree(target, ignore_errors=True)
		print(profile, status, round(elapsed, 1), row.get("bytes"), flush=True)
	rows["installs"] = installs
	(out / "install.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
