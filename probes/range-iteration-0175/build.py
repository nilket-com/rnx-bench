"""rnx 0175 builds and suites (plan rnx 7699309 sections 3 and 4). Run under the shared lock:

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 build.py OUT_DIR

1. Fork suites from ONE fork worktree (checked out per subject), each subject in its own cleaned target directory:
	base and candidate `cargo test -p rune --all-targets --all-features` (tracing on: zero fast-path hits), and the
	candidate's named non-tracing configuration (positive-hit tests).
2. Harness builds at the frozen default release profile: primary (the performance subject), counter (FIFO
	reproduction, base only consumes it) and allocation (counting allocator; never a performance subject), each
	subject into its own cleaned, equal-length target directory, `cargo build -v` retained.
3. Feature audit: the actual `--cfg feature=...` set passed to the rune crate, which must not contain "tracing".
4. The 0169 resident driver from its pinned source.
Builds run on the controller's original CPU set (recorded); measurement pinning happens later.
"""
import json, os, pathlib, re, shutil, subprocess, sys, time
from common import HERE, FORK, SOURCES, EB, sha, text_sha, run_bounded, Ledger

MANIFEST = HERE / "harness/Cargo.toml"
NON_TRACING = "alloc,bench,byte-code,capture-io,cli,disable-io,doc,emit,fmt,languageserver,musli,serde,std,workspace"


def checkout(rev):
	subprocess.run(["git", "-C", str(FORK), "checkout", "-q", "--detach", rev], check=True, env=EB)
	assert subprocess.run(["git", "-C", str(FORK), "rev-parse", "HEAD"], capture_output=True, text=True, env=EB).stdout.strip() == rev
	assert subprocess.run(["git", "-C", str(FORK), "status", "--porcelain"], capture_output=True, text=True, env=EB).stdout == ""


def fresh(path):
	if path.exists():
		shutil.rmtree(path)
	return path


def step(out, ledger, label, argv, env, cwd=None, timeout=3600):
	began = time.monotonic()
	try:
		r = run_bounded(argv, timeout, env, cwd=cwd)
		status, log = r.returncode, r.stdout + r.stderr
	except subprocess.TimeoutExpired:
		status, log = "timeout", ""
	elapsed = time.monotonic() - began
	(out / f"{label}.log").write_text(log)
	ledger.write(kind="step", label=label, argv=argv, env=env, cwd=str(cwd) if cwd else None, status=status, seconds=elapsed)
	return status, log, elapsed


def rune_features(log):
	"""The --cfg feature set of the `rune` crate's own rustc invocation (not rune-alloc/rune-core)."""
	sets = []
	for line in log.splitlines():
		if "--crate-name rune " in line and "Running" in line:
			sets.append(sorted(set(re.findall(r"feature=\\?\"([a-z0-9_-]+)\\?\"", line))))
	assert len(sets) == 1, ("rune rustc invocations", len(sets))
	return sets[0]


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert len(os.sched_getaffinity(0)) == os.cpu_count(), "builds must start unpinned"
	ledger = Ledger(out / "commands.jsonl")
	res = {"rustc": subprocess.run(["rustc", "-vV"], capture_output=True, text=True, env=EB).stdout, "sources": SOURCES,
		"build_affinity": sorted(os.sched_getaffinity(0))}
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	# 1. Suites.
	suites = {}
	for subject, rev in SOURCES.items():
		checkout(rev)
		env = {**EB, "CARGO_TARGET_DIR": str(fresh(HERE / f"test-{subject}"))}
		runs = [("all-features", ["cargo", "test", "--locked", "-p", "rune", "--all-targets", "--all-features"])]
		if subject == "cand":
			runs.append(("non-tracing", ["cargo", "test", "--locked", "-p", "rune", "--lib", "--no-default-features",
				"--features", NON_TRACING, "range_iteration"]))
		for name, argv in runs:
			status, log, elapsed = step(out, ledger, f"suite-{subject}-{name}", argv, env, cwd=FORK)
			passed = sum(int(m) for m in re.findall(r"test result: ok\. (\d+) passed", log))
			failed = sum(int(m) for m in re.findall(r"; (\d+) failed", log))
			suites[f"{subject}-{name}"] = {"rev": rev, "status": status, "passed": passed, "failed": failed, "seconds": elapsed}
			print(subject, name, suites[f"{subject}-{name}"], flush=True)
		shutil.rmtree(env["CARGO_TARGET_DIR"])
	res["suites"] = suites
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	assert all(v["status"] == 0 and v["failed"] == 0 and v["passed"] > 0 for v in suites.values()), ("STOP: suite", suites)
	# 2. Harness builds (default release profile; opt-level 3 is Cargo's default).
	bindir = fresh(HERE / "bin")
	bindir.mkdir()
	builds = {}
	for subject, rev in SOURCES.items():
		checkout(rev)
		target = fresh(HERE / f"tgt-{subject}")
		for kind in ("primary", "counter", "allocation"):
			feat = [] if kind == "primary" else ["--features", kind]
			argv = ["cargo", "build", "-v", "--release", "--locked", "--offline", "-j", "8", *feat, "--manifest-path", str(MANIFEST)]
			status, log, elapsed = step(out, ledger, f"build-{subject}-{kind}", argv, {**EB, "CARGO_TARGET_DIR": str(target)})
			assert status == 0, ("STOP: build", subject, kind)
			exe = bindir / f"{subject}-{kind}"
			shutil.copy2(target / "release/rune-base-new", exe)
			row = {"rev": rev, "seconds": elapsed, "sha256": sha(exe), "text_sha256": text_sha(exe), "bytes": exe.stat().st_size}
			# Only a build that recompiled rune shows its invocation; the primary build always does (fresh target).
			if "--crate-name rune " in log:
				row["rune_features"] = rune_features(log)
				assert "tracing" not in row["rune_features"], ("STOP: tracing feature in measured build", row["rune_features"])
			builds[f"{subject}-{kind}"] = row
			print(subject, kind, row["sha256"][:12], row.get("rune_features"), flush=True)
		shutil.rmtree(target)
	assert builds["base-primary"]["rune_features"] == builds["cand-primary"]["rune_features"], "feature sets differ"
	res["builds"] = builds
	checkout(SOURCES["base"])
	# 3. The resident driver.
	clock = HERE / "clock"
	clock.mkdir(exist_ok=True)
	c = subprocess.run(["rustc", "--edition", "2021", "-C", "opt-level=3", str(HERE / "plan_clock.rs"), "-o", str(clock / "plan_clock")],
		capture_output=True, text=True, env=EB)
	assert c.returncode == 0, c.stderr[-500:]
	res["clock"] = {"source_sha256": sha(HERE / "plan_clock.rs"), "sha256": sha(clock / "plan_clock")}
	(out / "build.json").write_text(json.dumps(res, indent=1) + "\n")
	(out / "partial.json").unlink()


if __name__ == "__main__":
	main(sys.argv[1])
