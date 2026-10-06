"""rnx 0179: freeze the reviewed subject manifest (subjects.json) from an accepted build receipt, without rebuilding.
Binds all SIX artifacts (2 sources x P0 x 3 kinds), both sources' receipts and the neutrality control.

	python3 freeze.py RESULTS_RUN_DIR      # e.g. ../../results/startup-0179/prep1

Binds the source revisions, the six harness binaries, the resident driver (source and binary), the actual rune feature
set, the build receipt itself, the inventory receipts (both inventory tests passed on base and candidate; the golden
blob is the same at all three revisions), the harness/fixture/oracle/Lua inputs and the Lua binaries. measure.py refuses to
start unless every one of these still matches.
"""
import json, pathlib, re, subprocess, sys
from common import HERE, FORK, SOURCES, PRODUCTION_PARENT, PROFILES, KINDS, EB, sha, digest_tree

# The four goldens frozen on the base (doc and production-feature inventories, doc and production-feature
# registration order). Their blobs must be identical at base and candidate: the candidate may not regenerate them.
GOLDENS = ["crates/rune/src/compile/context_inventory.golden", "crates/rune/src/compile/context_inventory_nodoc.golden",
	"crates/rune/src/compile/context_startup_order.golden", "crates/rune/src/compile/context_startup_order_nodoc.golden",
	"crates/rune/src/compile/startup_fixtures/first-use-stdio.rn", "crates/rune/src/compile/startup_fixtures/first-use.rn"]
# Base contract tests: must pass on both sources under BOTH the all-feature suite and the production feature set.
INVENTORY_TESTS = ["compile::context::inventory_tests::registered_inventory_matches_the_golden",
	"compile::context::inventory_tests::inventory_comparison_detects_changes",
	"compile::context::startup_tests::item_display_bytes_are_frozen_before_the_candidate",
	"compile::context::startup_tests::registration_order_matches_the_base",
	"compile::context::startup_tests::custom_associated_constant_values_and_errors_are_unchanged",
	"compile::context::startup_tests::every_module_first_use_completes_with_and_without_stdio"]
SUITES = ["all-features", "production-features"]
LUA = {"lua54": "/home/me/.local/bin/lua54", "luajit": "/home/me/.local/bin/luajit"}
INPUTS = ["harness/Cargo.toml", "harness/Cargo.lock", "harness/src/*.rs", "harness.rs", "alloc_track.rs", "plan_clock.rs",
	"SOURCES-fb56b1d.sha256", "oracle.py", "corpus/*.rn", "fixtures/*.rn", "fixtures/manifest.json", "range/*.rn", "lua/*.lua"]


def expected_keys():
	return {f"{p}-{s}-{k}" for p in PROFILES for s in SOURCES for k in KINDS}


def identity_problems(manifest, build):
	"""Profile-axis identity: the frozen profile definitions, exactly the 18 artifact names in both the manifest and
	the build receipt, and every receipt row's profile/source/kind/rev and recorded profile section and codegen-units
	result agreeing with its own key and the constants. Returns a list of problems (empty = consistent)."""
	bad = []
	if manifest.get("profiles") != PROFILES:
		bad.append(("manifest profile definitions differ from the frozen PROFILES", manifest.get("profiles")))
	if build.get("profiles") != PROFILES:
		bad.append(("build receipt profile definitions differ from the frozen PROFILES", build.get("profiles")))
	want = expected_keys()
	for where, keys in (("manifest binaries", set(manifest.get("binaries", {}))), ("build receipt", set(build.get("builds", {})))):
		if keys != want:
			bad.append((f"{where}: artifact names", {"missing": sorted(want - keys), "extra": sorted(keys - want)}))
	for key, row in build.get("builds", {}).items():
		if key not in want:
			continue
		profile, source, kind = key.split("-", 2)
		expect_section = "\n" + "\n".join(["opt-level = 3", *PROFILES[profile]]) + "\n"
		expect_cgu = "1 on every target invocation" if PROFILES[profile] else "default (no flag) on every target invocation"
		got = (row.get("profile"), row.get("source"), row.get("kind"), row.get("rev"), row.get("manifest_profile_section"), row.get("codegen_units"))
		if got != (profile, source, kind, SOURCES[source], expect_section, expect_cgu):
			bad.append(("row identity", key, got))
		if manifest.get("binaries", {}).get(key) != row.get("sha256"):
			bad.append(("manifest hash differs from the receipt row", key))
	return bad


def inputs_digest():
	return digest_tree(HERE, INPUTS)


def main(run):
	run = pathlib.Path(run).resolve()
	build_json = run / "build/build.json"
	build = json.loads(build_json.read_text())
	assert build["sources"] == SOURCES, "build receipt is for other sources"
	binaries = {}
	for name, row in build["builds"].items():
		path = HERE / "bin" / name
		assert sha(path) == row["sha256"], ("binary no longer matches its build receipt", name)
		binaries[name] = row["sha256"]
	assert set(binaries) == expected_keys(), "artifact names"
	assert sha(HERE / "clock/plan_clock") == build["clock"]["sha256"]
	inventory = {}
	for subject in SOURCES:
		for suite in SUITES:
			log_path = run / f"build/suite-{subject}-{suite}.log"
			log = log_path.read_text()
			passed = {t: bool(re.search(rf"^test {re.escape(t)} \.\.\. ok$", log, re.M)) for t in INVENTORY_TESTS}
			assert all(passed.values()), (subject, suite, passed)
			inventory[f"{subject}-{suite}"] = {"log": str(log_path.relative_to(HERE.parents[1])), "log_sha256": sha(log_path), "tests_passed": passed}
	blobs = {g: {s: subprocess.run(["git", "-C", str(FORK), "rev-parse", f"{rev}:{g}"], capture_output=True, text=True, check=True,
		env=EB).stdout.strip() for s, rev in SOURCES.items()} for g in GOLDENS}
	assert all(len(set(v.values())) == 1 for v in blobs.values()), ("a frozen golden or fixture differs between sources", blobs)
	fixture_blobs = {name: subprocess.run(["git", "hash-object", str(HERE / "fixtures" / name)], capture_output=True, text=True, check=True,
		env=EB).stdout.strip() for name in ("first-use-stdio.rn", "first-use.rn")}
	for name, blob in fixture_blobs.items():
		assert blob == blobs[f"crates/rune/src/compile/startup_fixtures/{name}"]["base"], ("bench fixture differs from the fork's copy", name)
	neutrality = build["neutrality"]
	assert neutrality["identical"] is True and neutrality["sha256"] == neutrality["reference_sha256"], ("neutrality control", neutrality)
	assert build["candidate_diff"]["production_files"] == ["crates/rune/src/compile/context.rs"], build["candidate_diff"]
	manifest = {
		"sources": SOURCES, "production_parent": PRODUCTION_PARENT,
		"build_receipt": {"path": str(build_json.relative_to(HERE.parents[1])), "sha256": sha(build_json)},
		"binaries": binaries,
		"clock": build["clock"],
		"profiles": PROFILES,
		"rune_features": build["builds"]["p0-base-primary"]["rune_features"],
		"inventory": {"golden_blobs": {g: v["base"] for g, v in blobs.items()}, "receipts": inventory},
		"neutrality": neutrality, "candidate_diff": build["candidate_diff"],
		"inputs": inputs_digest(),
		"lua": {k: {"path": v, "sha256": sha(v)} for k, v in LUA.items()},
	}
	assert "tracing" not in manifest["rune_features"]
	problems = identity_problems(manifest, build)
	assert not problems, ("refusing to freeze an inconsistent manifest", problems)
	(HERE / "subjects.json").write_text(json.dumps(manifest, indent=1) + "\n")
	print("frozen", len(binaries), "binaries,", len(manifest["inputs"]), "inputs; features", manifest["rune_features"])


if __name__ == "__main__":
	main(sys.argv[1])
