"""rnx 0170 N1: allocation counts per workload on the unmodified 0168 `allocation` binaries (counting allocator).

	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 alloc.py OUT_DIR

The harness prints `ALLOC (calls, allocated_bytes, live_bytes, peak_bytes)` on stderr for the whole process,
including context construction and compile. `compile` mode on the same file gives the startup part; run - compile
is net run-path allocation, stated as such (not an exclusive execution phase).
"""
import ast, hashlib, json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import EXPECT, binary, kernel, held_lock, sha

WORKS = ["empty", "answer", "numeric", "while", "fib", "calls", "compare", "vector", "strings"]
HASHES = {"old": "d0dfe6428efbd75c", "new": "3380abd68a3ec38a"}  # results/rune-base-0168/conditions.json


def alloc(exe, mode, work):
	r = subprocess.run([exe, mode, str(kernel(work))], capture_output=True, text=True, timeout=300)
	assert r.returncode == 0, (mode, work, r.stderr[-300:])
	lines = r.stderr.splitlines()
	assert lines and lines[-1].startswith("ALLOC ") and len(lines) == 1, (mode, work, r.stderr[-300:])
	if mode == "run":
		assert r.stdout == EXPECT[work], (work, r.stdout[:100])
	a = ast.literal_eval(lines[-1][6:])
	return {"calls": a[0], "allocated_bytes": a[1], "live_bytes": a[2], "peak_bytes": a[3]}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under the shared lock"
	res = {"subjects": {}, "workloads": {}}
	for base in ("old", "new"):
		exe = binary(base, "allocation")
		h = sha(exe)
		assert h.startswith(HASHES[base]), (base, h)
		res["subjects"][base] = {"path": str(exe), "sha256": h}
		for w in WORKS:
			c = alloc(str(exe), "compile", w)
			r = alloc(str(exe), "run", w)
			again = alloc(str(exe), "run", w)
			assert again["calls"] == r["calls"], (base, w, "allocation count not deterministic", r, again)
			res["workloads"][f"{base}-{w}"] = {"compile": c, "run": r, "run_minus_compile_calls": r["calls"] - c["calls"]}
			print(base, w, "compile", c["calls"], "run", r["calls"], "net run-path", r["calls"] - c["calls"], flush=True)
	(out / "alloc.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
