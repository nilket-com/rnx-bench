"""rnx 0178 suites and builds (plan rnx 31ca480 section 2; 0176 tooling with a profile axis). Under the shared lock:

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 build.py OUT_DIR

1. Fork suites once per source from ONE fork worktree path, each source in its own cleaned target: all three
	`cargo test -p rune --all-targets --all-features` (tracing on: zero fast-path hits), the candidates' named
	non-tracing configuration (positive hits), and every source's no-std check.
2. One timed `cargo fetch --locked` for the harness, then 18 builds in the frozen order P0-B, P1-B, P1-S75, P0-S75,
	P0-S76, P1-S76, each as primary, counter, allocation. Every build gets the SAME freshly emptied target path, -j8,
	--locked --offline, EB (no RUSTFLAGS), `cargo build -v` retained. Only [profile.release] of the harness manifest
	changes (0174 mechanics); the profile section is set once per (profile, source) cell and the manifest is restored
	and sha-verified at each cell boundary (after its three kinds). Build cost is the wall time of the `cargo build`
	command alone (compile and link; it excludes the binary copy and identity extraction), one observation per build.
3. Effective settings from the verbose rustc lines: every invocation building linked code (`-C opt-level=3`) carries
	`-C codegen-units=1` under P1 and no codegen-units flag under P0; host build-dependency invocations are counted
	separately; rune's actual --cfg feature set, which must not contain tracing.
4. The 0169 resident driver from its pinned source.
"""
import json, os, pathlib, re, shutil, subprocess, sys, time
from common import HERE, FORK, SOURCES, PROFILES, BUILD_ORDER, KINDS, EB, sha, text_sha, run_bounded, set_profile, Ledger

MANIFEST = HERE / "harness/Cargo.toml"
NON_TRACING = "alloc,bench,byte-code,capture-io,cli,disable-io,doc,emit,fmt,languageserver,musli,serde,std,workspace"
TARGET = HERE / "tgt-build"


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
	r = run_bounded(argv, timeout, env, cwd=cwd)
	# A deadline keeps whatever the step wrote before it was killed.
	status, log = ("timeout" if r.timed_out else r.returncode), r.stdout + r.stderr
	elapsed = time.monotonic() - began
	(out / f"{label}.log").write_text(log)
	ledger.write(kind="step", label=label, argv=argv, env=env, cwd=str(cwd) if cwd else None, status=status, seconds=elapsed,
		timed_out=r.timed_out, interrupted=r.interrupted, reaped=r.reaped, group_survivors=r.survivors)
	lifecycle_gate(r, label)  # after retention: a clean exit status alone is not accepted
	return status, log, elapsed


def lifecycle_gate(r, label):
	"""Reject a deadline, interrupt, unreaped leader or any live group survivor, whatever the exit status."""
	if r.timed_out or r.interrupted or r.reaped is not True or r.survivors:
		raise SystemExit(("STOP: process lifecycle", label, r.timed_out, r.interrupted, r.reaped, r.survivors))


def rustc_lines(log):
	return [l for l in log.splitlines() if "Running `" in l and "rustc " in l and "--crate-name" in l]


def rune_features(log):
	"""The --cfg feature set of the `rune` crate's own rustc invocation (not rune-alloc/rune-core)."""
	sets = [sorted(set(re.findall(r"feature=\\?\"([a-z0-9_-]+)\\?\"", l))) for l in rustc_lines(log) if "--crate-name rune " in l]
	assert len(sets) == 1, ("rune rustc invocations", len(sets))
	return sets[0]


def codegen_units(log):
	"""Per rustc invocation that builds code linked into the subject (marked by `-C opt-level=3`): its explicit
	-C codegen-units value, or None when Cargo left the default. Host-side build dependencies (proc-macros and their
	dependencies under Cargo's build-override, which pass no opt-level flag) are counted separately: they run at
	compile time and are not part of the measured binary."""
	target, host = [], 0
	for l in rustc_lines(log):
		if "-C opt-level=3" in l:
			m = re.search(r"-C codegen-units=(\d+)", l)
			target.append((re.search(r"--crate-name (\S+)", l).group(1), int(m.group(1)) if m else None))
		else:
			host += 1
	return target, host


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert len(os.sched_getaffinity(0)) == os.cpu_count(), "builds must start unpinned"
	ledger = Ledger(out / "commands.jsonl")
	original = MANIFEST.read_text()
	res = {"rustc": subprocess.run(["rustc", "-vV"], capture_output=True, text=True, env=EB).stdout, "sources": SOURCES,
		"profiles": PROFILES, "build_order": BUILD_ORDER, "build_affinity": sorted(os.sched_getaffinity(0)),
		"manifest_sha256": sha(MANIFEST), "harness_lock_sha256": sha(HERE / "harness/Cargo.lock")}
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	# 1. Suites, once per source.
	suites = {}
	for source, rev in SOURCES.items():
		checkout(rev)
		env = {**EB, "CARGO_TARGET_DIR": str(fresh(HERE / f"test-{source}"))}
		runs = [("all-features", ["cargo", "test", "--locked", "-p", "rune", "--all-targets", "--all-features"])]
		if source != "base":
			runs.append(("non-tracing", ["cargo", "test", "--locked", "-p", "rune", "--lib", "--no-default-features",
				"--features", NON_TRACING, "range_iteration"]))
		runs.append(("no-std", ["cargo", "check", "--locked", "--offline", "-p", "rune", "--no-default-features", "--features", "alloc"]))
		for name, argv in runs:
			status, log, elapsed = step(out, ledger, f"suite-{source}-{name}", argv, env, cwd=FORK)
			passed = sum(int(m) for m in re.findall(r"test result: ok\. (\d+) passed", log))
			failed = sum(int(m) for m in re.findall(r"; (\d+) failed", log))
			suites[f"{source}-{name}"] = {"rev": rev, "status": status, "passed": passed, "failed": failed, "seconds": elapsed}
			print(source, name, suites[f"{source}-{name}"], flush=True)
		shutil.rmtree(env["CARGO_TARGET_DIR"])
	res["suites"] = suites
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	bad = {k: v for k, v in suites.items() if v["status"] != 0 or v["failed"] != 0 or (k.endswith("-no-std") is False and v["passed"] == 0)}
	assert not bad, ("STOP: suite", bad)
	# 2. One timed locked fetch, then the 18 builds.
	began = time.monotonic()
	f = run_bounded(["cargo", "fetch", "--locked", "--manifest-path", str(MANIFEST)], 1800, EB)
	res["fetch"] = {**f.record(), "seconds": time.monotonic() - began}
	(out / "fetch.log").write_text(f.stdout + f.stderr)
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	lifecycle_gate(f, "fetch")
	assert f.returncode == 0, ("STOP: fetch", f.stderr[-500:])
	bindir = fresh(HERE / "bin")
	bindir.mkdir()
	builds = {}
	try:
		for profile, source in BUILD_ORDER:
			checkout(SOURCES[source])
			text = set_profile(MANIFEST, profile)
			for kind in KINDS:
				fresh(TARGET)
				feat = [] if kind == "primary" else ["--features", kind]
				argv = ["cargo", "build", "-v", "--release", "--locked", "--offline", "-j", "8", *feat, "--manifest-path", str(MANIFEST)]
				name = f"{profile}-{source}-{kind}"
				status, log, elapsed = step(out, ledger, f"build-{name}", argv, {**EB, "CARGO_TARGET_DIR": str(TARGET)})
				assert status == 0, ("STOP: build", name)
				exe = bindir / name
				shutil.copy2(TARGET / "release/rune-base-new", exe)
				target, host = codegen_units(log)
				want = 1 if PROFILES[profile] else None
				assert target and all(v == want for _, v in target), ("STOP: effective codegen-units", name, [t for t in target if t[1] != want])
				row = {"profile": profile, "source": source, "kind": kind, "rev": SOURCES[source], "seconds": elapsed,
					"sha256": sha(exe), "text_sha256": text_sha(exe), "bytes": exe.stat().st_size, "manifest_profile_section":
					text.split("[profile.release]", 1)[1], "target_invocations": len(target), "host_invocations": host,
					"codegen_units": "1 on every target invocation" if want else "default (no flag) on every target invocation",
					"rune_features": rune_features(log)}
				assert "tracing" not in row["rune_features"], ("STOP: tracing feature in measured build", name)
				builds[name] = row
				print(name, row["sha256"][:12], round(elapsed, 1), "s", flush=True)
			MANIFEST.write_text(original)
			assert sha(MANIFEST) == res["manifest_sha256"], "manifest not restored"
	finally:
		MANIFEST.write_text(original)
		shutil.rmtree(TARGET, ignore_errors=True)
	feats = {tuple(v["rune_features"]) for v in builds.values()}
	assert len(feats) == 1, ("feature sets differ", feats)
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
