"""rnx 0170 step D (substitute for the failed DWARF split): deterministic whole-process instruction counts on the
unmodified primary binaries for `compile` mode (context + compile, no execution) vs `run` mode on the same file.
run - compile = instructions attributable to execution plus teardown of the run's values (stated, not hidden).

	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 split.py OUT_DIR
"""
import json, pathlib, statistics, subprocess, sys, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import EXPECT, binary, kernel, held_lock, perf_stat, parse_stat

WORKS = ["numeric", "while", "fib", "calls", "compare", "vector", "strings", "answer", "empty"]


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under the shared lock"
	ledger = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	res = {}
	for base in ("old", "new"):
		exe = str(binary(base, "primary"))
		for w in WORKS:
			row = {}
			for mode in ("compile", "run"):
				vals = []
				for _ in range(5):
					r = perf_stat([exe, mode, str(kernel(w))])
					assert r.returncode == 0, (base, w, mode, r.stderr[-300:])
					if mode == "run":
						assert r.stdout == EXPECT[w], (base, w, r.stdout[:100])
					else:
						assert r.stdout == "", (base, w, "compile printed", r.stdout[:100])
					vals.append(parse_stat(r.stderr)["instructions"])
				row[mode] = {"values": vals, "median": statistics.median(vals), "spread": (max(vals) - min(vals)) / statistics.median(vals)}
			row["run_minus_compile"] = row["run"]["median"] - row["compile"]["median"]
			res[f"{base}-{w}"] = row
			print(base, w, f"compile {row['compile']['median'] / 1e6:.2f}M run {row['run']['median'] / 1e6:.2f}M exec {row['run_minus_compile'] / 1e6:.2f}M", flush=True)
	ledger.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	(out / "split.json").write_text(json.dumps({"result": res, "ledger": ledger}, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
