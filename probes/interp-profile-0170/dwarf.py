"""rnx 0170 step C: DWARF call-graph pass, classification only (startup/registration vs compile vs VM run).

	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 dwarf.py STEP_B_DIR OUT_DIR

One repeat per engine x workload with the step-B instruction-event invocation count. Each sample is classified by its
unwound stack (innermost to outermost; the first marker found from the OUTERMOST frame inward decides):
	run: a frame of Vm::run / Vm::call / Vm::execute / Vm::complete / VmExecution
	registration: Context::with_config / with_default_modules / Context::install / Module construction
	compile: rune::prepare / Build::build / rune::compile
	unclassified: anything else, including failed unwinds (kept in the denominator).
These shares are never used as decomposition weights; >10% unclassified marks a workload's split insufficient.
"""
import collections, json, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import EXPECT, binary, kernel, held_lock

PERIOD = 1000000
WORKS = ["numeric", "while", "fib", "calls", "compare", "vector", "strings", "answer"]
MARKERS = [
	("run", re.compile(r"<rune::runtime::vm::Vm>::(run|call|execute|complete)|VmExecution|vm_call|Vm>::call_")),
	("registration", re.compile(r"Context>::(with_config|with_default_modules|install)|modules::[a-z_]+::module|Module>::")),
	("compile", re.compile(r"rune::prepare|Build<.*>::build|Build>::build|rune::compile::compile|compile::v1|rune::build")),
]


def classify(frames):
	for frame in reversed(frames):  # outermost first
		for name, rx in MARKERS:
			if rx.search(frame):
				return name
	return "unclassified"


def main(step_b, out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under the shared lock"
	plan = json.loads((pathlib.Path(step_b) / "plan.json").read_text())["invocations_per_repeat"]
	ledger = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	result = {}
	for base in ("old", "new"):
		exe = str(binary(base, "s2"))
		for w in WORKS:
			n = plan[f"{base}-{w}-instructions"]
			data = out / f"{base}-{w}.data"
			outfile = out / f"{base}-{w}.stdout"
			loop = f'for i in $(seq {n}); do "$0" run "$1"; done > "$2"'
			r = subprocess.run(["taskset", "-c", "4", "perf", "record", "-q", "-e", "cpu_core/instructions/u", "-c", str(PERIOD),
				"--call-graph", "dwarf,16384", "-o", str(data), "--", "bash", "-c", loop, exe, str(kernel(w)), str(outfile)],
				capture_output=True, text=True, timeout=900)
			assert r.returncode == 0, r.stderr[-500:]
			assert outfile.read_text() == EXPECT[w] * n
			outfile.unlink()
			s = subprocess.run(["perf", "script", "-i", str(data), "-F", "comm,ip,sym", "--no-inline"], capture_output=True, text=True, timeout=900)
			assert s.returncode == 0, s.stderr[-500:]
			counts = collections.Counter()
			frames = []
			comm_ok = False
			for line in s.stdout.splitlines() + [""]:
				if not line.strip():
					if frames or comm_ok:
						counts[classify(frames)] += 1
					frames, comm_ok = [], False
					continue
				if not line.startswith((" ", "\t")):
					comm_ok = True  # sample header line
					continue
				frames.append(line.strip())
			total = sum(counts.values())
			stats = subprocess.run(["perf", "report", "-i", str(data), "--stats"], capture_output=True, text=True).stdout
			lost = sum(int(x) for x in re.findall(r"LOST(?:_SAMPLES)? events:\s+(\d+)", stats))
			throttle = sum(int(x) for x in re.findall(r"THROTTLE events:\s+(\d+)", stats))
			share = {k: v / total for k, v in counts.items()}
			result[f"{base}-{w}"] = {"invocations": n, "samples": total, "counts": dict(counts), "shares": share,
				"unclassified_share": share.get("unclassified", 0.0), "split_sufficient": share.get("unclassified", 0.0) <= 0.10,
				"lost": lost, "throttle": throttle}
			data.unlink()  # large; the classification and counts are what's retained
			print(base, w, total, {k: round(v * 100, 1) for k, v in share.items()}, "lost", lost, "throttle", throttle, flush=True)
	ledger.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	(out / "dwarf.json").write_text(json.dumps({"period": PERIOD, "markers": [(n, r.pattern) for n, r in MARKERS], "result": result, "ledger": ledger}, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])
