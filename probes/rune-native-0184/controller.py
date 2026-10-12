#!/usr/bin/env python3
"""FUEL probe: controller (rnx 0184), revision "fuel" of the P2 probe controller: revision r3's
design (the R3 probe, ../../0184-r3-probe1, = revision 6's design with the ctl4 launch and
validation safeguards) with the FUEL subject. Wall-clock only; no perf pass.

Revision fuel (Codex GO 8330, ../CODEX-GO-8330.txt) changes, relative to revision r3, ONLY:

- Subjects fuel-on, fuel-off, built ONCE each from 346623b6 (FUEL, branch fuel/guarded-fold,
  sole parent e1e1f30b R1; NOT built on R3 088d8245), pinned by sha256 and X_OK (PINS.json).
  The header's `probe` field names revision "fuel", so no revision-r3, revision-6, ctl4 or
  stage-2 raw file can bind. Step 0 / nm subject names; one more recorded-only nm substring
  (`fuel_tests`, FUEL's #[cfg(test)] module experimental_native::fuel_tests).
- The pre-registered mappings are unchanged in shape (calls 451 -> 721 code bytes is still one
  4 KiB page); the comments name the FUEL release listing.
- Every mechanism of revision r3 below is unchanged.

Revision r3 (Codex GO 8294, ../../0184-r3-probe1/CODEX-GO-8294.txt) changed, relative to revision 6:

- Subjects r3-on, r3-off, built ONCE each from 088d8245 (R3, parent e1e1f30b R1), pinned by
  sha256 and X_OK (PINS.json). The header's `probe` field names revision "r3", so no revision-6
  (R2), ctl4 or stage-2 raw file can bind. Step 0 / nm subject names; one more recorded-only nm
  substring (`r3_tests`, R3's #[cfg(test)] module experimental_native::r3_tests).
- Pins (ctl4): both subjects need X_OK; the worktree must be clean at the commit with the pinned
  tree and the pinned workspace lock; git runs with colour off and stdin /dev/null.
- Step 1 (stricter, ctl4): every Rune transcript's MAPS count must equal the pre-registered
  mapping for its (subject, kernel); the whole stdout hashes are recorded beside the compared
  result+checksum hashes.
- Blocks record their within-round `position` (= block index); the schedule is asserted against
  MAX_ROUNDS / MAX_BLOCKS / MAX_CHILDREN (60 / 200 / 400).
- `run` refuses (rc 1, nothing runs) a seed other than the sealed SESSION-SEED.txt.
- The cells, K1/K2, ROUNDS, bounds, schedule mechanics and every fail-closed mechanism of
  revision 6 are unchanged. Decision rules live in analyze.py (calls the SOLE PRIMARY for R_jit;
  while and numeric CURRENT ACCEPTANCE SCREENS; fib/shared_rows controls upper <= 1.01; bare
  LuaJIT the primary comparator, luajit -joff the secondary).

Revision 6 (Codex GO 8173) changed ONLY the subjects (r2-on, r2-off), the Step 0 / nm subject
names, the recorded-only nm substring `r2_tests`, the header's `probe` field and the wording.

Revision 5 (Codex GO 8137) changed ONLY the subjects (r1-on, r1-off, built from e1e1f30b R1),
the Step 0 / nm subject names, one recorded-only nm substring (`r1_tests`), the header's
`probe` field and the wording.

Revision 4 (Codex GO 8101) changed ONLY the subjects (w13-on, w13-off, built from 0765cce6
W13), the Step 0 / nm subject names, one recorded-only nm substring (`w13_tests`), the header's
`probe` field and the wording.

Revision 3 (CALLS-PROBE-PLAN.md with Codex GO 8052) changed ONLY the subjects (b1-on,
b1-off), the cell table, the Step 0 expectations, the nm symbol lists, the LuaJIT trace
diagnostic kernel (calls) and the bound estimates. Every fail-closed mechanism of revision 2
(all-phases deadline, per-child SIGKILL timeout, explicit validity, footer, rc) is unchanged.

usage:
  controller.py schedule SEED            print the sealed schedule and its bounds; run nothing
  controller.py validate OUT_DIR [--max-k N]
                                         Steps 0-1 (admission evidence, transcripts, checksums,
                                         nm, environment); records NO timing. --max-k caps every
                                         K for a dry run of the controller itself (labelled).
  controller.py run OUT_DIR SEED         Steps 0-1 at full K, then the timed session (Step 2).
                                         HELD: runs only after review and an explicit GO.
                                         SEED must equal the sealed SESSION-SEED.txt.

Run it as (../LAUNCH-COMMANDS.txt has the exact argv):
  flock /tmp/rnx-runtime-bench.lock env -u PERF_BUILDID_DIR python3 -I -B controller.py ...  </dev/null

Design (P2-PROBE-PLAN.md with Codex's corrections, CODEX-GO-7954; revision 3:
CALLS-PROBE-PLAN.md with CODEX-GO-8052; revision 4: CODEX-GO-8101; revision 5: CODEX-GO-8137;
revision 6: CODEX-GO-8173; revision r3: CODEX-GO-8294; revision fuel: CODEX-GO-8330):

- Subjects: bare `luajit` (headline and primary comparator, real defaults), `luajit -joff`
  (secondary comparator), `fuel-on`, `fuel-off`. No -O3 subject. A CURRENT ACCEPTANCE SCREEN of
  the FUEL binaries: no R1 (or R3, R2, W13, B1) binary is a subject, so nothing here is a paired
  FUEL-vs-R1 (or FUEL-vs-R3) estimate.
- Cells: calls/calls_main (the SOLE PRIMARY for the LuaJIT target), while/loop_main and
  numeric/loop_main (CURRENT ACCEPTANCE SCREENS, same target rule), calls/tiny (fixed-cost
  diagnostic, harness overhead included), all four subjects; fib and shared_rows controls
  (fuel-on and fuel-off only).
- Pairing: each cell has ROUNDS rounds; a round runs one block of every subject of that cell
  in a seeded random order; a block runs K1 and K2 back to back in a seeded random order.
  Rounds of all cells are interleaved in a seeded random order. Ratio CIs are computed from
  the rounds (paired), see analyze.py.
- Every child: `taskset -c 4`, stdin /dev/null, PERF_BUILDID_DIR absent, a per-child
  timeout; no nice/ionice on timed children. Wall time is the parent's CLOCK_MONOTONIC.
- Validity: rc 0, empty stderr, exact checksum line (and, for Rune, the MAPS line). An
  invalid sample is recorded and reported, never dropped or retried. Any stderr line from
  the native tier's invalid-exit report fails validation outright.
- Readiness (pre-registered, recorded BEFORE each block): load1 <= 1.5, MemAvailable >= 4
  GiB, no increase of CPU 4's thermal throttle counter during the block. A failing block is
  still run and kept; it is only flagged (sensitivity column).
- Bounds fixed before the run. SESSION_BOUND_S (5,400 s) is an ALL-PHASES deadline: it starts
  when `run` (or `validate`) starts, BEFORE pins, nm, admission, transcripts and the LuaJIT
  trace diagnostics, and covers the timed blocks too. It is checked before every child of
  validation and before every timed block; a child already started may overrun it by at most
  its own CHILD_TIMEOUT_S. Exceeding it stops the session (no further children), is recorded
  in the footer and gives a nonzero rc. The outer `timeout --signal=INT --kill-after=10 7200`
  of the sealed argv is only a backstop for the controller process itself.
- Child timeout mechanism (the actual one): `subprocess.run(..., timeout=CHILD_TIMEOUT_S)`.
  On expiry Python calls Popen.kill(), i.e. SIGKILL immediately, with NO SIGINT and no grace
  period, then waits for the child; the partial stdout/stderr read so far is kept in the
  record. The child is `taskset -c 4 SUBJECT ...` and util-linux taskset execs SUBJECT in the
  same pid, so the SIGKILL reaches the subject itself. Any other exception in the parent
  (including KeyboardInterrupt from the outer timeout's SIGINT) also makes subprocess.run
  SIGKILL the running child before the exception propagates.
- Validity is tracked explicitly. Every timed sample is checked; the footer records
  `complete`, `valid`, the invalid sample identities and `invalid_native_exit`. The final rc
  is 0 ONLY for a complete session in which every sample is valid; otherwise RC_INVALID (3,
  complete but some sample invalid), RC_NATIVE (4, an invalid native exit anywhere) or
  RC_STOPPED (1, stopped by the deadline, an exception or validation). An invalid session
  keeps collecting as sealed (no retry, no deletion); it never prints "complete" with rc 0.
  An exception in the parent is written to the footer with its traceback (diagnostics kept).
- Environment recorded: machine state (CPU model, microcode, governor, turbo, SMT, cpuset,
  kernel), ldd and the libc/libm/ld-linux hashes, df and meminfo before and after, and the
  environment as keys and value lengths only (redaction rule).
"""
import hashlib, json, os, random, re, shutil, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PINS = json.load(open(os.path.join(HERE, "PINS.json")))
LUAJIT = PINS["luajit"]["path"]
LUA_HARNESS = os.path.join(HERE, "harness-lua", "repeat-input-v3.lua")
BINS = {"fuel-on": PINS["rune_harness"]["fuel-on"]["path"], "fuel-off": PINS["rune_harness"]["fuel-off"]["path"]}
KERNELS_DIR = os.path.join(HERE, "kernels")
INPUTS_DIR = os.path.join(HERE, "inputs")
MANIFEST = json.load(open(os.path.join(INPUTS_DIR, "MANIFEST.json")))

CPU = "4"
ROUNDS = 10
CHILD_TIMEOUT_S = 120
SESSION_BOUND_S = 5400  # all phases, from the start of run/validate (see the docstring)
MAX_ROUNDS, MAX_BLOCKS, MAX_CHILDREN = 60, 200, 400  # revision 6's counts; asserted against the schedule
RC_OK, RC_STOPPED, RC_INVALID, RC_NATIVE = 0, 1, 3, 4
READY_LOAD1 = 1.5
READY_MEM = 4 << 30
INVALID_EXIT_TEXT = "INVALID native region exit"
# The untimed -jv/-jdump diagnostics only: the jit.* modules of the LuaJIT build tree whose
# src/luajit is byte-identical to the pinned binary (PINS.json "luajit_build").
DIAG_LUA_PATH = PINS["luajit_build"]["lua_path"]

ALL = ["luajit", "luajit-joff", "fuel-on", "fuel-off"]
RUNE = ["fuel-on", "fuel-off"]
# Bound into the raw header and required by analyze.py. Prior headers: revision r3 (R3)
# "rnx-0184-r3-probe revision r3", revision 6 (R2)
# "rnx-0184-r2-probe revision 6", ctl4 "rnx-0184-ctl4-probe revision ctl4", stage 2
# "rnx-0184-stage2-probe revision s2", revision 5 (R1) "rnx-0184-r1-probe revision 5",
# revision 4 (W13) "rnx-0184-w13-probe revision 4"; revision 3 (B1) and P2 have none.
PROBE = "rnx-0184-fuel-probe revision fuel"
SEED_FILE = os.path.join(HERE, "SESSION-SEED.txt")
# (kernel, stream, subjects); K1/K2 come from the manifest cell.
CELLS = [
	("calls", "calls_main", ALL),
	("calls", "tiny", ALL),
	("while", "loop_main", ALL),
	("numeric", "loop_main", ALL),
	("fib", "fib_main", RUNE),
	("shared_rows", "shared_rows_main", RUNE),
]
# Per-invocation estimates (us) for the bounds only (never a result). Revision fuel keeps
# revision 3's (and 4's, 5's, 6's and r3's) values verbatim (subject names only): while/numeric/fib/
# shared_rows from 0184-luajit-gap1/gap.txt (D21 for both Rune subjects); calls 443.5 us for both Rune subjects
# (the on subject conservatively as if not native) and 500 us for both LuaJIT subjects; tiny
# cells 2 us for every subject. Not updated from the B1, W13 or R1 sessions' figures, so no
# bound depends on a measured result (nor on the R2, ctl4, stage-2 or R3 sessions').
ESTIMATE_US = {
	"calls": {"luajit": 500.0, "luajit-joff": 500.0, "fuel-on": 443.5, "fuel-off": 443.5},
	"while": {"luajit": 4.77, "luajit-joff": 38.37, "fuel-on": 161.92, "fuel-off": 161.92},
	"numeric": {"luajit": 30.82, "luajit-joff": 61.15, "fuel-on": 283.71, "fuel-off": 283.71},
	"fib": {"fuel-on": 1113.33, "fuel-off": 1113.33},
	"shared_rows": {"fuel-on": 2.47, "fuel-off": 2.47},
}
# Step 0, release evidence: anonymous executable mappings at exit (one page per region).
# INDIRECT evidence that a region is loaded and stays mapped; never a production-entry counter.
# FUEL kept every admission and every golden mapped page (346623b6: calls 451 -> 721 code bytes,
# still one 4 KiB page; while 295 and numeric 552 unchanged; release listing of this package,
# byte-equal to 0184-fuel-impl1/listings/after), so one page each.
# Pre-registered (Codex 8330, as 8294): calls, while and numeric mapped in fuel-on; fib and
# shared_rows not; fuel-off maps nothing. The Step 1 transcripts must show the same counts (calls/tiny runs the
# calls kernel).
EXPECTED_MAPPINGS = {
	("fuel-on", "calls"): 1, ("fuel-on", "while"): 1, ("fuel-on", "numeric"): 1,
	("fuel-on", "fib"): 0, ("fuel-on", "shared_rows"): 0,
	("fuel-off", "calls"): 0, ("fuel-off", "while"): 0, ("fuel-off", "numeric"): 0,
	("fuel-off", "fib"): 0, ("fuel-off", "shared_rows"): 0,
}
# nm -C: test-only code that must be ABSENT from both timed binaries (CALLS-PROBE-PLAN.md 3, as
# in B1), and production code that must be present in the on subject only. heap::native's
# production code is two `impl Store` methods, whose symbols carry the TYPE path
# (`<...::heap::Store>::name`), not the module path, plus `range_next_reachable`, which is
# inlined; so the literal `heap::native` substring matches nothing in either binary (recorded
# in NM_RECORDED) and the presence check names the two methods instead (B1 deviation D3,
# accepted by Codex in seq 8063). Revision 4 also RECORDS (no gate) the count of `w13_tests`,
# W13's #[cfg(test)] module; revision 5 adds `r1_tests` (R1's two #[cfg(test)] modules,
# experimental_native::r1_tests and experimental_core::region::commit::r1_tests); revision 6
# adds `r2_tests` (R2's #[cfg(test)] module experimental_native::r2_tests); revision r3 adds
# `r3_tests` (R3's #[cfg(test)] module experimental_native::r3_tests; absent from the FUEL source,
# kept recorded); revision fuel adds `fuel_tests` (FUEL's #[cfg(test)] module
# experimental_native::fuel_tests).
NM_ABSENT = ["region::hook", "region::simulate", "simulate_traced", "force_replay",
	"set_region_transform_for_test", "inject_m1_failure_for_test", "inject_m2_failure_for_test"]
NM_ON_ONLY = ["region::cache", "heap::Store>::range_iterator_for_native", "heap::Store>::commit_range_next_for_native"]
NM_RECORDED = ["heap::native", "w13_tests", "r1_tests", "r2_tests", "r3_tests", "fuel_tests"]
# The untimed LuaJIT -jv/-jdump trace review (invocation markers, K = 3): calls only.
TRACE_DIAG = [("calls", "calls_main")]


def now_s():
	return time.monotonic()


class Deadline:
	"""The all-phases session deadline: started once, before validation."""

	def __init__(self, bound_s=None):
		self.bound_s = SESSION_BOUND_S if bound_s is None else bound_s
		self.started = now_s()

	def elapsed(self):
		return now_s() - self.started

	def exceeded(self):
		return self.elapsed() > self.bound_s


def sha256(path):
	h = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(1 << 20), b""):
			h.update(chunk)
	return h.hexdigest()


def cell_info(kernel, stream):
	return MANIFEST["cells"][f"{kernel}/{stream}"]


def inputs_path(stream):
	return os.path.join(INPUTS_DIR, MANIFEST["streams"][stream]["path"])


def argv(subject, kernel, k, inputs, phases, mode=None):
	if subject in ("luajit", "luajit-joff"):
		flags = [] if subject == "luajit" else ["-joff"]
		tail = [mode] if mode else []
		return [LUAJIT] + flags + [LUA_HARNESS, kernel + ".lua", str(k), inputs, phases] + tail
	tail = ["--transcript"] if mode == "transcript" else []
	return [BINS[subject], kernel + ".rn", str(k), inputs, phases] + tail


def child_env():
	env = dict(os.environ)
	env.pop("PERF_BUILDID_DIR", None)
	return env


def run_child(cmd, timeout=CHILD_TIMEOUT_S, timed=False, extra_env=None):
	"""Runs one child on CPU 4. Returns its record; wall_ns only when `timed`."""
	env = child_env()
	env.update(extra_env or {})
	t0 = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
	try:
		r = subprocess.run(["taskset", "-c", CPU] + cmd, cwd=KERNELS_DIR, stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
		rc, out, err, timed_out = r.returncode, r.stdout, r.stderr, False
	except subprocess.TimeoutExpired as e:
		rc, out, err, timed_out = None, e.stdout or b"", e.stderr or b"", True
	t1 = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
	rec = {"argv": cmd, "rc": rc, "timed_out": timed_out,
		"stderr": err.decode(errors="replace"), "stdout_sha256": hashlib.sha256(out).hexdigest()}
	if timed_out:
		rec["killed"] = f"SIGKILL by subprocess.run after {timeout} s (no SIGINT, no grace period)"
	if timed:
		rec["wall_ns"] = t1 - t0
	return rec, out.decode(errors="replace")


def check_output(subject, stdout, expected_checksum, k, transcript_lines=None):
	"""(valid, reason, maps) for one child's stdout."""
	lines = stdout.split("\n")
	if lines and lines[-1] == "":
		lines.pop()
	body = lines
	if transcript_lines is not None:
		n = len(transcript_lines)
		if lines[:n] != transcript_lines:
			first = next((i for i, (a, b) in enumerate(zip(lines, transcript_lines)) if a != b), None)
			return False, f"transcript differs from the model (first difference at line {first})", None
		body = lines[n:]
	want = f"CHECKSUM {expected_checksum} invocations={k}"
	if subject in RUNE:
		if len(body) != 2 or body[0] != want:
			return False, f"stdout {body[:3]!r} != {want!r} + MAPS", None
		m = re.fullmatch(r"MAPS anon_exec_mappings=(\d+) anon_exec_kib=(\d+)", body[1])
		if not m:
			return False, f"bad MAPS line {body[1]!r}", None
		return True, "", (int(m.group(1)), int(m.group(2)))
	if body != [want]:
		return False, f"stdout {body[:3]!r} != {want!r}", None
	return True, "", None


def child_valid(rec, subject, stdout, expected_checksum, k, transcript_lines=None):
	if rec["timed_out"]:
		return False, "timeout", None
	if rec["rc"] != 0:
		return False, f"rc {rec['rc']}", None
	if rec["stderr"]:
		reason = "INVALID NATIVE EXIT" if INVALID_EXIT_TEXT in rec["stderr"] else "stderr not empty"
		return False, reason, None
	return check_output(subject, stdout, expected_checksum, k, transcript_lines)


# ------------------------------------------------------------------- environment

def read(path):
	try:
		return open(path).read().strip()
	except OSError as e:
		return f"<unreadable: {e.__class__.__name__}>"


def machine_state():
	cpuinfo = read("/proc/cpuinfo")
	block = next((b for b in cpuinfo.split("\n\n") if re.search(rf"^processor\s*:\s*{CPU}$", b, re.M)), "")
	field = lambda name: next((l.split(":", 1)[1].strip() for l in block.splitlines() if l.startswith(name)), None)
	status = read("/proc/self/status")
	meminfo = {l.split(":")[0]: l.split(":")[1].strip() for l in read("/proc/meminfo").splitlines() if ":" in l}
	du = shutil.disk_usage("/home/me/work")
	return {
		"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
		"uname": list(os.uname()),
		"cpu4_model": field("model name"), "cpu4_microcode": field("microcode"),
		"cpu4_governor": read(f"/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_governor"),
		"cpu4_cur_freq_khz": read(f"/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_cur_freq"),
		"intel_no_turbo": read("/sys/devices/system/cpu/intel_pstate/no_turbo"),
		"cpufreq_boost": read("/sys/devices/system/cpu/cpufreq/boost"),
		"smt_active": read("/sys/devices/system/cpu/smt/active"),
		"cpus_allowed": next((l.split(":", 1)[1].strip() for l in status.splitlines() if l.startswith("Cpus_allowed_list")), None),
		"cpu4_throttle_count": read(f"/sys/devices/system/cpu/cpu{CPU}/thermal_throttle/core_throttle_count"),
		"loadavg": read("/proc/loadavg"),
		"mem_total": meminfo.get("MemTotal"), "mem_available": meminfo.get("MemAvailable"),
		"disk_free_bytes": du.free,
	}


def environment_keys():
	"""Keys and value lengths only: never values (redaction rule)."""
	return {k: len(v) for k, v in sorted(os.environ.items())}


def libraries(binary):
	out = subprocess.run(["ldd", binary], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
	libs = {}
	for line in out.splitlines():
		m = re.search(r"(/\S+)", line)
		if m and any(x in m.group(1) for x in ("libc.so", "libm.so", "ld-linux")):
			p = os.path.realpath(m.group(1))
			libs[m.group(1)] = {"realpath": p, "sha256": sha256(p)}
	return {"ldd": out, "libs": libs}


def ready():
	load1 = os.getloadavg()[0]
	mem = 0
	for line in open("/proc/meminfo"):
		if line.startswith("MemAvailable:"):
			mem = int(line.split()[1]) * 1024
	return {"load1": load1, "mem_available": mem, "ok": load1 <= READY_LOAD1 and mem >= READY_MEM}


def throttle_count():
	try:
		return int(open(f"/sys/devices/system/cpu/cpu{CPU}/thermal_throttle/core_throttle_count").read())
	except (OSError, ValueError):
		return None


# --------------------------------------------------------------------- pins, nm

def git(wt, *a):
	return subprocess.run(["git", "-C", wt, "-c", "color.ui=false", "-c", "color.diff=false", *a],
		capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout


def verify_pins():
	"""Every pinned file's sha256, both subjects (sha256 + X_OK), the LuaJIT pins and the source
	worktree (HEAD, tree, clean, workspace lock). Returns (ok, report)."""
	report, ok = [], True

	def check(label, path, want, need_exec=False):
		nonlocal ok
		have = sha256(path) if os.path.exists(path) else "<missing>"
		good = have == want
		rec = {"what": label, "path": path, "want": want, "have": have}
		if need_exec:
			rec["x_ok"] = os.access(path, os.X_OK)
			good &= rec["x_ok"]
		rec["ok"] = good
		ok &= good
		report.append(rec)

	check("luajit", LUAJIT, PINS["luajit"]["sha256"], need_exec=True)
	lb = PINS["luajit_build"]
	check("luajit build tree src/luajit", os.path.join(lb["tree"], "src", "luajit"), lb["src_luajit_sha256"])
	for name in ("vmdef", "v", "dump"):
		check(f"luajit jit/{name}.lua", os.path.join(lb["tree"], "src", "jit", name + ".lua"), lb[name + ("_sha256" if name == "vmdef" else "_lua_sha256")])
	for s in RUNE:
		check(s, BINS[s], PINS["rune_harness"][s]["sha256"], need_exec=True)
	for name, want in PINS["files"].items():
		check(name, os.path.join(HERE, name), want)
	ent = PINS["rune"]
	wt = ent["worktree"]
	head = git(wt, "rev-parse", "HEAD").strip()
	tree = git(wt, "rev-parse", "HEAD^{tree}").strip()
	dirty = git(wt, "status", "--porcelain", "--untracked-files=no")
	lock = os.path.join(wt, "Cargo.lock")
	lock_have = sha256(lock) if os.path.exists(lock) else "<missing>"
	toml = os.path.join(wt, "crates", "rune", "Cargo.toml")
	toml_have = sha256(toml) if os.path.exists(toml) else "<missing>"
	good = (head == ent["commit"] and tree == ent["tree"] and dirty == "" and lock_have == ent["workspace_lock_sha256"]
		and toml_have == ent["crate_cargo_toml_sha256"])
	ok &= good
	report.append({"what": "rune worktree", "path": wt, "want": ent["commit"], "have": head, "tree": tree, "dirty": dirty,
		"lock_want": ent["workspace_lock_sha256"], "lock_have": lock_have, "crate_toml_have": toml_have, "ok": good})
	return ok, report


def nm_check():
	"""No test hook, simulator or test injection in either timed binary (with the source/cfg
	review); region::cache and heap::native's two methods present only in fuel-on."""
	out, ok = {}, True
	for s in RUNE:
		syms = subprocess.run(["nm", "-C", BINS[s]], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.splitlines()
		absent = {name: [l for l in syms if name in l] for name in NM_ABSENT}
		on_only = {name: len([l for l in syms if name in l]) for name in NM_ON_ONLY}
		recorded = {name: len([l for l in syms if name in l]) for name in NM_RECORDED}
		out[s] = {"symbols": len(syms), "absent": absent, "on_only_counts": on_only, "recorded_counts": recorded}
		ok &= len(syms) > 0 and not any(absent.values())
		ok &= all((n > 0) == (s == "fuel-on") for n in on_only.values())
	return ok, out


# ------------------------------------------------------------------ steps 0 and 1

class DeadlineStop(Exception):
	pass


def validate(out_dir, max_k=None, deadline=None):
	"""Steps 0 and 1. Records no timing. Returns True when everything passed. Every child is
	preceded by a check of the all-phases deadline; exceeding it stops validation (failed)."""
	deadline = deadline or Deadline()
	os.makedirs(out_dir, exist_ok=False)
	log = open(os.path.join(out_dir, "validate.jsonl"), "w")
	emit = lambda rec: (log.write(json.dumps(rec) + "\n"), log.flush())
	passed = True
	stopped = None
	emit({"step": "header", "probe": PROBE, "max_k": max_k, "dry_run": max_k is not None,
		"deadline": {"policy": "all phases", "bound_s": deadline.bound_s, "elapsed_s": deadline.elapsed()},
		"machine": machine_state(), "environment_keys": environment_keys(),
		"libraries": {s: libraries(BINS[s]) for s in RUNE}})
	assert "PERF_BUILDID_DIR" not in os.environ, "run under env -u PERF_BUILDID_DIR"

	def child(cmd, where, **kw):
		if deadline.exceeded():
			raise DeadlineStop(f"session bound {deadline.bound_s} s (all phases) exceeded before {where}")
		return run_child(cmd, **kw)

	ok, report = verify_pins()
	emit({"step": "0-pins", "ok": ok, "report": report})
	passed &= ok
	ok, report = nm_check()
	emit({"step": "0-nm", "ok": ok, "report": report})
	passed &= ok

	try:
		# Step 0, release evidence of admission: mappings at exit after K=1.
		for (subject, kernel), want in sorted(EXPECTED_MAPPINGS.items()):
			stream = next(s for k, s, _ in CELLS if k == kernel and s != "tiny")
			exp = cell_info(kernel, stream)["expected_checksum"]["1"]
			rec, stdout = child(argv(subject, kernel, 1, inputs_path(stream), "-"), f"admission {subject} {kernel}")
			valid, reason, maps = child_valid(rec, subject, stdout, exp, 1)
			ok = valid and maps is not None and maps[0] == want
			passed &= ok
			emit({"step": "0-admission", "subject": subject, "kernel": kernel, "want_mappings": want,
				"maps": maps, "valid": valid, "reason": reason, "ok": ok, "child": rec})

		# Step 1: transcripts (Rune and LuaJIT) against the model over the whole K2 stream.
		for kernel, stream, subjects in CELLS:
			info = cell_info(kernel, stream)
			k = info["k2"] if max_k is None else min(info["k2"], max_k)
			expected = open(os.path.join(INPUTS_DIR, info["expected_path"])).read().split("\n")[:k]
			from_model = None
			if max_k is None:
				from_model = info["expected_checksum"][str(k)]
			else:
				c = 0
				for r in expected:
					c = (c * 31 + int(r)) % 1_000_000_007
				from_model = c
			transcripts, whole = {}, {}
			for subject in subjects:
				rec, stdout = child(argv(subject, kernel, k, inputs_path(stream), "-", "transcript"),
					f"transcript {kernel}/{stream} {subject}")
				valid, reason, maps = child_valid(rec, subject, stdout, from_model, k, expected)
				# The results and checksum lines only: the MAPS line differs by design.
				kept = [l for l in stdout.split("\n") if not l.startswith("MAPS ")]
				transcripts[subject] = hashlib.sha256("\n".join(kept).encode()).hexdigest()
				whole[subject] = rec["stdout_sha256"]
				ok = valid
				if subject in RUNE:
					# Stricter than revision 6 (ctl4): the transcript's MAPS count is pre-registered too.
					ok &= maps is not None and maps[0] == EXPECTED_MAPPINGS[(subject, kernel)]
				passed &= ok
				emit({"step": "1-transcript", "kernel": kernel, "stream": stream, "subject": subject,
					"k": k, "valid": valid, "reason": reason, "maps": maps,
					"want_mappings": EXPECTED_MAPPINGS.get((subject, kernel)), "ok": ok, "child": rec})
			if "fuel-on" in transcripts:
				same = transcripts["fuel-on"] == transcripts["fuel-off"]
				passed &= same
				emit({"step": "1-on-off-identical", "kernel": kernel, "stream": stream, "identical": same,
					"compared": "result lines and checksum line (MAPS excluded)", "model_checksum": from_model,
					"kept_sha256": transcripts, "whole_stdout_sha256": whole})

		# Step 1, LuaJIT trace review (untimed diagnostics): -jv and -jdump with invocation markers.
		diag = os.path.join(out_dir, "luajit-trace")
		os.makedirs(diag)
		status, _ = child([LUAJIT, "-e", "print(jit.version); print(jit.status())"], "luajit status")
		emit({"step": "1-luajit-status", "child": status})
		for kernel, stream in TRACE_DIAG:
			for flag in ("-jv", "-jdump=+tbirsmx"):
				cmd = [LUAJIT, flag, LUA_HARNESS, kernel + ".lua", "3", inputs_path(stream), "-", "markers"]
				rec, stdout = child(cmd, f"luajit trace {kernel} {flag}", extra_env={"LUA_PATH": DIAG_LUA_PATH})
				passed &= rec["rc"] == 0
				name = f"{kernel}{flag.split('=')[0]}"
				open(os.path.join(diag, name + ".stdout.txt"), "w").write(stdout)
				open(os.path.join(diag, name + ".stderr.txt"), "w").write(rec["stderr"])
				emit({"step": "1-luajit-trace", "kernel": kernel, "flag": flag, "rc": rec["rc"], "argv": cmd,
					"env_added": {"LUA_PATH": DIAG_LUA_PATH}})
	except DeadlineStop as e:
		stopped = str(e)
		passed = False
		emit({"step": "stopped", "reason": stopped})

	emit({"step": "footer", "passed": passed, "stopped": stopped,
		"deadline_elapsed_s": deadline.elapsed(), "machine": machine_state()})
	print("VALIDATION", "PASSED" if passed else "FAILED", "(dry run, capped K)" if max_k else "",
		f"STOPPED: {stopped}" if stopped else "")
	return passed


# ---------------------------------------------------------------- the schedule

def schedule(seed):
	"""The interleaved, paired schedule: a list of rounds, each a list of blocks."""
	rng = random.Random(seed)
	rounds = [(kernel, stream, subjects, r) for kernel, stream, subjects in CELLS for r in range(ROUNDS)]
	rng.shuffle(rounds)
	out = []
	for kernel, stream, subjects, r in rounds:
		info = cell_info(kernel, stream)
		order = list(subjects)
		rng.shuffle(order)
		blocks = []
		for subject in order:
			ks = [info["k1"], info["k2"]]
			if rng.random() >= 0.5:
				ks.reverse()
			blocks.append({"subject": subject, "order": ks})
		out.append({"kernel": kernel, "stream": stream, "round": r, "blocks": blocks})
	return out


def estimate_s(plan):
	total = 0.0
	worst = 0.0
	for rnd in plan:
		for b in rnd["blocks"]:
			us = 2.0 if rnd["stream"] == "tiny" else ESTIMATE_US[rnd["kernel"]][b["subject"]]
			for k in b["order"]:
				child = k * us / 1e6 + 0.2
				total += child
				worst = max(worst, child)
	return total, worst


def estimate_validation_s():
	"""Steps 0-1: one K2 transcript per (cell, subject), the K=1 admission children and the
	LuaJIT diagnostics (transcript printing not modelled: an estimate for the bound only)."""
	total = 0.0
	for kernel, stream, subjects in CELLS:
		for subject in subjects:
			us = 2.0 if stream == "tiny" else ESTIMATE_US[kernel][subject]
			total += cell_info(kernel, stream)["k2"] * us / 1e6 + 0.2
	return total + 0.2 * (len(EXPECTED_MAPPINGS) + 1 + 2 * len(TRACE_DIAG))


def print_schedule(seed):
	plan = schedule(seed)
	total, worst = estimate_s(plan)
	val = estimate_validation_s()
	children = sum(2 * len(r["blocks"]) for r in plan)
	print(f"seed={seed} rounds={len(plan)} blocks={sum(len(r['blocks']) for r in plan)} children={children}")
	print(f"estimated validation {val/60:.1f} min + timed session {total/60:.1f} min = {(val+total)/60:.1f} min "
		f"(all-phases bound {SESSION_BOUND_S/60:.0f} min); slowest child ~{worst:.1f} s (bound {CHILD_TIMEOUT_S} s)")
	blocks = sum(len(r["blocks"]) for r in plan)
	assert len(plan) <= MAX_ROUNDS and blocks <= MAX_BLOCKS and 2 * blocks <= MAX_CHILDREN, "schedule exceeds the sealed bounds"
	assert worst < CHILD_TIMEOUT_S / 2 and val + total < SESSION_BOUND_S / 2, "bounds too tight for the schedule"
	for i, r in enumerate(plan[:12]):
		print(i, r["kernel"], r["stream"], "round", r["round"], [(b["subject"], b["order"]) for b in r["blocks"]])
	print("...")
	return plan


# ------------------------------------------------------------- step 2, timed

class Validity:
	"""Explicit validity of the timed session. Fed every timed sample; never reset."""

	def __init__(self):
		self.samples = 0
		self.invalid = []
		self.invalid_native_exit = False

	def add(self, ident, rec):
		self.samples += 1
		if INVALID_EXIT_TEXT in (rec.get("stderr") or "") or rec.get("reason") == "INVALID NATIVE EXIT":
			self.invalid_native_exit = True
		if not rec.get("valid"):
			self.invalid.append(dict(ident, reason=rec.get("reason")))

	def valid(self):
		return not self.invalid and not self.invalid_native_exit


def final_rc(complete, validity):
	"""0 only for a complete session in which every timed sample is valid."""
	if not complete:
		return RC_STOPPED
	if validity.invalid_native_exit:
		return RC_NATIVE
	if not validity.valid():
		return RC_INVALID
	return RC_OK


def final_line(complete, stopped, validity, rc):
	if not complete:
		return f"SESSION STOPPED (INCOMPLETE): {stopped}; rc {rc}"
	if rc == RC_OK:
		return f"SESSION complete, all {validity.samples} samples valid; rc 0"
	what = "INVALID NATIVE EXIT observed" if validity.invalid_native_exit else f"{len(validity.invalid)} invalid sample(s)"
	return f"SESSION INVALID: all blocks collected as sealed, {what}; rc {rc}"


def sealed_seed():
	return int(open(SEED_FILE).read().strip())


def run(out_dir, seed, deadline=None):
	deadline = deadline or Deadline()  # all phases: started before validation
	if seed != sealed_seed():
		print(f"STOP: seed {seed} is not the sealed SESSION-SEED.txt; nothing was run; rc {RC_STOPPED}")
		return RC_STOPPED
	if not validate(os.path.join(out_dir, "validation"), deadline=deadline):
		print(f"STOP: validation failed or the all-phases deadline was exceeded; no timing was run; rc {RC_STOPPED}")
		return RC_STOPPED
	plan = print_schedule(seed)
	expected_blocks = sum(len(r["blocks"]) for r in plan)
	raw = open(os.path.join(out_dir, "raw.jsonl"), "w")
	emit = lambda rec: (raw.write(json.dumps(rec) + "\n"), raw.flush())
	emit({"record": "header", "probe": PROBE, "seed": seed, "rounds_per_cell": ROUNDS, "cells": CELLS,
		"subjects": ALL, "child_timeout_s": CHILD_TIMEOUT_S, "session_bound_s": SESSION_BOUND_S,
		"deadline_policy": "all phases (validation included), from the start of run",
		"elapsed_before_timing_s": deadline.elapsed(),
		"expected_blocks": expected_blocks, "expected_children": 2 * expected_blocks,
		"controller_sha256": sha256(os.path.abspath(__file__)),
		"pins": PINS, "manifest_seed": MANIFEST["seed"], "machine": machine_state(),
		"environment_keys": environment_keys()})
	validity = Validity()
	stopped, error, done = None, None, 0
	try:
		for i, rnd in enumerate(plan):
			info = cell_info(rnd["kernel"], rnd["stream"])
			for j, block in enumerate(rnd["blocks"]):
				if deadline.exceeded():
					stopped = f"session bound {deadline.bound_s} s (all phases) exceeded before round {i} block {j}"
					break
				before = ready()
				thr0 = throttle_count()
				samples = {}
				for k in block["order"]:
					phases = os.path.join(out_dir, f"phases.{i}.{j}.{k}.txt")
					rec, stdout = run_child(argv(block["subject"], rnd["kernel"], k, inputs_path(rnd["stream"]), phases), timed=True)
					valid, reason, maps = child_valid(rec, block["subject"], stdout, info["expected_checksum"][str(k)], k)
					rec.update({"valid": valid, "reason": reason, "maps": maps, "stdout": stdout,
						"phases": open(phases).read() if os.path.exists(phases) else None})
					samples[str(k)] = rec
					validity.add({"round_index": i, "block": j, "cell": f"{rnd['kernel']}/{rnd['stream']}",
						"round": rnd["round"], "subject": block["subject"], "k": k}, rec)
				thr1 = throttle_count()
				flagged = (not before["ok"]) or (thr0 is not None and thr1 is not None and thr1 > thr0)
				emit({"record": "block", "round_index": i, "kernel": rnd["kernel"], "stream": rnd["stream"],
					"round": rnd["round"], "block": j, "position": j, "subject": block["subject"], "order": block["order"],
					"ready": before, "throttle": [thr0, thr1], "flagged": flagged, "samples": samples})
				done += 1
			if stopped:
				break
	except BaseException as e:  # diagnostics kept; the running child was already SIGKILLed by subprocess.run
		stopped = f"exception {e.__class__.__name__}: {e}"
		error = traceback.format_exc()
	complete = stopped is None and done == expected_blocks
	if stopped is None and not complete:
		stopped = f"only {done} of {expected_blocks} blocks collected"
	rc = final_rc(complete, validity)
	emit({"record": "footer", "complete": complete, "stopped": stopped, "error": error,
		"blocks_collected": done, "expected_blocks": expected_blocks,
		"samples_checked": validity.samples, "valid": complete and validity.valid(),
		"invalid_samples": validity.invalid, "invalid_native_exit": validity.invalid_native_exit,
		"rc": rc, "elapsed_total_s": deadline.elapsed(), "machine": machine_state()})
	print(final_line(complete, stopped, validity, rc))
	if error:
		print(error, file=sys.stderr)
	return rc


def main(args):
	deadline = Deadline()  # started first: the bound covers every phase
	if args[:1] == ["schedule"] and len(args) == 2:
		print_schedule(int(args[1]))
		return 0
	if args[:1] == ["validate"] and len(args) in (2, 4):
		max_k = None
		if len(args) == 4:
			assert args[2] == "--max-k"
			max_k = int(args[3])
		return 0 if validate(args[1], max_k, deadline=deadline) else 1
	if args[:1] == ["run"] and len(args) == 3:
		return run(args[1], int(args[2]), deadline=deadline)
	print(__doc__)
	return 2


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
