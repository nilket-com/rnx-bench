"""rnx 0178 pre-check diagnostic (plan rnx 31ca480 section 3; 0176 diagnostic with a profile axis). Descriptive only: not a gate, and it cannot
revise the candidate. Run under the shared lock after semantics pass and before the deciding measurement:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 callgrind.py OUT_DIR

Primary: callgrind instruction counts (Ir) for six binaries (B, S75, S76 under P0 and P1; the primary builds of the
frozen manifest) x four workloads (context, run-fib, run-calls, run-numeric) = 24 runs; edges0178.py then replays
0177's caller-edge parser on the retained files. The counts are deterministic for this instrumented build and configuration; they are not
native instructions:u, and per-function attribution follows compiled functions, not source match arms. Secondary,
once per binary: `nm` symbol sizes and objdump disassembly of the located dispatch-loop / call symbols (static
evidence only), with direct calls inside them listed. A symbol that inlining removed is reported as absent only when
nm itself succeeded; no enclosing symbol is substituted.

Retention: every command (tool version, nm, objdump, valgrind, callgrind_annotate) goes through tool(), which appends
argv, env, cwd, status, raw stdout/stderr and lifecycle (including an interrupted command's partial record) to
commands.jsonl BEFORE anything is parsed or checked; diagnostic.json is rewritten after every command. Any tool failure
makes the diagnostic FAILED/inconclusive and stops it; it never yields an "absent" symbol or an attribution table.
"""
import json, pathlib, re, sys, time
from common import E0, SOURCES, PROFILES, sha, run_bounded
import measure

VALGRIND = pathlib.Path("/home/me/.local/opt/valgrind/usr")
EV = {**E0, "VALGRIND_LIB": str(VALGRIND / "libexec/valgrind")}
TOOLS = {"valgrind": str(VALGRIND / "bin/valgrind"), "annotate": str(VALGRIND / "bin/callgrind_annotate"), "perl": "/usr/bin/perl",
	"nm": "/usr/bin/nm", "objdump": "/usr/bin/objdump"}
SUBJECTS = [f"{p}-{s}" for p in PROFILES for s in SOURCES]
WORKLOADS = [w for w in measure.WORKLOADS if w[0] in ("context", "run-fib", "run-calls", "run-numeric")]
# v0 symbol mangling (this toolchain): demangled names read "<rune::runtime::vm::Vm>::run". Exact matches only, so
# closures such as "::try_range_dispatch::{closure#2}" are not counted as the function itself.
SYMBOLS = [(name, rf"^<rune::runtime::vm::Vm>::{name}$") for name in
	("run", "op_call", "op_call_fn", "op_call_associated", "try_range_next", "try_range_dispatch")]


class DiagnosticFailure(Exception):
	pass


class Recorder:
	def __init__(self, out):
		self.out = out
		self.log = (out / "commands.jsonl").open("a")
		self.summary = {"status": "running", "started": time.time(), "env": EV, "tools": {}, "subjects": {}, "runs": {}}
		self.save()

	def save(self):
		(self.out / "diagnostic.json").write_text(json.dumps(self.summary, indent=1) + "\n")

	def tool(self, argv, timeout, env, meta):
		"""Run one bounded command; persist its full record (or the interrupted partial) before returning it."""
		row = {**meta, "argv": argv, "env": env, "cwd": str(pathlib.Path.cwd())}
		try:
			r = run_bounded(argv, timeout, env)
		except BaseException as error:
			row.update(getattr(error, "partial", {}), exception=repr(error))
			self.log.write(json.dumps(row) + "\n")
			self.log.flush()
			raise
		row.update(r.record())
		self.log.write(json.dumps(row) + "\n")
		self.log.flush()
		return row


def ok(row, what):
	"""After retention: a clean lifecycle and status 0, or the diagnostic fails."""
	if row["timed_out"] or row["interrupted"] or row["reaped"] is not True or row["group_survivors"]:
		raise DiagnosticFailure((what, "lifecycle", row["argv"]))
	if row["status"] != 0:
		raise DiagnosticFailure((what, "status", row["status"], row["stderr"][-300:]))


def symbol_table(rec, exe, subject):
	row = rec.tool([TOOLS["nm"], "-S", "--size-sort", "-C", str(exe)], 120, E0, {"kind": "nm", "subject": subject})
	(rec.out / f"nm.{subject}.txt").write_text(row["stdout"])
	ok(row, ("nm", subject))
	found = {}
	for line in row["stdout"].splitlines():
		parts = line.split(None, 3)
		if len(parts) == 4 and parts[2] in "tTwW":
			for key, rx in SYMBOLS:
				if re.search(rx, parts[3]):
					found.setdefault(key, []).append({"symbol": parts[3], "address": int(parts[0], 16), "bytes": int(parts[1], 16)})
	return {key: found.get(key, "absent (nm succeeded; not a separate symbol in this binary)") for key, _ in SYMBOLS}


def disassemble(rec, exe, subject, symbols):
	"""objdump of each located symbol's exact address range, with the direct calls it contains listed."""
	result = {}
	for key, entries in symbols.items():
		if not isinstance(entries, list):
			continue
		for i, e in enumerate(entries):
			argv = [TOOLS["objdump"], "-d", "-C", "--no-show-raw-insn", f"--start-address={e['address']:#x}",
				f"--stop-address={e['address'] + e['bytes']:#x}", str(exe)]
			row = rec.tool(argv, 300, E0, {"kind": "objdump", "subject": subject, "symbol": e["symbol"]})
			(rec.out / f"objdump.{subject}.{key}.{i}.txt").write_text(row["stdout"])
			ok(row, ("objdump", subject, key))
			calls = sorted(set(re.findall(r"\bcall\s+[0-9a-f]+\s+<([^>]+)>", row["stdout"])))
			result[f"{key}.{i}"] = {"symbol": e["symbol"], "bytes": e["bytes"], "instructions": len(re.findall(r"^\s+[0-9a-f]+:\s", row["stdout"], re.M)),
				"direct_calls": calls}
	return result


def annotate(rec, cg, subject, label):
	"""Exclusive and inclusive callgrind_annotate tables; each output is saved before its status is checked."""
	tables = {}
	for kind, extra in (("exclusive", []), ("inclusive", ["--inclusive=yes"])):
		a = rec.tool([TOOLS["perl"], TOOLS["annotate"], *extra, "--threshold=99.9", str(cg)], 300, EV,
			{"kind": "annotate", "table": kind, "subject": subject, "workload": label})
		(rec.out / f"annotate-{kind}.{subject}.{label}.txt").write_text(a["stdout"])
		ok(a, ("annotate", kind, subject, label))
		tables[kind] = f"annotate-{kind}.{subject}.{label}.txt"
	return tables


def check_callgrind_file(path, collected):
	"""The output file must exist, record the Ir event and carry a positive summary equal to the collected total."""
	if not path.exists():
		raise DiagnosticFailure(("callgrind output missing", str(path)))
	text = path.read_text(errors="replace")
	if not re.search(r"^events:\s+Ir\s*$", text, re.M):
		raise DiagnosticFailure(("callgrind output lacks the Ir event", str(path)))
	m = re.search(r"^(?:summary|totals):\s+(\d+)\s*$", text, re.M)
	if not m or int(m.group(1)) <= 0:
		raise DiagnosticFailure(("callgrind summary missing or not positive", str(path)))
	if collected is None or int(m.group(1)) != collected:
		raise DiagnosticFailure(("callgrind summary differs from the collected total", int(m.group(1)), collected))
	return int(m.group(1))


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	m, bad = measure.verify_manifest(measure.MANIFEST)
	if bad:
		(out / "refused.json").write_text(json.dumps({"mismatches": bad}, indent=1) + "\n")
		raise SystemExit(("refusing: manifest mismatch", bad))
	rec = Recorder(out)
	try:
		for name, argv, env in (("valgrind", [TOOLS["valgrind"], "--version"], EV), ("nm", [TOOLS["nm"], "--version"], E0),
				("objdump", [TOOLS["objdump"], "--version"], E0), ("perl", [TOOLS["perl"], "-v"], E0)):
			row = rec.tool(argv, 30, env, {"kind": "version", "tool": name})
			ok(row, ("version", name))
			rec.summary["tools"][name] = {"version": row["stdout"].strip().splitlines()[0] if row["stdout"].strip() else row["stdout"],
				"path": argv[0], "sha256": sha(argv[0] if name != "valgrind" else VALGRIND / "bin/valgrind.bin")}
			rec.save()
		for subject in SUBJECTS:
			exe = measure.BIN / f"{subject}-primary"
			h = sha(exe)
			if h != m["binaries"][f"{subject}-primary"]:
				raise DiagnosticFailure(("binary changed", subject))
			symbols = symbol_table(rec, exe, subject)
			rec.summary["subjects"][subject] = {"sha256": h, "symbols": symbols}
			rec.save()
			rec.summary["subjects"][subject]["disassembly"] = disassemble(rec, exe, subject, symbols)
			rec.save()
			for label, tail, expect in WORKLOADS:
				cg = out / f"callgrind.out.{subject}.{label}"
				row = rec.tool([TOOLS["valgrind"], "--tool=callgrind", f"--callgrind-out-file={cg}", str(exe), *tail], 1800, EV,
					{"kind": "callgrind", "subject": subject, "workload": label, "binary_sha256": h})
				ok(row, ("callgrind", subject, label))
				if row["stdout"] != expect:
					raise DiagnosticFailure(("workload output", subject, label, row["stdout"][:80]))
				collected = re.search(r"Collected : (\d+)", row["stderr"])
				total = check_callgrind_file(cg, int(collected.group(1)) if collected else None)
				rec.summary["runs"][f"{subject}/{label}"] = {"ir_total": total, "tables": annotate(rec, cg, subject, label)}
				rec.save()
				print(subject, label, total, flush=True)
		rec.summary["status"] = "complete"
	except BaseException as error:
		rec.summary["status"] = "FAILED (inconclusive)"
		rec.summary["failure"] = repr(error)
		raise
	finally:
		rec.summary["ended"] = time.time()
		rec.save()


if __name__ == "__main__":
	main(sys.argv[1])
