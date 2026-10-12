#!/usr/bin/env python3
"""Synthetic controls for the FUEL probe analyzer and controller (rnx 0184, revision fuel; Codex GO 8330).

The R3 suite (revision r3, Codex GO 8294), adapted to revision fuel: the subjects fuel-on/fuel-off,
the probe name, the FUEL pins, code notes and tradeoffs, the R3 history lines, and, in addition:
revision r3's header, the R3 binaries' pins, the R3 commit and worktree and the subjects r3-on/r3-off
refused as foreign; the real R3 session raw refused; FUEL wording-guard positives.

Revision 6's design controls (calls the SOLE PRIMARY met / below / unresolved and never a STOP;
while and numeric screens: below / unresolved / R_joff failure -> STOP; calls R_joff failure ->
STOP; fib/shared_rows control failures -> STOP) combined with the ctl4 safeguards:

- per-case control margin wording: lower > 1.01 (scoped >1% statement), straddling (unresolved),
  equality at 1.01 (upper met, lower not above), missing interval; no blanket disclaimer;
- the joint paired-round bootstrap (one index vector per resample for every subject of a cell)
  with an INDEPENDENT-RESAMPLING mutant that must be caught (and is shown to be material);
- complete-tuple sensitivity with a PARTIAL (per-pair) mutant that must be caught;
- denominator positivity at the point, resample and lower-bound stages;
- global invalid suppression (one invalid sample anywhere, an invalid native exit, a missing
  block or subject: no interval or verdict in ANY cell);
- complete-footer, binding and schedule-identity safeguards; foreign subjects; old headers
  (revision 3-6, ctl4, stage 2, r3); the real prior raw files (P2, B1, W13, R1, R2, ctl4, stage 2, R3)
  refused, read only;
- banned-word / attribution guards with a positive control;
- the controller's fail-closed paths with a fake runner (including the sealed-seed refusal and
  the stricter transcript MAPS check).

NO subject is run and NOTHING is timed: every session file is fabricated; the controller's child
runner, validation and clock are replaced by fakes at the function level.

usage: python3 -I -B test_analyze.py      (exit 0 when every control passes)
"""
import contextlib, copy, hashlib, importlib.util, io, json, os, random, statistics, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module(name):
	spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


A = load_module("analyze")
C = load_module("controller")
MANIFEST_PATH = os.path.join(HERE, "inputs", "MANIFEST.json")
MANIFEST = json.load(open(MANIFEST_PATH))
PINS = json.load(open(os.path.join(HERE, "PINS.json")))
SEED = int(open(os.path.join(HERE, "SESSION-SEED.txt")).read().strip())
WORK = tempfile.mkdtemp(prefix="fuel-controls-")
RESULTS = []
OUTPUTS = []  # every analyzer output produced by these controls (wording guards)

PRIOR_RAW = {
	"P2": ("/home/me/work/.reviews/0184-p2-probe1/session/raw.jsonl", "f94735f5edc35d436262d902b8529809983c12d9009783f3e3a3b2cf827253cb"),
	"B1": ("/home/me/work/.reviews/0184-b1-session1/session/raw.jsonl", "547a3ea68f351c30eba0c9905c28407ed896be5325134e29403b47c8a14ca78f"),
	"W13": ("/home/me/work/.reviews/0184-w13-session1/session/raw.jsonl", "7d498f588a0efd12089b58d36a7356c8db5565648fa982c5691ffff3e6c59d1c"),
	"R1": ("/home/me/work/.reviews/0184-r1-session1/session/raw.jsonl", "f5d60aab54f5eb881b9acb1281cc86bf5159a5c8852c2a6235f0ecf88ca8280e"),
	"R2": ("/home/me/work/.reviews/0184-r2-session1/session/raw.jsonl", "dddf3a15caf92dcb5136257c263943c8429c3e48d18f4b0ee57cb10dabfb80e5"),
	"ctl4": ("/home/me/work/.reviews/0184-ctl4-session1/session/raw.jsonl", "0ee977613dcc89119a9e252aa9b2883fa54112f55a923ab845ebc10825adfffa"),
	"stage2": ("/home/me/work/.reviews/0184-stage2-session1/session/raw.jsonl", "80ab2579139e64b596f46b7ab9b834fac775bae52cfff664adb242b38b0f2d0c"),
	"R3": ("/home/me/work/.reviews/0184-r3-session1/session/raw.jsonl", "8ef0930a710d1377e3f4389252ee77506adc039ed1a34e2a5ac3e30e687c85f8"),
}
# Real unrounded intervals (R2, R1 and R3 RESULTS.json) as wording fixtures.
R2_FIB = [1.0190828610573877, 1.0386724089366006]
R2_SHARED = [0.9451927967089353, 1.0333230026937792]
R1_FIB = [0.9894610301517119, 1.0022642386645717]
R3_SHARED = [1.0087552542601506, 1.021740590251954]
# Synthetic per-invocation cost (ns): every gate PASSES on a clean session.
GOOD_NS = {"luajit": 1000.0, "luajit-joff": 4000.0, "fuel-on": 1100.0, "fuel-off": 9000.0}
CONTROL_NS = 5000.0
GATE_CELLS = {"calls": "calls/calls_main", "while": "while/loop_main", "numeric": "numeric/loop_main"}


def check(case, cond, detail=""):
	RESULTS.append((case, bool(cond), detail))
	print(("PASS " if cond else "FAIL ") + case + (f" -- {detail}" if detail else ""))


# ---------------------------------------------------------------- fabrication

def base_ns(cell, subject):
	return CONTROL_NS if cell.split("/")[0] in ("fib", "shared_rows") else GOOD_NS[subject]


def noisy(rel=None, sd=0.002, seed=1, shared_sd=0.0):
	"""slope = base * rel[(cell, subject)] * (1 + per-(cell, round) effect shared by every subject + own noise)."""
	rel = rel or {}
	rng = random.Random(seed)
	cells = [f"{k}/{s}" for k, s, _ in A.CELLS]
	own = {(c, s, r): rng.gauss(0, sd) for c in cells for s in A.ALL for r in range(A.ROUNDS)}
	shared = {(c, r): rng.gauss(0, shared_sd) for c in cells for r in range(A.ROUNDS)}
	return lambda cell, subject, rnd: base_ns(cell, subject) * rel.get((cell, subject), 1.0) * (1 + shared[(cell, rnd)] + own[(cell, subject, rnd)])


def blocks(slope=None, flagged=None, seed=SEED):
	slope = slope or noisy()
	out = []
	for i, rnd in enumerate(A.schedule(seed, MANIFEST)):
		cell = f"{rnd['kernel']}/{rnd['stream']}"
		info = MANIFEST["cells"][cell]
		for j, b in enumerate(rnd["blocks"]):
			s = slope(cell, b["subject"], rnd["round"])
			maps = [C.EXPECTED_MAPPINGS[(b["subject"], rnd["kernel"])], 4 * C.EXPECTED_MAPPINGS[(b["subject"], rnd["kernel"])]] if b["subject"] in A.RUNE else None
			mk = lambda wall: {"valid": True, "rc": 0, "stderr": "", "reason": "", "maps": maps, "wall_ns": wall,
				"phases": "ready 1000\nfirst 5000\n"}
			samples = {str(info["k1"]): mk(2_000_000), str(info["k2"]): mk(2_000_000 + int(round(s * (info["k2"] - info["k1"]))))}
			out.append({"record": "block", "round_index": i, "kernel": rnd["kernel"], "stream": rnd["stream"],
				"round": rnd["round"], "block": j, "position": j, "subject": b["subject"], "order": b["order"],
				"flagged": bool(flagged and (cell, b["subject"], rnd["round"]) in flagged), "samples": samples})
	return out


def header(seed=SEED, **over):
	h = {"record": "header", "probe": A.PROBE, "seed": seed, "rounds_per_cell": A.ROUNDS,
		"cells": json.loads(json.dumps(A.CELLS)), "subjects": list(A.ALL),
		"child_timeout_s": A.CHILD_TIMEOUT_S, "session_bound_s": A.SESSION_BOUND_S,
		"expected_blocks": A.SEAL_BLOCKS, "expected_children": A.SEAL_CHILDREN, "pins": copy.deepcopy(PINS),
		"manifest_seed": MANIFEST["seed"], "controller_sha256": A.sha256_file(os.path.join(HERE, "controller.py"))}
	h.update(over)
	return h


def footer(blks=None, **over):
	inv = [b for b in (blks or []) if not all(s["valid"] for s in b["samples"].values())]
	native = any("INVALID native region exit" in (s.get("stderr") or "") for b in (blks or []) for s in b["samples"].values())
	f = {"record": "footer", "complete": True, "stopped": None, "error": None, "blocks_collected": A.SEAL_BLOCKS,
		"expected_blocks": A.SEAL_BLOCKS, "samples_checked": A.SEAL_CHILDREN, "valid": not inv,
		"invalid_samples": [], "invalid_native_exit": native, "rc": 4 if native else 3 if inv else 0}
	f.update(over)
	return f


def write(name, records, tail=None):
	path = os.path.join(WORK, name + ".jsonl")
	with open(path, "w") as f:
		for r in records:
			f.write(json.dumps(r) + "\n")
		if tail is not None:
			f.write(tail)
	return path


def analyze(name, records, tail=None):
	out, rc = A.analyze(write(name, records, tail), MANIFEST_PATH)
	OUTPUTS.append((name, out))
	return out, rc


def session(name, slope=None, flagged=None, mutate=None):
	blks = blocks(slope, flagged)
	if mutate:
		mutate(blks)
	return analyze(name, [header()] + blks + [footer(blks)])


def find(blks, cell, subject, rnd):
	return next(b for b in blks if f"{b['kernel']}/{b['stream']}" == cell and b["subject"] == subject and b["round"] == rnd)


def verdict_paths(obj, path=""):
	found = []
	if isinstance(obj, dict):
		for k, v in obj.items():
			if k == "verdict":
				found.append(path)
			found += verdict_paths(v, f"{path}/{k}")
	return found


def expect_no_verdicts(case, out, rc, status):
	v = verdict_paths(out["verdicts"])
	ci = [p for p in ("calls", "while", "numeric") if "ci95" in out["verdicts"].get(p, {}).get("R_jit", {})]
	check(case, out["session_status"] == status and rc == A.RC[status] and out["acceptance_verdicts"] is False and not v and not ci
		and out["observed_categories"].get("suppressed"),
		f"status={out['session_status']} rc={rc} acceptance={out['acceptance_verdicts']} verdicts={len(v)} "
		f"errors={(out['errors']['invalid'] + out['errors']['incomplete'])[:2]}")


def straddle(cell, lo, hi, subject="fuel-on"):
	"""A slope function whose `subject` in `cell` alternates lo / hi x the cell's reference (luajit, or the control base) over rounds."""
	sl = noisy()
	return lambda c, s, r: (base_ns(c, "luajit") * (lo if r % 2 == 0 else hi)) if (c, s) == (cell, subject) else sl(c, s, r)


# ---------------------------------------------------------------- seal controls

def seal_controls():
	check("seal arithmetic: 200 blocks / 400 children / 60 rounds", A.derived_counts() == (200, 400) and A.SEAL_ROUNDS == 60
		and len(C.schedule(SEED)) == 60 and sum(len(r["blocks"]) for r in C.schedule(SEED)) == 200
		and (C.MAX_ROUNDS, C.MAX_BLOCKS, C.MAX_CHILDREN) == (60, 200, 400))
	saved = list(A.CELLS)
	try:
		A.CELLS.append(("while", "tiny", A.ALL))
		try:
			A.derived_counts()
			raised = False
		except A.SealArithmeticError:
			raised = True
	finally:
		A.CELLS[:] = saved
	check("seal arithmetic refuses an extra (dropped revision-2) cell", raised and A.derived_counts() == (200, 400))
	check("manifest table: the sealed 6 cells with revision 6's K1/K2", set(MANIFEST["cells"]) == set(A.SEALED_K)
		and all((MANIFEST["cells"][c]["k1"], MANIFEST["cells"][c]["k2"]) == k for c, k in A.SEALED_K.items())
		and A.SEALED_K == {"calls/calls_main": (100, 10100), "calls/tiny": (1000, 101000), "while/loop_main": (1000, 101000),
			"numeric/loop_main": (1000, 101000), "fib/fib_main": (100, 10100), "shared_rows/shared_rows_main": (1000, 101000)})
	check("schedule identity: analyzer == controller for the sealed seed and 3 others",
		all(A.schedule(s, MANIFEST) == C.schedule(s) for s in (SEED, 0, 1, 2**63 - 1)) and A.CELLS == C.CELLS and A.ROUNDS == C.ROUNDS == 10)
	check("controller pre-registration: maps, nm lists, probe name, bounds",
		C.EXPECTED_MAPPINGS == {("fuel-on", "calls"): 1, ("fuel-on", "while"): 1, ("fuel-on", "numeric"): 1, ("fuel-on", "fib"): 0,
			("fuel-on", "shared_rows"): 0, ("fuel-off", "calls"): 0, ("fuel-off", "while"): 0, ("fuel-off", "numeric"): 0,
			("fuel-off", "fib"): 0, ("fuel-off", "shared_rows"): 0}
		and C.PROBE == A.PROBE == "rnx-0184-fuel-probe revision fuel" and C.ALL == A.ALL and C.RUNE == A.RUNE == ["fuel-on", "fuel-off"]
		and C.NM_ABSENT == ["region::hook", "region::simulate", "simulate_traced", "force_replay",
			"set_region_transform_for_test", "inject_m1_failure_for_test", "inject_m2_failure_for_test"]
		and C.NM_ON_ONLY == ["region::cache", "heap::Store>::range_iterator_for_native", "heap::Store>::commit_range_next_for_native"]
		and C.NM_RECORDED == ["heap::native", "w13_tests", "r1_tests", "r2_tests", "r3_tests", "fuel_tests"]
		and C.TRACE_DIAG == [("calls", "calls_main")]
		and (C.ROUNDS, C.CHILD_TIMEOUT_S, C.SESSION_BOUND_S) == (10, 120, 5400) == (A.ROUNDS, A.CHILD_TIMEOUT_S, A.SESSION_BOUND_S)
		and (A.JIT_TARGET, A.JOFF_STOP, A.CONTROL_MARGIN, A.B) == (1.25, 1.0, 1.01, 10_000))
	check("pins: subject commit 346623b6, workspace lock 54422608, harness lock b65e3a87, both binaries pinned",
		PINS["rune"]["commit"] == "346623b6c9ee33f15ea1bca3c143723e9e147d07" and PINS["rune"]["base"].startswith("e1e1f30b")
		and PINS["rune"]["workspace_lock_sha256"].startswith("54422608") and PINS["build"]["harness_lock_sha256"].startswith("b65e3a87")
		and set(PINS["rune_harness"]) == {"fuel-on", "fuel-off"} and all(len(PINS["rune_harness"][s]["sha256"]) == 64 for s in A.RUNE)
		and "rune-fuel-probe" in PINS["rune"]["worktree"] and all("rune-fuel-probe-" in PINS["rune_harness"][s]["path"] for s in A.RUNE))
	check("bootstrap seed is the sealed BOOT-SEED.txt (no CLI seed); session seed is SESSION-SEED.txt; both pinned",
		A.boot_seed() == int(open(os.path.join(HERE, "BOOT-SEED.txt")).read()) and C.sealed_seed() == SEED
		and "BOOT-SEED.txt" in PINS["files"] and "SESSION-SEED.txt" in PINS["files"])


# ---------------------------------------------------------------- wording units

def wording_unit_controls():
	scoped = lambda t: "these binaries" in t and "this session" in t
	jit = [([1.10, 1.20], "met", "target met"), ([1.20, 1.25], "met_equal_edge", "upper bound equals 1.25 exactly"),
		([1.2499, 1.2500001], "unresolved", "straddles 1.25"), ([1.25, 1.30], "unresolved_equal_edge", "lower bound equals 1.25 exactly"),
		([1.2500001, 1.30], "below", "below target"), ([1.2499999, 1.2500000000001], "unresolved", "unresolved")]
	for ci, cat, must in jit:
		t = A.jit_target_verdict({"ci95": ci})
		check(f"R_jit rule {ci} -> {cat}", A.jit_category(ci) == cat and must in t and scoped(t), t)
	t = A.jit_target_verdict({"unresolved": "denominator luajit not finite and strictly positive (point estimate)"})
	check("R_jit no interval -> unresolved", t.startswith("unresolved") and A.jit_category(None) == "unresolved_no_ci", t)
	joff = [([0.5, 0.9], "faster", "established faster"), ([0.9, 1.0], "unresolved_equal_edge", "upper bound equals 1.0 exactly"),
		([1.0, 1.1], "unresolved_equal_edge", "lower bound equals 1.0 exactly"), ([1.01, 1.2], "above", "supports fuel-on being slower"),
		([0.9, 1.1], "unresolved", "contains 1.0")]
	for ci, cat, must in joff:
		t = A.joff_verdict({"ci95": ci})
		check(f"R_joff rule {ci} -> {cat}", A.joff_category(ci) == cat and must in t and scoped(t), t)
	ctl = [
		("R2 fib CI (lower > 1.01)", R2_FIB, "above", ["margin not met", "whole fuel-on/fuel-off interval lies above 1.01", "more than 1% slower", "no attribution to source, hook or builds"], ["unresolved"]),
		("R3 shared_rows CI (straddling, above 1)", R3_SHARED, "unresolved", ["unresolved relative to 1.01", "straddles 1.01"], ["direction also unresolved", "more than 1% slower"]),
		("R2 shared_rows CI (straddling, contains 1)", R2_SHARED, "unresolved", ["unresolved relative to 1.01", "straddles 1.01", "direction also unresolved"], ["more than 1% slower"]),
		("[1.005, 1.02] (straddling)", [1.005, 1.02], "unresolved", ["unresolved relative to 1.01", "straddles"], ["direction also unresolved", "more than 1% slower"]),
		("[0.98, 1.01] (upper == 1.01)", [0.98, 1.01], "met_equal_edge", ["margin met", "upper bound equals 1.01 exactly", "inclusive"], []),
		("[1.01, 1.02] (lower == 1.01)", [1.01, 1.02], "unresolved_equal_edge", ["lower bound equals 1.01 exactly, which is not above 1.01"], ["whole", "more than 1% slower"]),
		("R1 fib CI (met)", R1_FIB, "met", ["margin met (upper bound <= 1.01)", "at most 1% slower"], ["equals"]),
	]
	for name, ci, cat, must, must_not in ctl:
		t = A.control_verdict({"ci95": ci})
		check(f"control margin {name} -> {cat}", A.control_category(ci) == cat and all(m in t for m in must)
			and not any(m in t for m in must_not) and scoped(t) and "proof" not in t, t)
	t = A.control_verdict({"unresolved": "denominator fuel-off: its own bootstrap lower bound is not finite and strictly positive"})
	check("control no interval -> margin not met, unresolved (never met)", t.startswith("margin not met; unresolved") and A.control_category(None) == "unresolved_no_ci", t)


# ---------------------------------------------------------------- end-to-end

def end_to_end_controls():
	out, rc = session("clean", noisy(seed=11))
	v = out["verdicts"]
	want = {
		"calls R_jit met": v["calls"]["R_jit"]["verdict"].startswith("target met"),
		"calls R_joff faster": v["calls"]["R_joff"]["verdict"].startswith("fuel-on established faster"),
		"screens met": all(v[k]["R_jit"]["verdict"].endswith("current acceptance gate met")
			and v[k]["R_joff"]["verdict"].endswith("current acceptance gate met") for k in ("while", "numeric")),
		"controls met": all(v[f"control/{k}"]["verdict"].startswith("margin met") for k in ("fib", "shared_rows")),
		"S descriptive": "ci95" in v["calls"]["S_off_over_on"] and "verdict" not in v["calls"]["S_off_over_on"],
		"tiny descriptive": not verdict_paths(v["calls/tiny"]) and "ci95" in v["calls/tiny"]["fuel-on/fuel-off"],
		"sensitivity beside": all("ci95" in v[k][x]["sensitivity_unflagged_rounds"] and "verdict" not in v[k][x]["sensitivity_unflagged_rounds"]
			for k in ("calls", "while", "numeric") for x in ("R_jit", "R_joff")),
		"r1 descriptive": all(v[k]["r1_context"]["label"].startswith("DESCRIPTIVE CONTEXT ONLY") and "not a paired comparator" in v[k]["r1_context"]["label"]
			and not verdict_paths(v[k]["r1_context"]) for k in ("calls", "while", "numeric")) and v["calls"]["r1_context"]["R_jit"]["ci95"] == [1.26685, 1.27735],
		"code notes": "451 -> 721 bytes" in v["calls"]["code_note"] and "17 -> 15 instructions" in v["calls"]["code_note"]
			and "%r12" in v["calls"]["code_note"] and "fuel >= 2" in v["calls"]["code_note"] and "295 bytes" in v["while"]["code_note"]
			and "552 bytes" in v["numeric"]["code_note"] and all("FUEL" in v[k]["code_note"] for k in ("calls", "while", "numeric")),
		"history verbatim": out["history_verbatim"][0].startswith("B1: fib 1.0039 [0.9861, 1.0121], NOT met → STOP (Codex 8074)")
			and any(h.startswith("R1: fib 0.9963 [0.9895, 1.0023], met.") for h in out["history_verbatim"])
			and any(h.startswith("R2: fib 1.0254 [1.0190828610573877, 1.0387]") for h in out["history_verbatim"])
			and "Both R2 STOPs are honoured. The B1 STOP stands." in out["history_verbatim"]
			and any("close this diagnostic line and resume calls work from the accepted R1 checkpoint" in h for h in out["history_verbatim"])
			and any(h.startswith("R3 (Codex 8312): COMPLETE400valid. Calls R_jit1.260577428765625 [1.2520139992698127,1.2739821493498587] BELOW") for h in out["history_verbatim"])
			and any("shared control1.015650 [1.008755,1.021741] unresolved at1.01 => STOP" in h for h in out["history_verbatim"])
			and out["history_verbatim"][-1] == "Codex 8330: FUEL is semantically accepted, performance unqualified; R1 remains the checkpoint."
			and v["control/fib"]["b1_fib_stop_history"] == out["history_verbatim"][0],
		"disclosures": "8 verdict-bearing marginal 95% intervals" in out["disclosures"]["multiplicity"]
			and "R1 is not a paired comparator and neither is R3" in out["disclosures"]["no_cross_session"]
			and "R3 shared_rows STOP" in out["disclosures"]["no_gate_change"] and "R1 (e1e1f30b) stays the accepted checkpoint" in out["disclosures"]["no_gate_change"]
			and "451 -> 721" in out["disclosures"]["tradeoffs"] and "%r12" in out["disclosures"]["tradeoffs"]
			and "346623b6" in out["disclosures"]["design"] and "FUEL binaries" in out["disclosures"]["design"],
		"joint method": "one index vector per resample" in v["calls"]["R_jit"]["method"] and v["calls"]["R_jit"]["rounds"] == 10,
		"break-even": "invocations" in v["calls"]["break_even"] or "undefined" in v["calls"]["break_even"],
	}
	check("clean session: COMPLETE, every gate met, no STOP, 200 blocks", out["session_status"] == "COMPLETE" and rc == 0
		and out["acceptance_verdicts"] and all(want.values()) and not out["stop_or_review"] and out["schedule"]["accepted_blocks"] == 200,
		f"failed={[k for k, ok in want.items() if not ok]} stop={out['stop_or_review']}")

	# calls PRIMARY: met / below / unresolved; never a STOP by itself.
	for label, fn, prefix in (("met", noisy({("calls/calls_main", "fuel-on"): 1.10}, seed=12), "target met"),
			("below", noisy({("calls/calls_main", "fuel-on"): 1.40}, seed=13), "below target"),
			("unresolved (straddling 1.25)", straddle("calls/calls_main", 1.20, 1.30), "unresolved")):
		out, rc = session("primary-" + label.split()[0], fn)
		j = out["verdicts"]["calls"]["R_jit"]
		ci = j.get("ci95", [None, None])
		ok = (out["session_status"] == "COMPLETE" and j["verdict"].startswith(prefix) and out["verdicts"]["primary"]["calls"] == j["verdict"]
			and not out["stop_or_review"] and all(out["verdicts"][k]["R_jit"]["verdict"].startswith("target met") for k in ("while", "numeric")))
		ok &= ci[1] <= 1.25 if label == "met" else ci[0] > 1.25 if label == "below" else ci[0] <= 1.25 < ci[1]
		check(f"PRIMARY calls R_jit {label} (never a STOP)", ok, f"{j.get('ratio', 0):.4f} {ci} -> '{j['verdict'][:50]}'")

	# Screens: below and unresolved -> STOP; met -> gate met.
	for kernel, cell in (("while", "while/loop_main"), ("numeric", "numeric/loop_main")):
		for label, fn, prefix in (("below", noisy({(cell, "fuel-on"): 1.40}, seed=14), "below target"),
				("unresolved", straddle(cell, 1.20, 1.30), "unresolved")):
			out, rc = session(f"screen-{kernel}-{label}", fn)
			j = out["verdicts"][kernel]["R_jit"]
			stops = [x for x in out["stop_or_review"] if "R_jit" in x]
			check(f"SCREEN {kernel} R_jit {label} -> gate not met -> STOP", j["verdict"].startswith(prefix)
				and j["verdict"].endswith("current acceptance gate not met")
				and stops == [f"{kernel}: current acceptance gate not met (R_jit target not established: {prefix}) -> STOP for review"]
				and out["verdicts"]["screens"][kernel]["R_jit"] == j["verdict"], f"{j.get('ci95')} stops={stops}")
		out, rc = session(f"screen-{kernel}-joff", noisy({(cell, "fuel-on"): 4.4}, seed=15))
		jo = out["verdicts"][kernel]["R_joff"]
		check(f"SCREEN {kernel} R_joff not established -> gate not met -> STOP", jo["verdict"].startswith("NOT established faster")
			and jo["verdict"].endswith("current acceptance gate not met")
			and f"{kernel}: current acceptance gate not met (R_joff upper >= 1.0) -> STOP for review" in out["stop_or_review"],
			jo["verdict"][:80])
	out, rc = session("calls-joff", noisy({("calls/calls_main", "fuel-on"): 4.4}, seed=16))
	jo = out["verdicts"]["calls"]["R_joff"]
	check("calls R_joff not established -> STOP for design review", jo["category"] == "above"
		and "calls: R_joff not established faster (upper >= 1.0) -> STOP for design review of the inline/Replay/entry path" in out["stop_or_review"],
		jo["verdict"][:80])

	# Controls: lower > margin, straddling, equality-adjacent; each a STOP with per-case wording.
	out, rc = session("fib-above", noisy({("fib/fib_main", "fuel-on"): 1.03}, seed=17))
	c = out["verdicts"]["control/fib"]
	check("control fib lower > 1.01 -> scoped >1% statement + STOP", c["category"] == "above" and c["ci95"][0] > 1.01
		and "more than 1% slower than fuel-off" in c["verdict"] and "proof" not in json.dumps(out)
		and any(x.startswith("fib: control margin not met (above)") for x in out["stop_or_review"])
		and out["verdicts"]["control/shared_rows"]["verdict"].startswith("margin met"), c["verdict"][:90])
	out, rc = session("shared-straddle", straddle("shared_rows/shared_rows_main", 0.99, 1.04))
	c = out["verdicts"]["control/shared_rows"]
	check("control shared_rows straddling 1.01 -> unresolved + STOP (no >1% statement)", c["category"] == "unresolved"
		and c["ci95"][0] <= 1.01 < c["ci95"][1] and "unresolved relative to 1.01" in c["verdict"] and "more than 1% slower" not in c["verdict"]
		and any(x.startswith("shared_rows: control margin not met (unresolved)") for x in out["stop_or_review"]), f"{c['ci95']} {c['verdict'][:80]}")
	out, rc = session("fib-edge", noisy({("fib/fib_main", "fuel-on"): 1.0102}, sd=0.0002, seed=18))
	c = out["verdicts"]["control/fib"]
	check("control fib upper just above 1.01 -> not met (no favourable rounding) + STOP", c["ci95"][1] > 1.01 and c["category"] != "met"
		and any(x.startswith("fib: control margin not met") for x in out["stop_or_review"]), f"{c['ci95']} {c['category']}")

	# Sensitivity never replaces primary.
	fl = {("calls/calls_main", s, r) for s in A.ALL for r in range(5)}
	sl = noisy(seed=19)
	slow = lambda c, s, r: base_ns(c, s) * 1.6 if (c, s) == ("calls/calls_main", "fuel-on") and r < 5 else sl(c, s, r)
	out, rc = session("sens-not-primary", slow, flagged=fl)
	j = out["verdicts"]["calls"]["R_jit"]
	check("sensitivity never replaces primary (calls R_jit)", j["verdict"].startswith("unresolved")
		and j["sensitivity_unflagged_rounds"]["ci95"][1] <= 1.25 and j["sensitivity_unflagged_rounds"]["rounds"] == 5 and j["rounds"] == 10
		and "verdict" not in j["sensitivity_unflagged_rounds"], f"primary {j.get('ci95')} sensitivity {j['sensitivity_unflagged_rounds'].get('ci95')}")
	fl = {("while/loop_main", s, r) for s in A.ALL for r in range(5)}
	slow = lambda c, s, r: base_ns(c, s) * 1.6 if (c, s) == ("while/loop_main", "fuel-on") and r < 5 else sl(c, s, r)
	out, rc = session("sens-not-screen", slow, flagged=fl)
	j = out["verdicts"]["while"]["R_jit"]
	check("sensitivity never rescues a screen (while R_jit -> STOP)", j["verdict"].endswith("current acceptance gate not met")
		and j["sensitivity_unflagged_rounds"]["category"] == "met" and any(x.startswith("while: current acceptance gate not met") for x in out["stop_or_review"]))


# ---------------------------------------------------------------- joint bootstrap + mutants

def joint_controls():
	rng = random.Random(7)
	n = 10
	eff = [rng.gauss(0, 0.05) for _ in range(n)]  # a per-round effect shared by every subject
	series = {s: [GOOD_NS[s] * (1 + eff[i] + rng.gauss(0, 0.002)) for i in range(n)] for s in A.ALL}
	ratios = A.cell_ratios("calls/calls_main")
	res, keep = A.joint_bootstrap(series, n, random.Random(99), ratios, keep=True)
	d = keep["draws"]

	def joint_ok(draws, idx):
		"""Every resample's ratios recomputed from ONE index vector."""
		for b in range(0, len(idx), 97):
			med = {s: statistics.median(series[s][i] for i in idx[b]) for s in A.ALL}
			for rid, num, den in ratios:
				if draws[rid][b] != med[num] / med[den]:
					return False
		return True

	check("joint bootstrap: one index vector per resample drives every ratio of the cell", joint_ok(d, keep["idx"]) and len(keep["idx"]) == A.B)
	xs = sorted(d["R_jit"])
	check("joint bootstrap: reported interval = percentiles of the joint draws", res["R_jit"]["ci95"] == [A.pct(xs, 0.025), A.pct(xs, 0.975)])

	def independent(series, n, rng):
		"""MUTANT: numerator and denominator (and each ratio) resampled with independent index vectors."""
		draws, idx = {rid: [] for rid, _, _ in ratios}, []
		for _ in range(A.B):
			i1 = rng.choices(range(n), k=n)
			idx.append(i1)
			for rid, num, den in ratios:
				i2 = rng.choices(range(n), k=n)
				draws[rid].append(statistics.median(series[num][i] for i in i1) / statistics.median(series[den][i] for i in i2))
		return draws, idx

	md, midx = independent(series, n, random.Random(99))
	check("mutant caught: independently resampled ratios fail the one-index-vector check", not joint_ok(md, midx))
	jw = res["R_jit"]["ci95"][1] - res["R_jit"]["ci95"][0]
	mx = sorted(md["R_jit"])
	mw = A.pct(mx, 0.975) - A.pct(mx, 0.025)
	check("mutant is material: with a shared per-round effect the independent interval is much wider", mw > 3 * jw, f"joint {jw:.5f} vs independent {mw:.5f}")
	try:
		A.joint_bootstrap({**series, "luajit": series["luajit"][:-1]}, n, random.Random(1), ratios)
		raised = False
	except ValueError:
		raised = True
	check("joint bootstrap refuses unequal subject round sets", raised)


def sensitivity_controls():
	fl = {("calls/calls_main", "luajit-joff", 2), ("calls/calls_main", "fuel-off", 5), ("fib/fib_main", "fuel-on", 7)}
	out, rc = session("partial-tuple", noisy(seed=21), flagged=fl)
	j = out["verdicts"]["calls"]["R_jit"]["sensitivity_unflagged_rounds"]
	f = out["verdicts"]["control/fib"]["sensitivity_unflagged_rounds"]
	w = out["verdicts"]["while"]["R_jit"]["sensitivity_unflagged_rounds"]
	check("sensitivity uses complete unflagged tuples (a flag on ANY subject drops that round for EVERY ratio of the cell)",
		j["rounds"] == 8 and out["verdicts"]["calls"]["R_joff"]["sensitivity_unflagged_rounds"]["rounds"] == 8
		and out["verdicts"]["calls"]["S_off_over_on"]["sensitivity_unflagged_rounds"]["rounds"] == 8 and f["rounds"] == 9 and w["rounds"] == 10,
		f"calls {j['rounds']}, fib {f['rounds']}, while {w['rounds']}")
	flags = {(s, r): ("calls/calls_main", s, r) in fl for s in A.ALL for r in range(10)}
	good = {rid: A.complete_unflagged_rounds(flags, A.ALL) for rid, _, _ in A.cell_ratios("calls/calls_main")}

	def per_pair(num, den):
		"""MUTANT: per-pair filtering."""
		return [r for r in range(10) if not flags[(num, r)] and not flags[(den, r)]]

	mut = {rid: per_pair(num, den) for rid, num, den in A.cell_ratios("calls/calls_main")}
	ok = lambda sets: all(r == A.complete_unflagged_rounds(flags, A.ALL) for r in sets.values())
	check("mutant caught: partial (per-pair) sensitivity fails the complete-tuple check", ok(good) and not ok(mut),
		f"mutant R_jit uses {len(mut['R_jit'])} rounds vs {len(good['R_jit'])}")
	out, rc = session("all-flagged", noisy(seed=22), flagged={("calls/calls_main", "luajit", r) for r in range(10)})
	s = out["verdicts"]["calls"]["R_jit"]["sensitivity_unflagged_rounds"]
	check("sensitivity with < 2 complete rounds is unresolved; the primary verdict is unaffected",
		s.get("unresolved", "").startswith("fewer than 2") and out["verdicts"]["calls"]["R_jit"]["verdict"].startswith("target met"))


def denominator_controls():
	sl = noisy(seed=31)
	out, rc = session("den-negative", lambda c, s, r: -abs(sl(c, s, r)) if (c, s) == ("while/loop_main", "luajit") else sl(c, s, r))
	j = out["verdicts"]["while"]["R_jit"]
	check("denominator <= 0 at the point estimate: R_jit unresolved, screen gate not met -> STOP",
		"denominator luajit" in j.get("unresolved", "") and "ci95" not in j and j["category"] == "unresolved_no_ci"
		and j["verdict"].endswith("current acceptance gate not met") and any(x.startswith("while: current acceptance gate not met (R_jit") for x in out["stop_or_review"]),
		j.get("unresolved"))
	ratios = [("x", "a", "b")]
	res, _ = A.joint_bootstrap({"a": [5.0] * 10, "b": [0.0] * 4 + [5.0] * 6}, 10, random.Random(5), ratios)
	check("denominator zero in a resample -> unresolved (resample stage)", "bootstrap resample" in res["x"].get("unresolved", ""), res["x"].get("unresolved"))
	res, _ = A.joint_bootstrap({"a": [5.0] * 10, "b": [-1.0] * 3 + [5.0] * 7}, 10, random.Random(5), ratios)
	check("denominator non-positive somewhere -> never a verdict", "unresolved" in res["x"] and "ci95" not in res["x"])
	res, _ = A.joint_bootstrap({"a": [5.0, float("inf")] * 5, "b": [5.0] * 10}, 10, random.Random(5), ratios)
	check("non-finite values -> unresolved, never a verdict", "unresolved" in res["x"])
	out, rc = session("den-control", lambda c, s, r: -abs(sl(c, s, r)) if (c, s) == ("fib/fib_main", "fuel-off") else sl(c, s, r))
	c = out["verdicts"]["control/fib"]
	check("control denominator non-positive -> margin not met, unresolved -> STOP", c["category"] == "unresolved_no_ci"
		and c["verdict"].startswith("margin not met; unresolved") and any(x.startswith("fib: control margin not met") for x in out["stop_or_review"]))


# ---------------------------------------------------------------- suppression

def suppression_controls():
	def bad(blks):
		find(blks, "shared_rows/shared_rows_main", "fuel-on", 3)["samples"]["101000"].update(valid=False, rc=1, reason="rc 1", stderr="boom\n")
	out, rc = session("invalid-sample", noisy(seed=41), mutate=bad)
	expect_no_verdicts("one invalid sample (shared_rows) suppresses ALL intervals and verdicts in EVERY cell", out, rc, "INVALID")
	check("the invalid block is listed, not dropped; descriptive medians kept", len(out["invalid_blocks"]) == 1
		and out["cells"]["calls/calls_main"]["fuel-on"]["n_valid_blocks"] == 10 and out["cells"]["shared_rows/shared_rows_main"]["fuel-on"]["n_valid_blocks"] == 9)

	def bad2(blks):
		find(blks, "calls/calls_main", "luajit-joff", 4)["samples"]["100"].update(valid=False, rc=1, reason="rc 1", stderr="lua: error\n")
	out, rc = session("invalid-primary", noisy(seed=42), mutate=bad2)
	expect_no_verdicts("one invalid sample (calls luajit-joff) suppresses the controls and screens too", out, rc, "INVALID")

	def native(blks):
		find(blks, "calls/calls_main", "fuel-on", 2)["samples"]["100"].update(valid=False, reason="INVALID NATIVE EXIT",
			stderr="rune fresh-core-native: INVALID native region exit (X) in function f at header pc 3\n")
	out, rc = session("native-exit", noisy(seed=43), mutate=native)
	expect_no_verdicts("invalid native exit suppresses ALL verdicts", out, rc, "INVALID")
	check("invalid native exit is global and leads the STOP list", out["invalid_native_exit"] and out["stop_or_review"][0].startswith("SESSION INVALID"))

	def native_valid(blks):
		find(blks, "while/loop_main", "fuel-on", 0)["samples"]["1000"]["stderr"] = "INVALID native region exit (Y)\n"
	out, rc = session("native-text-valid-flag", noisy(seed=44), mutate=native_valid)
	expect_no_verdicts("invalid native exit text in a sample marked valid", out, rc, "INVALID")

	blks = blocks(noisy(seed=45))
	blks.remove(find(blks, "fib/fib_main", "fuel-off", 4))
	out, rc = analyze("missing-block", [header()] + blks + [footer(blks, complete=False, stopped="only 199 of 200 blocks collected", rc=1, blocks_collected=199)])
	expect_no_verdicts("missing pair (one block) suppresses ALL verdicts", out, rc, "INCOMPLETE")
	out, rc = analyze("missing-block-complete-footer", [header()] + blks + [footer(blks)])
	expect_no_verdicts("footer claims completion with a missing block -> INVALID", out, rc, "INVALID")
	blks = [b for b in blocks(noisy(seed=46)) if not (b["subject"] == "luajit" and b["kernel"] == "numeric")]
	out, rc = analyze("missing-subject", [header()] + blks + [footer(blks, complete=False, stopped="x", rc=1)])
	expect_no_verdicts("missing subject in a cell suppresses ALL verdicts", out, rc, "INCOMPLETE")


def footer_binding_controls():
	blks = blocks(noisy(seed=51))
	H = header()
	cases = [
		("no footer", [H] + blks, None, "INCOMPLETE"),
		("footer stopped", [H] + blks + [footer(blks, complete=False, stopped="deadline", rc=1)], None, "INCOMPLETE"),
		("footer with error", [H] + blks + [footer(blks, error="Traceback ...")], None, "INCOMPLETE"),
		("footer counts wrong (199 collected)", [H] + blks + [footer(blks, blocks_collected=199)], None, "INVALID"),
		("footer samples_checked wrong", [H] + blks + [footer(blks, samples_checked=398)], None, "INVALID"),
		("footer valid=False with all samples valid", [H] + blks + [footer(blks, valid=False, rc=3)], None, "INVALID"),
		("footer valid=True rc=3", [H] + blks + [footer(blks, rc=3)], None, "INVALID"),
		("footer without rc", [H] + blks + [{k: v for k, v in footer(blks).items() if k != "rc"}], None, "INVALID"),
		("two footers", [H] + blks + [footer(blks), footer(blks)], None, "INVALID"),
		("records after the footer", [H] + blks[:-1] + [footer(blks), blks[-1]], None, "INVALID"),
		("truncated last line", [H] + blks, '{"record": "foo', "INCOMPLETE"),
		("empty raw file", [], None, "INCOMPLETE"),
		("two headers", [H, H] + blks + [footer(blks)], None, "INVALID"),
		("no header", blks + [footer(blks)], None, "INVALID"),
		("wrong session seed", [header(seed=SEED + 1)] + blks + [footer(blks)], None, "INVALID"),
		("wrong manifest seed", [header(manifest_seed=1)] + blks + [footer(blks)], None, "INVALID"),
		("old header: revision r3 (R3)", [header(probe="rnx-0184-r3-probe revision r3")] + blks + [footer(blks)], None, "INVALID"),
		("old header: revision 6 (R2)", [header(probe="rnx-0184-r2-probe revision 6")] + blks + [footer(blks)], None, "INVALID"),
		("old header: ctl4", [header(probe="rnx-0184-ctl4-probe revision ctl4")] + blks + [footer(blks)], None, "INVALID"),
		("old header: stage 2", [header(probe="rnx-0184-stage2-probe revision s2")] + blks + [footer(blks)], None, "INVALID"),
		("old header: revision 5 (R1)", [header(probe="rnx-0184-r1-probe revision 5")] + blks + [footer(blks)], None, "INVALID"),
		("old header: revision 4 (W13)", [header(probe="rnx-0184-w13-probe revision 4")] + blks + [footer(blks)], None, "INVALID"),
		("old header: revision 3 (B1, no probe field)", [{k: v for k, v in H.items() if k != "probe"}] + blks + [footer(blks)], None, "INVALID"),
		("old header: no subjects field (revision 6 shape)", [{k: v for k, v in H.items() if k != "subjects"}] + blks + [footer(blks)], None, "INVALID"),
		("header subjects r3-on/r3-off", [header(subjects=["luajit", "luajit-joff", "r3-on", "r3-off"])] + blks + [footer(blks)], None, "INVALID"),
		("header subjects r2-on/r2-off", [header(subjects=["luajit", "luajit-joff", "r2-on", "r2-off"])] + blks + [footer(blks)], None, "INVALID"),
		("header cell table with r3 subjects", [header(cells=[[k, s, [x.replace("fuel", "r3") for x in subs]] for k, s, subs in A.CELLS])] + blks + [footer(blks)], None, "INVALID"),
		("header cell table with r2 subjects", [header(cells=[[k, s, [x.replace("fuel", "r2") for x in subs]] for k, s, subs in A.CELLS])] + blks + [footer(blks)], None, "INVALID"),
		("header ctl4 cell table", [header(cells=[["fib", "fib_main", ["r1-on", "r1-off", "r2-on", "r2-off"]], ["shared_rows", "shared_rows_main", ["r1-on", "r1-off", "r2-on", "r2-off"]]])] + blks + [footer(blks)], None, "INVALID"),
		("20 rounds per cell (ctl4)", [header(rounds_per_cell=20)] + blks + [footer(blks)], None, "INVALID"),
		("wrong controller sha256", [header(controller_sha256="0" * 64)] + blks + [footer(blks)], None, "INVALID"),
		("wrong bounds", [header(session_bound_s=9999)] + blks + [footer(blks)], None, "INVALID"),
	]
	for label, mut in (("fuel-on hash zeroed", lambda p: p["rune_harness"]["fuel-on"].update(sha256="0" * 64)),
			("the R3 binaries' pins", lambda p: p.update(rune_harness={
				"r3-on": {"path": "/home/me/work/.targets/rune-r3-probe-on/release/p2-probe-harness", "sha256": "e6970c0bbf03b7dec8b0df5d30ff043f6f8057d933f8f66ed1c1e12e75247f03"},
				"r3-off": {"path": "/home/me/work/.targets/rune-r3-probe-off/release/p2-probe-harness", "sha256": "f9605991027ca2a674573f265882c77797b3f8b8ae9342b07aefa07655a37d5b"}})),
			("the R3 binaries' hashes under the fuel names", lambda p: (p["rune_harness"]["fuel-on"].update(sha256="e6970c0bbf03b7dec8b0df5d30ff043f6f8057d933f8f66ed1c1e12e75247f03"),
				p["rune_harness"]["fuel-off"].update(sha256="f9605991027ca2a674573f265882c77797b3f8b8ae9342b07aefa07655a37d5b"))),
			("the R3 commit and worktree", lambda p: p["rune"].update(commit="088d8245a121506420b4011d7ee4aaa00c48a613", tree="1451e0d86f50d92022ee269741f00de349f82a4b", worktree="/home/me/work/.worktrees/rune-r3-probe")),
			("the R2 binaries' pins", lambda p: p.update(rune_harness={
				"r2-on": {"path": "/home/me/work/.targets/rune-r2-probe-on/release/p2-probe-harness", "sha256": "1ca4f3ce8fa6d281446220cd817551e06eee960071889fb662cf023a3b3a4d17"},
				"r2-off": {"path": "/home/me/work/.targets/rune-r2-probe-off/release/p2-probe-harness", "sha256": "98a0eb15668692860cd62f6928013b7ec467c737869dd74338a67ea14e4edf1e"}})),
			("the R1 binaries' pins", lambda p: p.update(rune_harness={
				"r1-on": {"path": "/home/me/work/.targets/rune-r1-probe-on/release/p2-probe-harness", "sha256": "4a4fe287dceb24e8aee19a42ce5d0ae2197b0f10f95e286c077055dc04950b71"},
				"r1-off": {"path": "/home/me/work/.targets/rune-r1-probe-off/release/p2-probe-harness", "sha256": "23d4d1916eb0e6a240715531c1b691cf99556ecf7f2a358539a078b7f2c97105"}})),
			("the R2 commit and worktree", lambda p: p["rune"].update(commit="74ee506e68b2cd2960ac8148bed3763e11fd6aa2", worktree="/home/me/work/.worktrees/rune-r2-probe")),
			("a different toolchain", lambda p: p["toolchain"].update(rustc_vV="rustc 1.95.0")),
			("a different workspace lock", lambda p: p["rune"].update(workspace_lock_sha256="d29a1d7f0bf79d0d3e05bb9dbad447c55392cc3a52d79572096297aebfef5a38"))):
		p = copy.deepcopy(PINS)
		mut(p)
		cases.append((f"header pins differ ({label})", [header(pins=p)] + blks + [footer(blks)], None, "INVALID"))
	for name, recs, tail, status in cases:
		out, rc = analyze("bind-" + "".join(ch if ch.isalnum() else "_" for ch in name), recs, tail)
		expect_no_verdicts(f"safeguard: {name} -> {status}", out, rc, status)

	fakes = {f"foreign subject {s}": (lambda s: lambda b: b[0].update(subject=s))(s)
		for s in ("r3-on", "r3-off", "r2-on", "r2-off", "r1-on", "r1-off", "w13-on", "b1-on", "p2-on", "c1-on", "c2-on", "off")}
	fakes.update({
		"foreign: luajit in a control cell": lambda b: next(x for x in b if x["kernel"] == "fib").update(subject="luajit"),
		"foreign: dropped while/tiny cell": lambda b: b[0].update(kernel="while", stream="tiny", round=0),
		"round 10 (beyond the seal)": lambda b: b[0].update(round=10),
		"duplicate block": lambda b: b.append(copy.deepcopy(b[0])),
		"wrong position": lambda b: b[0].update(position=b[0]["position"] + 1),
		"missing position (revision 6 block shape)": lambda b: b[0].pop("position"),
		"wrong K order": lambda b: b[0].update(order=list(reversed(b[0]["order"]))),
		"extra sample": lambda b: b[0]["samples"].update({"5": b[0]["samples"][str(b[0]["order"][0])]}),
		"one K sample missing": lambda b: b[0]["samples"].pop(str(b[0]["order"][0])),
		"non-int wall": lambda b: b[0]["samples"][str(b[0]["order"][0])].update(wall_ns=1.5),
		"flag not bool": lambda b: b[0].update(flagged="no"),
	})
	for name, fn in fakes.items():
		b2 = copy.deepcopy(blks)
		fn(b2)
		out, rc = analyze("ident-" + "".join(ch if ch.isalnum() else "_" for ch in name), [H] + b2 + [footer(b2)])
		expect_no_verdicts(f"schedule identity: {name} -> INVALID", out, rc, "INVALID")


def prior_raw_controls():
	for label, (path, sha) in PRIOR_RAW.items():
		have = A.sha256_file(path) if os.path.exists(path) else "<missing>"
		out, rc = A.analyze(path, MANIFEST_PATH)
		OUTPUTS.append(("real-" + label, out))
		ok = (have == sha and rc == 4 and out["session_status"] == "INVALID" and not out["acceptance_verdicts"]
			and any("refused: this is a real prior session raw file" in e for e in out["errors"]["invalid"])
			and any("header probe differs" in e for e in out["errors"]["invalid"]) and out.get("descriptive_suppressed")
			and not verdict_paths(out["verdicts"]) and A.sha256_file(path) == sha)
		check(f"real prior raw file refused: {label}", ok, f"sha {have[:12]} rc={rc} (read only, unchanged)")


# ---------------------------------------------------------------- controller controls

class FakeClock:
	def __init__(self):
		self.t = 0.0

	def __call__(self):
		return self.t


def parse_cmd(cmd):
	"""(subject, kernel, k, stream) from a controller argv; None for the LuaJIT status child."""
	if "-e" in cmd:
		return None
	if cmd[0] == C.BINS["fuel-on"]:
		subject = "fuel-on"
	elif cmd[0] == C.BINS["fuel-off"]:
		subject = "fuel-off"
	else:
		subject = "luajit-joff" if "-joff" in cmd else "luajit"
	i = next(n for n, a in enumerate(cmd) if a.endswith((".rn", ".lua")) and a.split(".")[0] in ("while", "numeric", "calls", "fib", "shared_rows"))
	stream = os.path.basename(cmd[i + 2]).split(".")[0]
	return subject, cmd[i].split(".")[0], int(cmd[i + 1]), stream


class FakeRunner:
	"""Replaces controller.run_child: never runs a process; fabricates the child's output."""

	def __init__(self, fault=None, clock=None, step_s=0.0, maps_override=None):
		self.calls, self.fault, self.clock, self.step_s, self.maps_override = [], fault, clock, step_s, maps_override

	def __call__(self, cmd, timeout=C.CHILD_TIMEOUT_S, timed=False, extra_env=None):
		n = len(self.calls)
		self.calls.append(cmd)
		if self.clock:
			self.clock.t += self.step_s
		p = parse_cmd(cmd)
		if p is None or "markers" in cmd:
			return {"argv": cmd, "rc": 0, "timed_out": False, "stderr": "", "stdout_sha256": ""}, ""
		subject, kernel, k, stream = p
		info = MANIFEST["cells"][f"{kernel}/{stream}"]
		checksum = info["expected_checksum"][str(k)] if str(k) in info["expected_checksum"] else None
		out = ""
		if cmd[-1] in ("--transcript", "transcript"):
			lines = open(os.path.join(HERE, "inputs", info["expected_path"])).read().split("\n")[:k]
			out = "\n".join(lines) + "\n"
		out += f"CHECKSUM {checksum} invocations={k}\n"
		if subject in C.RUNE:
			m = C.EXPECTED_MAPPINGS[(subject, kernel)]
			if self.maps_override and (subject, kernel, cmd[-1] == "--transcript") in self.maps_override:
				m = self.maps_override[(subject, kernel, cmd[-1] == "--transcript")]
			out += f"MAPS anon_exec_mappings={m} anon_exec_kib={4 * m}\n"
		rec = {"argv": cmd, "rc": 0, "timed_out": False, "stderr": "", "stdout_sha256": hashlib.sha256(out.encode()).hexdigest()}
		if self.fault:
			self.fault(n, subject, kernel, rec)
		if rec.get("raise"):
			raise rec["raise"]
		if timed:
			rec["wall_ns"] = int(1_000_000 + k * base_ns(f"{kernel}/{stream}", subject))
		return rec, out


@contextlib.contextmanager
def patched(runner, validate_result=True, clock=None):
	saved = (C.run_child, C.validate, C.now_s)
	C.run_child = runner
	C.validate = lambda out_dir, max_k=None, deadline=None: (os.makedirs(out_dir), validate_result)[1]
	if clock:
		C.now_s = clock
	try:
		yield
	finally:
		C.run_child, C.validate, C.now_s = saved


def run_controller(name, runner, clock=None, bound_s=None, validate_result=True, seed=SEED):
	out_dir = os.path.join(WORK, "ctl-" + name)
	os.makedirs(out_dir)
	buf = io.StringIO()
	with patched(runner, validate_result, clock), contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
		rc = C.run(out_dir, seed, deadline=C.Deadline(bound_s))
	raw = os.path.join(out_dir, "raw.jsonl")
	recs = [json.loads(l) for l in open(raw)] if os.path.exists(raw) else []
	foot = recs[-1] if recs and recs[-1]["record"] == "footer" else None
	return rc, buf.getvalue(), foot, raw


def controller_controls():
	vt = C.Validity()
	check("final_rc truth table", C.final_rc(True, vt) == 0 and C.final_rc(False, vt) == 1
		and (vt.add({}, {"valid": False, "reason": "rc 1"}) or C.final_rc(True, vt) == 3)
		and (vt.add({}, {"valid": False, "reason": "INVALID NATIVE EXIT"}) or C.final_rc(True, vt) == 4) and C.final_rc(False, vt) == 1)
	runner = FakeRunner()
	rc, text, foot, raw = run_controller("valid", runner)
	recs = [json.loads(l) for l in open(raw)]
	check("controller: valid session (400 children, positions recorded, header subjects)", rc == 0 and foot["complete"] and foot["valid"]
		and len(runner.calls) == 400 and "SESSION complete, all 400 samples valid; rc 0" in text
		and all(r.get("position") == r.get("block") for r in recs if r["record"] == "block") and recs[0]["subjects"] == A.ALL, f"rc={rc}")
	out, arc = A.analyze(raw, MANIFEST_PATH)
	OUTPUTS.append(("ctl-valid", out))
	check("controller->analyzer: valid session COMPLETE with verdicts", out["session_status"] == "COMPLETE" and arc == 0 and out["acceptance_verdicts"]
		and out["verdicts"]["calls"]["R_jit"]["verdict"].startswith("target met") and not out["stop_or_review"], f"rc={arc} stop={out['stop_or_review'][:2]}")
	rc, text, foot, raw = run_controller("foreign-seed", FakeRunner(), seed=SEED + 1)
	check("controller: a seed other than SESSION-SEED.txt is refused (rc 1, nothing run, no raw file)", rc == 1 and not os.path.exists(raw) and "not the sealed" in text)

	def bad_rc(n, subject, kernel, rec):
		if n == 17:
			rec.update(rc=1, stderr="error:boom\n")
	runner = FakeRunner(fault=bad_rc)
	rc, text, foot, raw = run_controller("invalid-sample", runner)
	check("controller: invalid sample kept, all 400 children still run, rc 3", rc == 3 and foot["complete"] and not foot["valid"]
		and len(foot["invalid_samples"]) == 1 and len(runner.calls) == 400 and "SESSION INVALID" in text)
	out, arc = A.analyze(raw, MANIFEST_PATH)
	OUTPUTS.append(("ctl-invalid", out))
	expect_no_verdicts("controller->analyzer: invalid sample suppresses ALL verdicts", out, arc, "INVALID")

	def timeout(n, subject, kernel, rec):
		if n == 3:
			rec.update(rc=None, timed_out=True, stderr="partial\n")
	rc, text, foot, raw = run_controller("timeout", FakeRunner(fault=timeout))
	check("controller: child timeout", rc == 3 and foot["invalid_samples"][0]["reason"] == "timeout")
	fired = []

	def native(n, subject, kernel, rec):
		if n >= 40 and subject in C.RUNE and not fired:
			fired.append(n)
			rec.update(stderr="rune fresh-core-native: INVALID native region exit (Y) ...\n")
	rc, text, foot, raw = run_controller("native", FakeRunner(fault=native))
	check("controller: invalid native exit (first Rune child at or after child 40)", fired and rc == 4 and foot["invalid_native_exit"], f"fired {fired}")
	out, arc = A.analyze(raw, MANIFEST_PATH)
	OUTPUTS.append(("ctl-native", out))
	expect_no_verdicts("controller->analyzer: invalid native exit", out, arc, "INVALID")

	clock = FakeClock()
	runner = FakeRunner(clock=clock, step_s=10.0)
	rc, text, foot, raw = run_controller("deadline-session", runner, clock=clock, bound_s=1000)
	check("controller: all-phases deadline exceeded in the timed session", rc == 1 and not foot["complete"]
		and "all phases" in (foot["stopped"] or "") and len(runner.calls) < 400)
	out, arc = A.analyze(raw, MANIFEST_PATH)
	OUTPUTS.append(("ctl-deadline", out))
	expect_no_verdicts("controller->analyzer: deadline-stopped session", out, arc, "INCOMPLETE")
	runner = FakeRunner()
	rc, text, foot, raw = run_controller("validation-fails", runner, validate_result=False)
	check("controller: validation failed -> no timing", rc == 1 and not os.path.exists(raw) and not runner.calls)

	def real_validate(name, runner, clock=None, bound=None):
		saved = (C.run_child, C.now_s, C.verify_pins, C.nm_check, C.libraries)
		C.run_child, C.verify_pins, C.nm_check, C.libraries = runner, (lambda: (True, [])), (lambda: (True, {})), (lambda b: {})
		if clock:
			C.now_s = clock
		d = os.path.join(WORK, "ctl-validate-" + name)
		try:
			with contextlib.redirect_stdout(io.StringIO()):
				if bound:
					rc = C.run(d, SEED, deadline=C.Deadline(bound))
					return rc, d
				ok = C.validate(d)
		finally:
			C.run_child, C.now_s, C.verify_pins, C.nm_check, C.libraries = saved
		return ok, d

	clock = FakeClock()
	runner = FakeRunner(clock=clock, step_s=100.0)
	rc, d = real_validate("deadline", runner, clock, bound=1000)
	val = [json.loads(l) for l in open(os.path.join(d, "validation", "validate.jsonl"))]
	check("controller: the deadline covers validation", rc == 1 and not os.path.exists(os.path.join(d, "raw.jsonl"))
		and val[-1]["step"] == "footer" and not val[-1]["passed"] and "all phases" in (val[-1]["stopped"] or "") and len(runner.calls) == 11,
		f"{len(runner.calls)} validation children")
	ok, d = real_validate("pass", FakeRunner())
	val = [json.loads(l) for l in open(os.path.join(d, "validate.jsonl"))]
	tr = [r for r in val if r["step"] == "1-transcript" and r["subject"] in C.RUNE]
	check("controller validate (fake runner): PASSED with pre-registered transcript MAPS", ok and len(tr) == 12
		and all(r["ok"] and r["maps"][0] == C.EXPECTED_MAPPINGS[(r["subject"], r["kernel"])] for r in tr)
		and all(r["identical"] for r in val if r["step"] == "1-on-off-identical"))
	for label, override in (("admission MAPS=0 for fuel-on calls", {("fuel-on", "calls", False): 0}),
			("transcript MAPS=0 for fuel-on calls (stricter than revision 6)", {("fuel-on", "calls", True): 0}),
			("admission MAPS=1 for fuel-on fib", {("fuel-on", "fib", False): 1}),
			("transcript MAPS=1 for fuel-off while", {("fuel-off", "while", True): 1})):
		ok, d = real_validate("maps-" + "".join(ch if ch.isalnum() else "_" for ch in label), FakeRunner(maps_override=override))
		check(f"controller validate: {label} -> FAILED", ok is False)

	def boom(n, subject, kernel, rec):
		if n == 99:
			rec["raise"] = RuntimeError("synthetic failure")
	rc, text, foot, raw = run_controller("exception", FakeRunner(fault=boom))
	check("controller: exception mid-session keeps the traceback", rc == 1 and not foot["complete"] and "RuntimeError" in (foot["error"] or ""))

	def interrupt(n, subject, kernel, rec):
		if n == 5:
			rec["raise"] = KeyboardInterrupt()
	rc, text, foot, raw = run_controller("interrupt", FakeRunner(fault=interrupt))
	check("controller: SIGINT (KeyboardInterrupt) mid-session", rc == 1 and "KeyboardInterrupt" in foot["stopped"])
	out, arc = A.analyze(raw, MANIFEST_PATH)
	OUTPUTS.append(("ctl-interrupt", out))
	expect_no_verdicts("controller->analyzer: interrupted session", out, arc, "INCOMPLETE")


# ---------------------------------------------------------------- wording guards (last)

def wording_controls():
	hits = {n: o["wording_violations"] for n, o in OUTPUTS if o.get("wording_violations")}
	check(f"wording guard: no banned word or attribution phrase in any analyzer output ({len(OUTPUTS)})", OUTPUTS and not hits,
		f"{dict(list(hits.items())[:2])}")
	blanket = [n for n, o in OUTPUTS if "not proof" in json.dumps({k: v for k, v in o.items() if k != "history_verbatim"}).lower()]
	check("no blanket 'not proof of a slowdown' wording in any output", not blanket, str(blanket[:3]))
	missing = [n for n, o in OUTPUTS if o.get("history_verbatim") != A.HISTORY]
	check(f"history quoted verbatim in every output ({len(OUTPUTS)})", not missing, str(missing[:3]))
	positives = ["the excess comes from fuel-on", "this is proof of a slowdown", "caused by placement", "a regression",
		"an r3-specific source effect", "layout noise", "general build variance is small", "due to alignment",
		"this explains the gap", "we promote R3", "joint coverage 95%", "attributable to the hook", "reverses the B1 STOP",
		"R3 improved calls", "R3 is faster", "faster than R1 now", "an R3 speedup", "R3 wins", "a clear gain",
		"the excess comes from fuel-on", "a fuel-specific source effect", "we promote FUEL", "FUEL improved calls",
		"FUEL is faster", "fuel made calls quicker", "faster than R3 now", "a FUEL speedup", "FUEL wins"]
	fired = [p for p in positives if A.wording_violations([p])]
	check(f"wording guard positive control: every planted phrase fires ({len(positives)})", fired == positives,
		f"missed {[p for p in positives if p not in fired]}")
	allowed = [A.NO_GATE_CHANGE, A.NO_CROSS_SESSION, A.MULTIPLICITY, A.R1_CONTEXT_LABEL, A.TRADEOFFS] + list(A.CODE_NOTES.values())
	check("wording guard: the sealed negated disclaimers and code notes do not fire", not A.wording_violations(allowed), str(A.wording_violations(allowed)[:2]))
	saved = dict(A.CODE_NOTES)
	A.CODE_NOTES["calls"] = "the excess comes from the FUEL lowering"
	try:
		out, rc = session("wording-planted", noisy(seed=61))
	finally:
		A.CODE_NOTES.clear()
		A.CODE_NOTES.update(saved)
	check("wording guard fires inside the analyzer and withdraws the verdicts (rc 4)", out["wording_violations"] and rc == 4
		and not out["acceptance_verdicts"] and "wording guard fired: verdicts withdrawn" in out["errors"]["invalid"])


def main():
	print(f"synthetic controls; fabricated files under {WORK}; no subject runs, nothing timed")
	seal_controls()
	wording_unit_controls()
	end_to_end_controls()
	joint_controls()
	sensitivity_controls()
	denominator_controls()
	suppression_controls()
	footer_binding_controls()
	prior_raw_controls()
	controller_controls()
	wording_controls()
	failed = [c for c, ok, _ in RESULTS if not ok]
	print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} controls passed")
	for c in failed:
		print("FAILED:", c)
	return 1 if failed else 0


if __name__ == "__main__":
	sys.exit(main())
