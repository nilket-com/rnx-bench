"""Signed-production map-boundary control before large performance captures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, "<RUNE_ROOT>/tools/xtask/measure")
import callgrind
import measurement_runtime as runtime

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
result = {"status": "FAIL"}
pins = {}
started = time.monotonic()
try:
	config = json.loads((HERE / "SYMBOLS.json").read_text())
	binary = Path(config["binary"])
	assert hashlib.sha256(binary.read_bytes()).hexdigest() == config["sha256"]
	assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == "cb3199b7db5eece4fd41e9610f6dcfb139c7cf26"
	assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
	fixture = ROOT / "tools/column/fixtures/cli-map.rn"
	for path in [binary, fixture, HERE / "SYMBOLS.json", *HERE.glob("*.py")]:
		pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
	result["pins"] = pins
	vgroot = Path("<VALGRIND_ROOT>")
	result["dependencies"] = runtime.dependency_snapshot([binary, vgroot / "bin/valgrind", vgroot / "bin/vgdb", Path("/usr/bin/gdb"), Path("/usr/bin/python3")])
	result["profiler"] = runtime.tool_tree(vgroot)
	config.update(out=str(out), fixture=str(fixture), valgrind_root=str(vgroot), calls=1, gdb_receipt=str(out / "GDB.json"))
	config_path = out / "CONFIG.json"
	config_path.write_text(json.dumps(config, indent=2) + "\n")
	env = {"PATH": "<USER_HOME>/.cargo/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "<USER_HOME>", "LANG": "C", "LC_ALL": "C", "POLARS_MAX_THREADS": "1"}
	# Fixed post-build cooldown, not a status/progress watcher.
	time.sleep(180)
	with runtime.lease("/tmp/rnx-runtime-bench.lock", 2) as lease:
		result["readiness"] = lease.ready(max_load=2, min_available_bytes=8 * 1024**3)
		result["execution"] = lease.execute(["/usr/bin/python3", "-B", str(HERE / "boundary_child.py"), str(config_path)], cwd=ROOT, env=env,
			stdout_path=out / "child.stdout", stderr_path=out / "child.stderr", timeout=720, deadline=time.monotonic() + 750)
	assert result["execution"]["status"] == 0, "boundary child failed"
	text = (out / "program.stdout").read_text()
	assert "COLUMN_OK" in text and "completed=true; rows=10000; valid_rows=10000;" in text
	assert "COLUMN_CAUGHT" not in text
	assert "rnx: engine=legacy" in (out / "program.stderr").read_text()
	parts = sorted(out.glob("map.callgrind.*"))
	assert len(parts) == 1, [str(p) for p in parts]
	profile = callgrind.parse(parts[0])
	functions = profile["functions"]
	def cost(fragment):
		return sum(v["self_Ir"] for k, v in functions.items() if fragment in k)
	worker = cost("rnx_polars::column::apply_joined")
	kernel = cost("experimental_core::column::run")
	assert worker > 0 and kernel > 0, "joined worker or kernel missing from profile"
	for forbidden in ("rnx::column::prepare::compile", "rnx_polars::column::script::column_kernel", "new_from_index_polars_core__series"):
		assert cost(forbidden) == 0, "setup leaked into map interval: " + forbidden
	result.update(total_map_Ir=profile["total_Ir"], worker_self_Ir=worker, kernel_self_Ir=kernel,
		gdb=json.loads((out / "GDB.json").read_text()), profile=str(parts[0]), profile_sha256=hashlib.sha256(parts[0].read_bytes()).hexdigest())
	(out / "PROFILE.json").write_text(json.dumps(profile, indent=2) + "\n")
	for path, digest in pins.items():
		assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
	result["status"] = "PASS"
except BaseException as error:
	result["error"] = repr(error)
	(out / "TRACEBACK.txt").write_text(traceback.format_exc())
finally:
	result["seconds"] = time.monotonic() - started
	(out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
	summary = "0205 signed CLI map-boundary control EXIT " + result["status"]
	notice = out / "NOTICE.txt"
	notice.write_text(summary + ". Receipt: " + str(out / "RESULT.json") + "\n")
	subprocess.run(["chatctl", "send", "--as", "sluice", "--to", "codex", "--conversation", "rune-native", "--summary", summary, "--body-file", str(notice)], check=True)
raise SystemExit(0 if result["status"] == "PASS" else 1)
