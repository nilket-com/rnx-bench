"""rnx 0176 pre-deciding dispatch diagnostic (plan rnx 084d2b4 section 4). Descriptive only: not a gate, and it cannot
revise the candidate. Run under the shared lock after semantics pass and before the deciding measurement:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 callgrind.py OUT_DIR

Exact per-function instruction attribution (callgrind Ir, which is NOT perf's native instructions:u) for three binaries
(base eaa59fc2, the 0175 candidate 863370da as a diagnostic comparator, the 0176 candidate) at the default release
profile x four workloads (context, run-fib, run-calls, run-numeric). Callgrind is deterministic, so one run each.
Retained per run: argv, status, raw stdout/stderr, callgrind.out, `callgrind_annotate` exclusive and --inclusive=yes
tables, and the binary hash. Secondary: symbol-table sizes of the dispatch loop and op_call (nm -S --size-sort), and the
presence of the outlined helper as its own symbol. A symbol that inlining removed is reported as absent, never
substituted by a guess. Environment: E0 plus VALGRIND_LIB (the user-local valgrind 3.26.0, unpacked from the distro
package without root).
"""
import json, pathlib, re, sys, time
from common import E0, sha, run_bounded
import measure

VALGRIND = pathlib.Path("/home/me/.local/opt/valgrind/usr")
EV = {**E0, "VALGRIND_LIB": str(VALGRIND / "libexec/valgrind")}
SUBJECTS = ["base", "prev", "cand"]
WORKLOADS = [w for w in measure.WORKLOADS if w[0] in ("context", "run-fib", "run-calls", "run-numeric")]
SYMBOLS = [("vm_run", r"rune::runtime::vm::Vm::run\b"), ("op_call", r"rune::runtime::vm::Vm::op_call\b"),
	("op_call_fn", r"rune::runtime::vm::Vm::op_call_fn\b"), ("op_call_associated", r"rune::runtime::vm::Vm::op_call_associated\b"),
	("try_range_next", r"rune::runtime::vm::Vm::try_range_next\b"), ("try_range_dispatch", r"rune::runtime::vm::Vm::try_range_dispatch\b")]


def lifecycle(r):
	if r.timed_out or r.interrupted or not r.reaped or r.survivors:
		raise SystemExit(("STOP: diagnostic process lifecycle", r.args, r.timed_out, r.interrupted, r.reaped, r.survivors))


def symbol_sizes(exe):
	r = run_bounded(["nm", "-S", "--size-sort", "-C", str(exe)], 120, E0)
	lifecycle(r)
	found = {}
	for line in r.stdout.splitlines():
		parts = line.split(None, 3)
		if len(parts) == 4 and parts[2] in "tTwW":
			for key, rx in SYMBOLS:
				if re.search(rx, parts[3]):
					found.setdefault(key, []).append({"symbol": parts[3], "bytes": int(parts[1], 16)})
	return {key: found.get(key, "absent (not a separate symbol in this binary)") for key, _ in SYMBOLS}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	m, bad = measure.verify_manifest(measure.MANIFEST)
	if bad:
		(out / "refused.json").write_text(json.dumps({"mismatches": bad}, indent=1) + "\n")
		raise SystemExit(("refusing: manifest mismatch", bad))
	version = run_bounded([str(VALGRIND / "bin/valgrind"), "--version"], 30, EV)
	lifecycle(version)
	res = {"started": time.time(), "valgrind": version.stdout.strip(), "valgrind_sha256": sha(VALGRIND / "bin/valgrind.bin"),
		"env": EV, "subjects": {}, "runs": {}}
	for subject in SUBJECTS:
		exe = measure.BIN / f"{subject}-primary"
		h = sha(exe)
		if h != m["binaries"][f"{subject}-primary"]:
			raise SystemExit(("STOP: binary changed", subject))
		res["subjects"][subject] = {"sha256": h, "symbols": symbol_sizes(exe)}
		for label, tail, expect in WORKLOADS:
			cg = out / f"callgrind.out.{subject}.{label}"
			argv = [str(VALGRIND / "bin/valgrind"), "--tool=callgrind", f"--callgrind-out-file={cg}", str(exe), *tail]
			r = run_bounded(argv, 1800, EV)
			row = {**r.record(), "subject": subject, "workload": label, "binary_sha256": h}
			(out / f"run.{subject}.{label}.json").write_text(json.dumps(row, indent=1) + "\n")
			lifecycle(r)
			if r.returncode != 0 or r.stdout != expect:
				raise SystemExit(("STOP: diagnostic run output", subject, label, r.returncode, r.stdout[:80]))
			total = re.search(r"Collected : (\d+)", r.stderr)
			tables = {}
			for kind, extra in (("exclusive", []), ("inclusive", ["--inclusive=yes"])):
				a = run_bounded(["perl", str(VALGRIND / "bin/callgrind_annotate"), *extra, "--threshold=99.9", str(cg)], 300, EV)
				lifecycle(a)
				(out / f"annotate-{kind}.{subject}.{label}.txt").write_text(a.stdout)
				tables[kind] = a.returncode
			res["runs"][f"{subject}/{label}"] = {"ir_total": int(total.group(1)) if total else None, "annotate_status": tables}
			print(subject, label, res["runs"][f"{subject}/{label}"]["ir_total"], flush=True)
	res["ended"] = time.time()
	(out / "callgrind.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
