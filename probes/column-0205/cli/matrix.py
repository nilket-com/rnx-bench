"""Exact production CLI captures; preflight small fixtures before any large run."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, "<RUNE_ROOT>/tools/xtask/measure")
import callgrind
import measurement_runtime as runtime
import measurement_readiness as readiness
from programs import KERNELS, fixture

def ready(lease, path):
	# Persist the exact input to the unchanged guard, including a refused snapshot.
	original = readiness.require_ready
	def recorded(observation, **limits):
		path.write_text(json.dumps({"observation": observation, "limits": limits}, indent=2) + "\n")
		return original(observation, **limits)
	readiness.require_ready = recorded
	try:
		return lease.ready(max_load=2, min_available_bytes=8 * 1024**3)
	finally:
		readiness.require_ready = original

mode = sys.argv[1]
assert mode in ("preflight", "large")
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=False)
result = {"status": "FAIL", "mode": mode, "records": []}
start = time.monotonic()
try:
	base = json.loads((HERE / "SYMBOLS.json").read_text())
	binary = Path(base["binary"])
	assert hashlib.sha256(binary.read_bytes()).hexdigest() == base["sha256"]
	assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == "cb3199b7db5eece4fd41e9610f6dcfb139c7cf26"
	assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
	pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [binary, HERE / "SYMBOLS.json", *HERE.glob("*.py")]}
	result["pins"] = pins
	vgroot = Path("<VALGRIND_ROOT>")
	result["dependencies"] = runtime.dependency_snapshot([binary, vgroot / "bin/valgrind", vgroot / "bin/vgdb", Path("/usr/bin/gdb"), Path("/usr/bin/python3")])
	result["profiler"] = runtime.tool_tree(vgroot)
	env = {"PATH": "<USER_HOME>/.cargo/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "<USER_HOME>", "LANG": "C", "LC_ALL": "C", "POLARS_MAX_THREADS": "1"}
	budget = 1000000000
	deadline = time.monotonic() + 43200
	def exact():
		for path, sha in pins.items():
			assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, path
	def validate(text, rows, layout):
		lines = [line for line in text.splitlines() if line.startswith("COLUMN_OK ")]
		assert len(lines) == 2, "both calls must complete equality checks"
		valid = rows if layout == "flat" else rows // 2
		for line in lines:
			assert f"completed=true; rows={rows}; valid_rows={valid}; attempts=1; replays=0; refusal=None" in line, line
			assert "path=avx2;" in line or "path=scalar-primitives;" in line, line
		return [int(re.search(r"\bms=(\d+) ", line)[1]) for line in lines]
	time.sleep(180)  # Fixed post-build cooldown; no readiness polling.
	with runtime.lease("/tmp/rnx-runtime-bench.lock", 2) as lease:
		for rows in ([4096] if mode == "preflight" else [10000000, 100000000]):
			for kind in KERNELS:
				for layout in ("flat", "sliced-chunked-null"):
					case = out / f"{kind}-{rows}-{layout}"
					case.mkdir()
					source = case / "program.rn"
					source.write_text(fixture(kind, rows, layout))
					row = {"kind": kind, "rows": rows, "layout": layout, "budget": budget, "fixture_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
					# Functional validation always precedes profiling this exact fixture.
					exact()
					row["direct_before"] = ready(lease, case / "DIRECT-READINESS.json")
					row["direct"] = lease.execute([str(binary), "run", "--debug-engine", "--budget", str(budget), str(source)], cwd=ROOT, env=env,
						stdout_path=case / "direct.stdout", stderr_path=case / "direct.stderr", timeout=1800, deadline=deadline)
					row["direct_after"] = readiness.snapshot(2)
					assert row["direct"]["status"] == 0, case
					assert "rnx: engine=legacy" in (case / "direct.stderr").read_text()
					row["map_elapsed_ms"] = validate((case / "direct.stdout").read_text(), rows, layout)
					row["timing_resolution_ms"] = 1
					row["thermal_stable"] = row["direct_before"]["observation"]["core_throttle_count"] == row["direct_after"]["core_throttle_count"]
					config = dict(base, out=str(case), fixture=str(source), valgrind_root=str(vgroot), calls=2, budget=budget, gdb_receipt=str(case / "GDB.json"))
					config_path = case / "CONFIG.json"
					config_path.write_text(json.dumps(config, indent=2) + "\n")
					row["profile_before"] = ready(lease, case / "PROFILE-READINESS.json")
					row["profile_execution"] = lease.execute(["/usr/bin/python3", "-B", str(HERE / "boundary_child.py"), str(config_path)], cwd=ROOT, env=env,
						stdout_path=case / "child.stdout", stderr_path=case / "child.stderr", timeout=1800, deadline=deadline)
					assert row["profile_execution"]["status"] == 0, case
					validate((case / "program.stdout").read_text(), rows, layout)
					parts = sorted(case.glob("map.callgrind.*"))
					assert len(parts) == 2, case
					row["map_Ir"] = []
					for part in parts:
						p = callgrind.parse(part)
						def cost(fragment):
							return sum(v["self_Ir"] for k, v in p["functions"].items() if fragment in k)
						assert cost("rnx_polars::column::apply_joined") > 0
						assert cost("experimental_core::column::run") > 0
						for forbidden in ("rnx::column::prepare::compile", "rnx_polars::column::script::column_kernel", "new_from_index_polars_core__series"):
							assert cost(forbidden) == 0, forbidden
						row["map_Ir"].append({"Ir": p["total_Ir"], "path": str(part), "sha256": hashlib.sha256(part.read_bytes()).hexdigest()})
					row["gdb"] = json.loads((case / "GDB.json").read_text())
					assert row["gdb"]["status"] == "PASS"
					exact()
					(case / "CAPTURE.json").write_text(json.dumps(row, indent=2) + "\n")
					result["records"].append(str(case / "CAPTURE.json"))
					time.sleep(5)
	result["status"] = "PASS"
except BaseException as error:
	result["error"] = repr(error)
	(out / "TRACEBACK.txt").write_text(traceback.format_exc())
finally:
	result["seconds"] = time.monotonic() - start
	(out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
	summary = "0205 CLI column matrix " + mode + " EXIT " + result["status"]
	notice = out / "NOTICE.txt"
	notice.write_text(summary + ". Receipt: " + str(out / "RESULT.json") + "\n")
	subprocess.run(["chatctl", "send", "--as", "sluice", "--to", "codex", "--conversation", "rune-native", "--summary", summary, "--body-file", str(notice)], check=True)
raise SystemExit(0 if result["status"] == "PASS" else 1)
