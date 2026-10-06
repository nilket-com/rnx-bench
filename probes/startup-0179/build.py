"""rnx 0179 suites and builds (plan rnx a2bea93 sections 3-4; 0178 tooling, P0 only). Under the shared lock:

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 build.py OUT_DIR

0. Candidate scope: the files changed between base and candidate, split into production and test-only files; the only
	production file may be crates/rune/src/compile/context.rs (feasibility 5c9847d section 5).
1. Fork suites once per source from ONE fork worktree path, each in its own cleaned target: the full
	`cargo test -p rune --all-targets --all-features` (no diagnostic cfg, every root test kept), the base contract
	tests under the exact measured feature set (alloc,anyhow,fmt,serde,std) with the reviewed test-only cfg
	rune_startup_inventory set for THAT command only, and the no-std check.
2. Neutrality control: the UNCHANGED 0178 harness (probes/profile-paired-0178/harness) built as the P0 primary against
	the tests-first base and compared section by section with 0178's retained P0 base primary. Never staged or timed.
	Whole-file identity was the first form of this control and FAILED on prep1 (retained): the base's `#[cfg(test)]`
	registration-order lines move one panic location's line number in context.rs. The reviewed form (neutrality.py)
	compares every byte of the two files and accepts only validated differences: build-id descriptor, `.llvm.<n>`
	local-symbol suffixes, and panic line fields of context.rs locations moved by exactly the source diff's shift.
	The rebuilt binary is retained (neutrality-bin/, untracked, hash in the receipt) before the target is cleaned.
3. One timed `cargo fetch --locked` for the adapted harness, then 6 builds in the frozen order P0-base, P0-cand, each
	as primary, counter, allocation. Every build gets the SAME freshly emptied target path, -j8, --locked --offline,
	EB (no RUSTFLAGS), `cargo build -v` retained. Build cost is the wall time of the `cargo build` command alone.
4. Effective settings from the verbose rustc lines: no codegen-units flag on any linked-code invocation (P0); rune's
	actual --cfg feature set, which must not contain tracing; the diagnostic cfg may appear only inside the
	`--check-cfg` declaration Cargo always passes, never as a set cfg (diagnostic_cfg_uses).
5. The 0169 resident driver from its pinned source.
"""
import json, os, pathlib, re, shutil, subprocess, sys, time
from common import HERE, FORK, SOURCES, PROFILES, BUILD_ORDER, KINDS, EB, sha, text_sha, run_bounded, set_profile, Ledger
import neutrality

MANIFEST = HERE / "harness/Cargo.toml"
HISTORICAL = HERE.parent / "profile-paired-0178"  # the unchanged 0178 harness and its frozen manifest
PRODUCTION_FEATURES = "alloc,anyhow,fmt,serde,std"
DIAGNOSTIC_CFG = "rune_startup_inventory"
HISTORICAL_BASE = "eaa59fc208c136ead86f8c4fa565431ea18de88b"  # 0178's base source
PRODUCTION_FILES = ["crates/rune/src/compile/context.rs"]
TEST_ONLY_FILES = ["crates/rune/src/compile/context_startup_tests.rs"]
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


def diagnostic_cfg_uses(log):
	"""Every mention of the diagnostic cfg in a verbose build log EXCEPT its declaration: Cargo passes the crate's
	[lints.rust] check-cfg list to rustc as `--check-cfg 'cfg(...)'` on every build, which only names the cfg as known.
	Any other mention (above all `--cfg rune_startup_inventory`) means a measured build could have had it set.
	The first form of this guard rejected the declaration itself and stopped prep2 (retained)."""
	stripped = re.sub(r"--check-cfg '[^']*'", "", log)
	return [l.strip()[:200] for l in stripped.splitlines() if DIAGNOSTIC_CFG in l]


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


REFERENCE_BINARY = pathlib.Path("/home/me/work/rnx-bench-w-0178d/probes/profile-paired-0178/bin/p0-base-primary")
RETAINED = HERE / "neutrality-bin"  # untracked; the rebuilt control binary is kept here for independent replay


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert len(os.sched_getaffinity(0)) == os.cpu_count(), "builds must start unpinned"
	ledger = Ledger(out / "commands.jsonl")
	original = MANIFEST.read_text()
	res = {"rustc": subprocess.run(["rustc", "-vV"], capture_output=True, text=True, env=EB).stdout, "sources": SOURCES,
		"profiles": PROFILES, "build_order": BUILD_ORDER, "build_affinity": sorted(os.sched_getaffinity(0)),
		"manifest_sha256": sha(MANIFEST), "harness_lock_sha256": sha(HERE / "harness/Cargo.lock")}
	assert "RUSTFLAGS" not in EB and DIAGNOSTIC_CFG not in json.dumps(EB)
	# 0. Candidate scope, before anything is compiled.
	changed = subprocess.run(["git", "-C", str(FORK), "diff", "--no-color", "--name-only", SOURCES["base"], SOURCES["cand"]], capture_output=True,
		text=True, check=True, env=EB).stdout.split()
	parent = subprocess.run(["git", "-C", str(FORK), "rev-list", "--parents", "-n", "1", SOURCES["cand"]], capture_output=True,
		text=True, check=True, env=EB).stdout.split()
	res["candidate_diff"] = {"changed": changed, "production_files": [f for f in changed if f not in TEST_ONLY_FILES],
		"test_only_files": [f for f in changed if f in TEST_ONLY_FILES], "candidate_parents": parent[1:]}
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	assert res["candidate_diff"]["production_files"] == PRODUCTION_FILES, ("STOP: candidate edit surface", changed)
	assert parent[1:] == [SOURCES["base"]], ("STOP: candidate is not a single commit on the base", parent)
	# 1. Suites, once per source.
	suites = {}
	for source, rev in SOURCES.items():
		checkout(rev)
		env = {**EB, "CARGO_TARGET_DIR": str(fresh(HERE / f"test-{source}"))}
		runs = [("all-features", ["cargo", "test", "--locked", "-p", "rune", "--all-targets", "--all-features"])]
		runs.append(("production-features", ["cargo", "test", "--locked", "-p", "rune", "--lib", "--no-default-features",
			"--features", PRODUCTION_FEATURES, "--release", "compile::context", "--", "--nocapture"]))
		runs.append(("no-std", ["cargo", "check", "--locked", "--offline", "-p", "rune", "--no-default-features", "--features", "alloc"]))
		for name, argv in runs:
			# The diagnostic cfg exists for this one command only; the all-feature suite and every build run without it.
			step_env = {**env, "RUSTFLAGS": f"--cfg {DIAGNOSTIC_CFG}"} if name == "production-features" else env
			status, log, elapsed = step(out, ledger, f"suite-{source}-{name}", argv, step_env, cwd=FORK)
			passed = sum(int(m) for m in re.findall(r"test result: ok\. (\d+) passed", log))
			failed = sum(int(m) for m in re.findall(r"; (\d+) failed", log))
			suites[f"{source}-{name}"] = {"rev": rev, "status": status, "passed": passed, "failed": failed, "seconds": elapsed}
			print(source, name, suites[f"{source}-{name}"], flush=True)
		shutil.rmtree(env["CARGO_TARGET_DIR"])
	res["suites"] = suites
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	bad = {k: v for k, v in suites.items() if v["status"] != 0 or v["failed"] != 0 or (k.endswith("-no-std") is False and v["passed"] == 0)}
	assert not bad, ("STOP: suite", bad)
	# 2. Neutrality control: the unchanged 0178 harness against the tests-first base must reproduce 0178's P0 base primary.
	reference = json.loads((HISTORICAL / "subjects.json").read_text())["binaries"]["p0-base-primary"]
	historical_inputs = {str(p.relative_to(HISTORICAL)): sha(p) for p in [HISTORICAL / "harness.rs", HISTORICAL / "alloc_track.rs",
		*sorted((HISTORICAL / "harness").rglob("*"))] if p.is_file()}
	git_clean = subprocess.run(["git", "-C", str(HISTORICAL), "status", "--porcelain", "--", "harness", "harness.rs", "alloc_track.rs"],
		capture_output=True, text=True, check=True, env=EB).stdout
	assert git_clean == "", ("STOP: the historical harness is not the committed one", git_clean)
	checkout(SOURCES["base"])
	fresh(TARGET)
	argv = ["cargo", "build", "-v", "--release", "--locked", "--offline", "-j", "8", "--manifest-path", str(HISTORICAL / "harness/Cargo.toml")]
	try:
		status, log, elapsed = step(out, ledger, "build-neutrality-p0-base-primary", argv, {**EB, "CARGO_TARGET_DIR": str(TARGET)})
		assert status == 0, "STOP: neutrality build"
		got = sha(TARGET / "release/rune-base-new")
		target, _ = codegen_units(log)
		assert sha(REFERENCE_BINARY) == reference, "STOP: the retained 0178 P0 base primary no longer matches its frozen hash"
		RETAINED.mkdir(exist_ok=True)
		kept = RETAINED / f"{out.parent.name}-p0-base-primary"
		shutil.copy2(TARGET / "release/rune-base-new", kept)  # before any cleanup, whatever the comparison says
		assert sha(kept) == got
		accepted, report = neutrality.compare(kept, REFERENCE_BINARY, HISTORICAL_BASE, SOURCES["base"])
		res["neutrality"] = {"rev": SOURCES["base"], "sha256": got, "text_sha256": text_sha(TARGET / "release/rune-base-new"),
			"reference_sha256": reference, "reference_text_sha256": text_sha(REFERENCE_BINARY), "reference_rev": HISTORICAL_BASE,
			"reference": "probes/profile-paired-0178/subjects.json p0-base-primary",
			"identical": got == reference, "accepted": accepted, "comparison": report, "seconds": elapsed,
			"retained_binary": str(kept), "reference_binary": str(REFERENCE_BINARY),
			"historical_inputs": historical_inputs, "codegen_units_flags": sorted({str(v) for _, v in target}),
			"rune_features": rune_features(log)}
	finally:
		shutil.rmtree(TARGET, ignore_errors=True)
	(out / "partial.json").write_text(json.dumps(res, indent=1) + "\n")
	print("neutrality", got[:12], "reference", reference[:12], "identical" if got == reference else "differs", "accepted" if accepted else
		"NOT ACCEPTED", json.dumps(report.get("differing_bytes_by_section")), flush=True)
	assert accepted and res["neutrality"]["text_sha256"] == res["neutrality"]["reference_text_sha256"], (
		"STOP: the tests-first base is not production-neutral under the unchanged harness", report["problems"])
	# 3. One timed locked fetch, then the 6 deciding builds with the adapted harness.
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
				assert not diagnostic_cfg_uses(log), ("STOP: diagnostic cfg in a measured build", name, diagnostic_cfg_uses(log)[:3])
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
	# 5. The resident driver.
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
