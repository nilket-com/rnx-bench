"""rnx 0174 harness builds: 3 sources x 4 profiles for measurement, plus 3 timed clean base builds per profile.

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 build.py OUT_DIR

Every build compiles ONE harness path against ONE fork worktree path (checked out per source) into its own empty,
equal-length target directory, with -j 8, environment EB, --locked --offline (dependencies fetched once beforehand
and timed separately), and `cargo build -v` output retained so the actual rustc/link arguments are on record.
Builds run on the controller's original CPU set (recorded per build as build_affinity; never pinned).
Balanced order for the timed base builds: P0 P1 P2 P3 / P3 P2 P1 P0 / P1 P3 P0 P2. 60-minute deadline per build.
"""
import json, os, pathlib, shutil, subprocess, sys, time
from common import HERE, FORK, SOURCES, PROFILES, EB, sha, text_sha, set_profile, Ledger

MANIFEST = HERE / "harness/Cargo.toml"
ORDER = [["p0", "p1", "p2", "p3"], ["p3", "p2", "p1", "p0"], ["p1", "p3", "p0", "p2"]]


def checkout(rev):
	subprocess.run(["git", "-C", str(FORK), "checkout", "-q", "--detach", rev], check=True, env=EB)
	assert subprocess.run(["git", "-C", str(FORK), "rev-parse", "HEAD"], capture_output=True, text=True, env=EB).stdout.strip() == rev
	assert subprocess.run(["git", "-C", str(FORK), "status", "--porcelain"], capture_output=True, text=True, env=EB).stdout == ""


def build(out, label, profile, ledger):
	target = HERE / f"tgt-{label}"
	if target.exists():
		shutil.rmtree(target)
	set_profile(MANIFEST, profile)
	argv = ["cargo", "build", "-v", "--release", "--locked", "--offline", "-j", "8", "--manifest-path", str(MANIFEST)]
	env = {**EB, "CARGO_TARGET_DIR": str(target)}
	began = time.monotonic()
	try:
		r = subprocess.run(argv, capture_output=True, text=True, timeout=3600, env=env)
		status = r.returncode
		log = r.stdout + r.stderr
	except subprocess.TimeoutExpired as e:
		status, log = "timeout", (e.stdout or b"").decode(errors="replace") + (e.stderr or b"").decode(errors="replace")
	elapsed = time.monotonic() - began
	(out / f"build-{label}.log").write_text(log)
	ledger.write(kind="build", label=label, profile=profile, argv=argv, env=env, status=status, seconds=elapsed)
	row = {"label": label, "profile": profile, "status": status, "seconds": elapsed, "build_affinity": sorted(os.sched_getaffinity(0))}
	if status == 0:
		exe = target / "release/rune-base-new"
		row.update(sha256=sha(exe), text_sha256=text_sha(exe), bytes=exe.stat().st_size)
	return row, target


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert len(os.sched_getaffinity(0)) == os.cpu_count(), "builds must start unpinned"
	ledger = Ledger(out / "commands.jsonl")
	rows = {"rustc": subprocess.run(["rustc", "-vV"], capture_output=True, text=True, env=EB).stdout}
	checkout(SOURCES["base"])
	began = time.monotonic()
	f = subprocess.run(["cargo", "fetch", "--locked", "--manifest-path", str(MANIFEST)], capture_output=True, text=True, env=EB)
	rows["fetch"] = {"status": f.returncode, "seconds": time.monotonic() - began}
	assert f.returncode == 0, f.stderr[-500:]
	bindir = HERE / "bin"
	bindir.mkdir(exist_ok=True)
	timed = []
	for rep, order in enumerate(ORDER):
		for profile in order:
			row, target = build(out, f"cost-{rep}-{profile}", profile, ledger)
			timed.append({**row, "rep": rep})
			if rep == 0 and row["status"] == 0:
				shutil.copy2(target / "release/rune-base-new", bindir / f"base-{profile}")
			shutil.rmtree(target, ignore_errors=True)
	rows["timed_base_builds"] = timed
	subjects = {}
	for src in ("s71", "s72"):
		checkout(SOURCES[src])
		for profile in PROFILES:
			row, target = build(out, f"{src}-{profile}", profile, ledger)
			subjects[f"{src}-{profile}"] = row
			if row["status"] == 0:
				shutil.copy2(target / "release/rune-base-new", bindir / f"{src}-{profile}")
			shutil.rmtree(target, ignore_errors=True)
	for profile in PROFILES:
		p = bindir / f"base-{profile}"
		if p.exists():
			subjects[f"base-{profile}"] = {"sha256": sha(p), "text_sha256": text_sha(p), "bytes": p.stat().st_size}
	rows["subjects"] = subjects
	clock = HERE / "clock"
	clock.mkdir(exist_ok=True)
	c = subprocess.run(["rustc", "--edition", "2021", "-C", "opt-level=3", str(HERE / "plan_clock.rs"), "-o", str(clock / "plan_clock")],
		capture_output=True, text=True, env=EB)
	assert c.returncode == 0, c.stderr[-500:]
	rows["clock"] = {"source_sha256": sha(HERE / "plan_clock.rs"), "sha256": sha(clock / "plan_clock")}
	set_profile(MANIFEST, "p0")
	checkout(SOURCES["base"])
	(out / "build.json").write_text(json.dumps(rows, indent=1) + "\n")
	for k, v in subjects.items():
		print(k, v.get("status", 0), v.get("sha256", "")[:12], v.get("text_sha256", "")[:12], v.get("bytes"))


if __name__ == "__main__":
	main(sys.argv[1])
