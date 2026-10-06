"""rnx 0176: freeze the reviewed subject manifest (subjects.json) from an accepted build receipt, without rebuilding.

	python3 freeze.py RESULTS_RUN_DIR      # e.g. ../../results/range-iteration-0176/rehearsal1

Binds the source revisions, the six harness binaries, the resident driver (source and binary), the actual rune feature
set, the build receipt itself, the inventory receipts (both inventory tests passed on base and candidate; the golden
blob is the same at both revisions), the harness/fixture/oracle/Lua inputs and the Lua binaries. measure.py refuses to
start unless every one of these still matches.
"""
import json, pathlib, re, subprocess, sys
from common import HERE, FORK, SOURCES, PRODUCTION_PARENT, EB, sha, digest_tree

GOLDEN = "crates/rune/src/compile/context_inventory.golden"
INVENTORY_TESTS = ["compile::context::inventory_tests::registered_inventory_matches_the_golden",
	"compile::context::inventory_tests::inventory_comparison_detects_changes"]
LUA = {"lua54": "/home/me/.local/bin/lua54", "luajit": "/home/me/.local/bin/luajit"}
INPUTS = ["harness/Cargo.toml", "harness/Cargo.lock", "harness/src/*.rs", "harness.rs", "alloc_track.rs", "plan_clock.rs",
	"SOURCES-fb56b1d.sha256", "oracle.py", "corpus/*.rn", "fixtures/*.rn", "range/*.rn", "lua/*.lua"]


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
	assert sorted(binaries) == sorted([f"{s}-{k}" for s in ("base", "cand") for k in ("primary", "counter", "allocation")] + ["prev-primary"])
	assert sha(HERE / "clock/plan_clock") == build["clock"]["sha256"]
	inventory = {}
	for subject in ("base", "cand"):
		log_path = run / f"build/suite-{subject}-all-features.log"
		log = log_path.read_text()
		passed = {t: bool(re.search(rf"^test {re.escape(t)} \.\.\. ok$", log, re.M)) for t in INVENTORY_TESTS}
		assert all(passed.values()), (subject, passed)
		inventory[subject] = {"log": str(log_path.relative_to(HERE.parents[1])), "log_sha256": sha(log_path), "tests_passed": passed}
	blobs = {s: subprocess.run(["git", "-C", str(FORK), "rev-parse", f"{rev}:{GOLDEN}"], capture_output=True, text=True, check=True,
		env=EB).stdout.strip() for s, rev in SOURCES.items()}
	assert blobs["base"] == blobs["cand"], ("inventory golden differs between subjects", blobs)
	manifest = {
		"sources": SOURCES, "production_parent": PRODUCTION_PARENT,
		"build_receipt": {"path": str(build_json.relative_to(HERE.parents[1])), "sha256": sha(build_json)},
		"binaries": binaries,
		"clock": build["clock"],
		"rune_features": build["builds"]["base-primary"]["rune_features"],
		"inventory": {"golden_path": GOLDEN, "golden_blob": blobs["base"], "receipts": inventory},
		"inputs": inputs_digest(),
		"lua": {k: {"path": v, "sha256": sha(v)} for k, v in LUA.items()},
	}
	assert "tracing" not in manifest["rune_features"]
	(HERE / "subjects.json").write_text(json.dumps(manifest, indent=1) + "\n")
	print("frozen", len(binaries), "binaries,", len(manifest["inputs"]), "inputs; features", manifest["rune_features"])


if __name__ == "__main__":
	main(sys.argv[1])
