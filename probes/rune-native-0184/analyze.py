#!/usr/bin/env python3
"""FUEL probe: analysis (rnx 0184), revision "fuel" of the P2 probe analyzer: revision r3's design (the
R3 probe, ../../0184-r3-probe1/probe/analyze.py: revision 6's design with the ctl4 statistical
safeguards) with the FUEL subject (346623b6). Reads the controller's raw.jsonl; writes
JSON to stdout. No aggregate across kernels, no best-of-N, no post-hoc deletion, retry or tuning.

Authority: Codex GO seq 8330 (../CODEX-GO-8330.txt), applying the R3 probe design accepted under
Codex GO seq 8294. All decisions below are declared before any measurement (../READINESS.md).
Revision fuel changes, relative to revision r3, ONLY: the subjects (fuel-on, fuel-off), the header
`probe` field, the per-(cell, set) RNG stream prefix ("fuel:"), the prior-raw refusal list (adds the
R3 session raw), the static code notes and tradeoffs, and the context and history text (R3 quoted
as history; R1 stays the checkpoint, with descriptive r1_context only).

usage: analyze.py RAW.jsonl MANIFEST.json
       (the bootstrap seed is the sealed BOOT-SEED.txt beside this file; there is no seed argument)

Design (revision 6's and r3's, unchanged):

- A CURRENT ACCEPTANCE SCREEN of the FUEL binaries (346623b6) against LuaJIT in this session. No R1
  (or R3, R2, W13, B1) binary is a subject: R1 is not a paired comparator, and neither is R3. The
  R1 session's figures are DESCRIPTIVE CONTEXT ONLY (`r1_context`); no cross-session claim of any kind is made.
- calls/calls_main is the SOLE PRIMARY for the LuaJIT target: R_jit = fuel-on / luajit (bare LuaJIT,
  the primary comparator) on its own CI; upper <= 1.25 "target met"; lower > 1.25 "below target";
  anything else (lower <= 1.25 < upper, lower == 1.25 exactly, or no CI) "unresolved". [1.20,
  1.25] is met; [1.25, 1.30] is unresolved; [1.2500001, 1.30] is below. Unrounded bounds. The
  calls R_jit verdict is never itself a STOP.
- while/loop_main and numeric/loop_main are CURRENT ACCEPTANCE SCREENS with the same target rule:
  "target met" -> "current acceptance gate met"; anything else -> "current acceptance gate not
  met" -> STOP for review.
- R_joff = fuel-on / luajit-joff (the secondary comparator): calls upper < 1.0 "established faster",
  otherwise STOP for design review of the inline/Replay/entry path; while and numeric: current
  within-session acceptance gates (otherwise STOP for review).
- fib and shared_rows are the controls: fuel-on / fuel-off, margin upper <= 1.01 (else STOP).
- calls/tiny is a fixed-cost diagnostic (no threshold); harness overhead is included.
- K1/K2, 10 rounds per cell, 200 blocks / 400 children / 60 rounds, bounds 120 s / 5,400 s: as
  revision 6 (no adaptive inputs, no tuning).

Statistics (ctl4 safeguards):

- Block slope: (wall(K2) - wall(K1)) / (K2 - K1), ns per invocation, parent CLOCK_MONOTONIC.
- PRIMARY: ALL 10 scheduled rounds of every cell, used ONLY when the whole session is valid
  (COMPLETE, every sample of every block valid, every (cell, round, subject) present exactly once,
  no invalid native exit). GLOBAL INVALID SUPPRESSION: any invalid sample anywhere, any invalid
  native exit, or any missing pair or subject suppresses ALL inferential intervals and verdicts in
  EVERY cell; no round is dropped to rescue an analysis. Descriptive per-subject medians remain
  unless provenance is unknown (structural or binding error).
- SENSITIVITY: per cell, only the rounds in which ALL blocks of that cell (every subject) are
  unflagged by the readiness rule (complete tuples: the same round set for every subject and
  every contrast of the cell; never per-pair sets). Beside the primary, never instead; it has a
  category but no verdict and never changes a verdict or a STOP.
- JOINT paired-round resampling: per (cell, set), each of B = 10,000 resamples draws ONE vector of
  round indices with replacement and applies it to every subject of the cell; every ratio of that
  resample (R_jit, R_joff, S_off_over_on; the tiny ratios; the control on/off) and the break-even
  terms come from the medians over that one vector. One RNG stream per (cell, set), seeded from
  BOOT-SEED.txt.
- Denominators must be finite and strictly positive at every stage: the point estimate, every
  resample, and the denominator's own bootstrap lower bound; otherwise that ratio is
  "unresolved: denominator ...", never a verdict.
- 95% percentile intervals, unrounded. Multiplicity: the primary carries 8 verdict-bearing
  marginal 95% intervals (calls, while, numeric R_jit and R_joff; fib and shared_rows controls),
  each read on its own; no joint or family-wise coverage is claimed.

Per-case wording (Codex 8294, unchanged under 8330):

- Controls (margin M = 1.01): upper <= 1.01 "margin met" (upper == 1.01 exactly is met, spelled
  out); lower > 1.01 "the whole interval lies above 1.01: under this model it supports fuel-on being
  more than 1% slower than fuel-off, for these binaries in this session" (a scoped >1% statement);
  lower == 1.01 exactly is NOT above (unresolved, spelled out); otherwise the interval straddles
  1.01 and the result is UNRESOLVED ("direction also unresolved" when it contains 1). A failed
  margin is a STOP in every case. No blanket disclaimer is attached to a failed margin.
- R_joff (1.0): upper < 1.0 established faster; upper == 1.0 exactly not established (spelled
  out); lower > 1.0 "the whole interval lies above 1.0: supports fuel-on being slower than
  luajit-joff, for these binaries in this session"; otherwise not established and unresolved.
- R_jit (1.25): as above, with the equality cases spelled out.
- A wording guard scans every emitted string except the verbatim history; if a banned word or
  attribution phrase appears, all verdicts are withdrawn (rc 4).

Safeguards (fail-closed, revision 6 plus ctl4): exactly one header (first) and one footer (last);
a complete footer (complete true, no stop/error, 200 of 200 blocks, 400 samples checked, valid/rc
consistent with the blocks); the header bound to this probe (probe = revision fuel, session seed =
SESSION-SEED.txt, manifest seed and sha256 = PINS.json, header pins = PINS.json, controller sha256,
subjects, cells, rounds, bounds, expected counts); this analyzer equal to its PINS.json pin; the
block set equal to the seeded schedule (every (cell, round, subject) exactly once, at its
round_index / block / position with its K order, holding exactly its K1 and K2 samples); known
prior session raw files (P2, B1, W13, R1, R2, ctl4, stage 2, R3) refused by sha256. Exit status: 0
COMPLETE, 3 INCOMPLETE, 4 INVALID (the JSON is written in every case).
"""
import hashlib, json, math, os, random, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))

B = 10_000
JOFF_STOP = 1.0
JIT_TARGET = 1.25
CONTROL_MARGIN = 1.01
SCOPE = "for these binaries in this session"

# The sealed schedule. Must equal controller.py; test_analyze.py checks.
ROUNDS = 10
ALL = ["luajit", "luajit-joff", "fuel-on", "fuel-off"]
RUNE = ["fuel-on", "fuel-off"]
PROBE = "rnx-0184-fuel-probe revision fuel"
PRIMARY = "calls"  # the SOLE PRIMARY, declared before any measurement
SCREENS = ("while", "numeric")  # CURRENT ACCEPTANCE SCREENS, same target rule
CELLS = [
	("calls", "calls_main", ALL),
	("calls", "tiny", ALL),
	("while", "loop_main", ALL),
	("numeric", "loop_main", ALL),
	("fib", "fib_main", RUNE),
	("shared_rows", "shared_rows_main", RUNE),
]
SEALED_K = {
	"calls/calls_main": (100, 10100), "calls/tiny": (1000, 101000),
	"while/loop_main": (1000, 101000), "numeric/loop_main": (1000, 101000),
	"fib/fib_main": (100, 10100), "shared_rows/shared_rows_main": (1000, 101000),
}
SEAL_CELLS = 6
SEAL_ROUNDS = 60  # 6 cells x 10 rounds
SEAL_BLOCKS = 200  # 4 cells x 4 subjects + 2 cells x 2 subjects = 20 per round index, x 10
SEAL_CHILDREN = 400
CHILD_TIMEOUT_S = 120
SESSION_BOUND_S = 5400
INVALID_EXIT_TEXT = "INVALID native region exit"
RC = {"COMPLETE": 0, "INCOMPLETE": 3, "INVALID": 4}

# Real prior session raw files: refused outright (in addition to failing every binding check).
KNOWN_PRIOR_RAW = {
	"f94735f5edc35d436262d902b8529809983c12d9009783f3e3a3b2cf827253cb": "P2 session (0184-p2-probe1)",
	"547a3ea68f351c30eba0c9905c28407ed896be5325134e29403b47c8a14ca78f": "B1 session (0184-b1-session1)",
	"7d498f588a0efd12089b58d36a7356c8db5565648fa982c5691ffff3e6c59d1c": "W13 session (0184-w13-session1)",
	"f5d60aab54f5eb881b9acb1281cc86bf5159a5c8852c2a6235f0ecf88ca8280e": "R1 session (0184-r1-session1)",
	"dddf3a15caf92dcb5136257c263943c8429c3e48d18f4b0ee57cb10dabfb80e5": "R2 session (0184-r2-session1)",
	"0ee977613dcc89119a9e252aa9b2883fa54112f55a923ab845ebc10825adfffa": "ctl4 session (0184-ctl4-session1)",
	"80ab2579139e64b596f46b7ab9b834fac775bae52cfff664adb242b38b0f2d0c": "stage-2 session (0184-stage2-session1)",
	"8ef0930a710d1377e3f4389252ee77506adc039ed1a34e2a5ac3e30e687c85f8": "R3 session (0184-r3-session1)",
}

# The R1 session (0184-r1-session1, COMPLETE 400/400, analyzer rc 0; r1-on/r1-off at e1e1f30b; raw
# f5d60aab...): DESCRIPTIVE CONTEXT ONLY, as revision 6 quoted it. Different binaries and session;
# R1 is not a subject here and not a paired comparator; no interval is formed across sessions.
R1_CONTEXT = {
	"calls": {"R_joff": {"ratio": 0.09158, "ci95": [0.09134, 0.09220], "r1_category": "established faster than luajit-joff"},
		"R_jit": {"ratio": 1.27084, "ci95": [1.26685, 1.27735], "r1_category": "below target (calls was the sole primary)"}},
	"while": {"R_joff": {"ratio": 0.15945, "ci95": [0.15803, 0.16109], "r1_category": "established faster than luajit-joff; current acceptance gate met"},
		"R_jit": {"ratio": 1.03329, "ci95": [1.02599, 1.04626], "r1_category": "target met; current acceptance gate met"}},
	"numeric": {"R_joff": {"ratio": 0.24820, "ci95": [0.24776, 0.24868], "r1_category": "established faster than luajit-joff; current acceptance gate met"},
		"R_jit": {"ratio": 0.44583, "ci95": [0.44487, 0.44616], "r1_category": "target met; current acceptance gate met"}},
	"fib": {"on_over_off": {"ratio": 0.99634, "ci95": [0.98946, 1.00226], "r1_category": "control margin met"}},
	"shared_rows": {"on_over_off": {"ratio": 0.97076, "ci95": [0.96392, 0.98941], "r1_category": "control margin met"}},
}
R1_CONTEXT_LABEL = ("DESCRIPTIVE CONTEXT ONLY (R1 session 0184-r1-session1, r1-on/r1-off at e1e1f30b): R1 is not a "
	"subject and not a paired comparator in this session; no interval across sessions; no cross-session causal claim")
# The history, verbatim (FOLLOWUP-DESIGN.md section 0 as quoted by the ctl4 analyzer; the R2 STOP
# lines; Codex 8276's closure of the controls diagnostic line; as the R3 analyzer quoted them), then
# the R3 session's figures as Codex 8312 quoted them (0184-r3-session1 RESULTS.json; CLOSEOUT.md)
# and Codex 8312's and 8330's checkpoint sentences. Quoted, never re-judged, and the only text
# exempt from the wording guard.
HISTORY = [
	"B1: fib 1.0039 [0.9861, 1.0121], NOT met → STOP (Codex 8074). shared_rows 0.9837 [0.9782, 0.9894], met.",
	"W13: fib 0.9935 [0.98796, 1.0088], met. shared_rows 0.9812 [0.9771, 0.9872], met.",
	"R1: fib 0.9963 [0.9895, 1.0023], met. shared_rows 0.9708 [0.9639, 0.9894], met.",
	"R2: fib 1.0254 [1.0190828610573877, 1.0387]. The lower bound is above 1.01, so under the sealed model the whole "
	"interval supports feature-on being >1% slower than feature-off for these binaries in that session (no "
	"attribution). shared_rows 1.0229 [0.9452, 1.0333]: NOT met, direction and margin unresolved.",
	"Both R2 STOPs are honoured. The B1 STOP stands.",
	"Codex 8276: Choose (c): close this diagnostic line and resume calls work from the accepted R1 checkpoint "
	"e1e1f30b, preserving R2 and all diagnostic branches/artifacts.",
	"R3 (Codex 8312): COMPLETE400valid. Calls R_jit1.260577428765625 [1.2520139992698127,1.2739821493498587] BELOW "
	"target; while/numeric screens met; fib met; shared control1.015650 [1.008755,1.021741] unresolved at1.01 => STOP. "
	"Honor that stop, no rerun/promotion; R1 remains checkpoint.",
	"Codex 8312: the machine-code reduction is established but a timing benefit over R1 is not.",
	"Codex 8330: FUEL is semantically accepted, performance unqualified; R1 remains the checkpoint.",
]
NO_GATE_CHANGE = ("No outcome of this probe promotes, demotes or reverses any prior gate: the B1 fib STOP, the R2 "
	"double STOP and the R3 shared_rows STOP stand, and R1 (e1e1f30b) stays the accepted checkpoint; a qualification "
	"here attaches to the two pinned FUEL binaries only.")
NO_CROSS_SESSION = ("R1 is not a paired comparator and neither is R3: there is no R1 or R3 binary in this session, so no "
	"cross-session causal claim is made and no FUEL-vs-R1 or FUEL-vs-R3 interval is formed; the R1 figures are "
	"descriptive context only and the R3 figures are quoted history only.")
MULTIPLICITY = ("Multiplicity: the primary has 8 verdict-bearing marginal 95% intervals (calls, while and numeric R_jit and "
	"R_joff; the fib and shared_rows controls), each read on its own, of which 7 can lead to a STOP (calls R_jit "
	"cannot); no joint or family-wise coverage is claimed and none is implied. The sensitivity intervals are beside the "
	"primary, are not independent of it and never replace it. No verdict is formed across kernels.")
# FUEL's static code facts (0184-fuel-impl1 LISTINGS.md; this package's release listing, byte-equal to
# listings/after), stated beside the results as facts about the code only.
CODE_NOTES = {
	"calls": ("static fact about the code only: FUEL changed the V2 calls region's machine code relative to its parent "
		"R1 (451 -> 721 bytes; static steady-state loop path 17 -> 15 instructions, 4 -> 3 conditional branches, 74 -> "
		"65 loop bytes; the per-iteration fuel check is one guard (fuel >= 2) before a single folded decrement of 2, "
		"with the callee pc-0 check gone from the hot loop; an exact slow copy for fuel 0 or 1; a new callee-saved "
		"%r12 save and per-exit restores; function instructions 106 -> 168); static instruction counts predict "
		"nothing about timing (HWC1)"),
	"while": ("static fact about the code only: FUEL left the while region's machine code byte-identical to R1's "
		"(295 bytes); identical machine bytes do not guarantee identical process timing"),
	"numeric": ("static fact about the code only: FUEL left the numeric region's machine code byte-identical to "
		"R1's (552 bytes); identical machine bytes do not guarantee identical process timing"),
}
TRADEOFFS = ("Disclosed tradeoffs (Codex 8330), relevant and not acceptance blockers: the new %r12 save/restore and "
	"the calls region growing 451 -> 721 bytes; 17 -> 15 instructions does not establish a speedup. FUEL census "
	"(Codex 8330, independently reproduced): 28 selected changes, 298 unselected identical, the same 10 refusals.")

# Wording guard: banned words or attribution/causal language in any emitted text except HISTORY.
# The allowed negated phrases are removed before scanning.
BANNED = [r"regression", r"\bproofs?\b", r"\bproves?\b", r"\bproven\b", r"\bcaus(e|es|ed|ing|al)\b", r"r3-specific", r"fuel-specific",
	r"source effect", r"layout noise", r"comes? from", r"\bdue to\b", r"because of", r"attribut", r"explain",
	r"\bthe excess\b", r"build variance", r"build-to-build", r"\bresponsible\b", r"\bdriven by\b",
	r"\bjoint(ly)? coverage\b", r"family-wise", r"\bpromot", r"\bdemot", r"\brevers", r"improv", r"thanks to",
	r"\bvictory\b", r"\bwins?\b", r"\bgains?\b", r"\br[0-9]+ (is|was) (faster|slower|better|worse|quicker)\b",
	r"\br[0-9]+ (made|makes|helped|sped)\b", r"\bfuel (is|was) (faster|slower|better|worse|quicker)\b",
	r"\bfuel (made|makes|helped|sped)\b",
	r"(faster|slower|better|worse) than (r1|r2|r3|w13|b1)\b", r"speedup (from|by|of) (r[0-9]|fuel)", r"(r[0-9]+|fuel) speedup"]
ALLOWED_NEGATED = ["no attribution to source, hook or builds", "no joint or family-wise coverage is claimed and none is implied",
	"no outcome of this probe promotes, demotes or reverses any prior gate", "no cross-session causal claim is made",
	"no cross-session causal claim"]


class SealArithmeticError(Exception):
	pass


def derived_counts():
	"""Blocks and children implied by the cells and rounds; must equal the seal's numbers."""
	blocks = ROUNDS * sum(len(subjects) for _, _, subjects in CELLS)
	if (blocks, 2 * blocks) != (SEAL_BLOCKS, SEAL_CHILDREN):
		raise SealArithmeticError(f"cells x rounds imply {blocks} blocks / {2 * blocks} children; "
			f"the seal says {SEAL_BLOCKS} / {SEAL_CHILDREN}")
	if ROUNDS * len(CELLS) != SEAL_ROUNDS:
		raise SealArithmeticError(f"cells x rounds imply {ROUNDS * len(CELLS)} rounds; the seal says {SEAL_ROUNDS}")
	if len(CELLS) != SEAL_CELLS or set(SEALED_K) != {f"{k}/{s}" for k, s, _ in CELLS}:
		raise SealArithmeticError(f"cell table differs from the sealed {SEAL_CELLS} cells")
	return blocks, 2 * blocks


def sha256_file(path):
	h = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(1 << 20), b""):
			h.update(chunk)
	return h.hexdigest()


def boot_seed():
	return int(open(os.path.join(HERE, "BOOT-SEED.txt")).read().strip())


def schedule(seed, manifest):
	"""Byte-for-byte the controller's schedule(): same RNG calls in the same order."""
	rng = random.Random(seed)
	rounds = [(kernel, stream, subjects, r) for kernel, stream, subjects in CELLS for r in range(ROUNDS)]
	rng.shuffle(rounds)
	out = []
	for kernel, stream, subjects, r in rounds:
		info = manifest["cells"][f"{kernel}/{stream}"]
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


def pct(sorted_xs, q):
	i = min(len(sorted_xs) - 1, max(0, int(q * len(sorted_xs))))
	return sorted_xs[i]


def finite_pos(x):
	return x is not None and isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def phases(text):
	if not text:
		return None
	out = {}
	for line in text.splitlines():
		k, v = line.split()
		out[k] = None if v == "na" else int(v)
	return out


# ------------------------------------------------------------------ verdict wording

def jit_category(ci):
	if not ci:
		return "unresolved_no_ci"
	lo, hi = ci
	if hi <= JIT_TARGET:
		return "met_equal_edge" if hi == JIT_TARGET else "met"
	if lo > JIT_TARGET:
		return "below"
	if lo == JIT_TARGET:
		return "unresolved_equal_edge"
	return "unresolved"


def jit_target_verdict(rec):
	"""The sealed LuaJIT target rule on unrounded bounds (per-case wording)."""
	ci = rec.get("ci95") if isinstance(rec, dict) else None
	if not ci:
		why = rec.get("unresolved", "missing") if isinstance(rec, dict) else "missing"
		return f"unresolved: no ratio interval ({why}); no target verdict, {SCOPE}"
	cat = jit_category(ci)
	if cat == "met":
		return f"target met: upper bound <= 1.25, so fuel-on at >= 80% of bare LuaJIT speed is supported, {SCOPE}"
	if cat == "met_equal_edge":
		return (f"target met: the upper bound equals 1.25 exactly and the rule is upper <= 1.25 (inclusive), so fuel-on at "
			f">= 80% of bare LuaJIT speed is supported, {SCOPE}")
	if cat == "below":
		return f"below target: the whole interval lies above 1.25 (lower bound > 1.25), {SCOPE}"
	if cat == "unresolved_equal_edge":
		return (f"unresolved: the lower bound equals 1.25 exactly, which is not above 1.25, and the upper bound exceeds "
			f"1.25 (no favourable rounding), {SCOPE}")
	return (f"unresolved: the interval straddles 1.25 (lower <= 1.25 < upper), neither wholly at or below 1.25 nor "
		f"wholly above it (no favourable rounding), {SCOPE}")


def joff_category(ci):
	if not ci:
		return "unresolved_no_ci"
	lo, hi = ci
	if hi < JOFF_STOP:
		return "faster"
	if hi == JOFF_STOP:
		return "unresolved_equal_edge"
	if lo > JOFF_STOP:
		return "above"
	if lo == JOFF_STOP:
		return "unresolved_equal_edge"
	return "unresolved"


def joff_verdict(rec):
	ci = rec.get("ci95") if isinstance(rec, dict) else None
	if not ci:
		why = rec.get("unresolved", "missing") if isinstance(rec, dict) else "missing"
		return f"unresolved: no ratio interval ({why}); not established faster than luajit-joff, {SCOPE}"
	cat = joff_category(ci)
	lo, hi = ci
	if cat == "faster":
		return f"fuel-on established faster than luajit-joff (upper bound < 1.0), {SCOPE}"
	if cat == "above":
		return (f"NOT established faster than luajit-joff: the whole interval lies above 1.0 (lower bound > 1.0), so it "
			f"supports fuel-on being slower than luajit-joff, {SCOPE}")
	if cat == "unresolved_equal_edge" and hi == JOFF_STOP:
		return (f"NOT established faster than luajit-joff: the upper bound equals 1.0 exactly, which is not below 1.0; "
			f"unresolved, {SCOPE}")
	if cat == "unresolved_equal_edge":
		return (f"NOT established faster than luajit-joff: the lower bound equals 1.0 exactly, which is not above 1.0, "
			f"and the upper bound exceeds 1.0; direction unresolved, {SCOPE}")
	return (f"NOT established faster than luajit-joff: the interval contains 1.0 (lower < 1.0 < upper); direction "
		f"unresolved, {SCOPE}")


def control_category(ci):
	if not ci:
		return "unresolved_no_ci"
	lo, hi = ci
	if hi <= CONTROL_MARGIN:
		return "met_equal_edge" if hi == CONTROL_MARGIN else "met"
	if lo > CONTROL_MARGIN:
		return "above"
	if lo == CONTROL_MARGIN:
		return "unresolved_equal_edge"
	return "unresolved"


def control_verdict(rec):
	"""Per-case control wording (Codex 8294): lower > 1.01 supports the scoped >1% statement; a
	straddling interval is unresolved; equalities spelled out."""
	ci = rec.get("ci95") if isinstance(rec, dict) else None
	pair = "fuel-on/fuel-off"
	if not ci:
		why = rec.get("unresolved", "missing") if isinstance(rec, dict) else "missing"
		return f"margin not met; unresolved: no {pair} interval ({why}), {SCOPE}"
	cat = control_category(ci)
	lo, hi = ci
	if cat == "met":
		return (f"margin met (upper bound <= 1.01): the {pair} interval supports fuel-on being at most 1% slower than "
			f"fuel-off, {SCOPE}")
	if cat == "met_equal_edge":
		return (f"margin met: the upper bound equals 1.01 exactly, and the rule is upper <= 1.01 (inclusive); the {pair} "
			f"interval supports fuel-on being at most 1% slower than fuel-off, {SCOPE}")
	if cat == "above":
		return (f"margin not met: the whole {pair} interval lies above 1.01 (lower bound > 1.01); under this model it "
			f"supports fuel-on being more than 1% slower than fuel-off, {SCOPE}; no attribution to source, hook or builds")
	if cat == "unresolved_equal_edge":
		return (f"margin not met; unresolved relative to 1.01: the {pair} lower bound equals 1.01 exactly, which is not "
			f"above 1.01, and the upper bound exceeds 1.01, {SCOPE}")
	direction = "; direction also unresolved (the interval contains 1)" if lo <= 1 <= hi else ""
	return (f"margin not met; unresolved relative to 1.01: the {pair} interval straddles 1.01 (lower <= 1.01 < "
		f"upper){direction}, {SCOPE}")


def wording_violations(texts):
	bad = []
	for t in texts:
		low = t.lower()
		for ok in ALLOWED_NEGATED:
			low = low.replace(ok, "")
		for pat in BANNED:
			if re.search(pat, low):
				bad.append((pat, t))
	return bad


def strings(obj, skip=("history_verbatim",)):
	"""Every string in an output object, except the verbatim history."""
	if isinstance(obj, str):
		return [obj]
	if isinstance(obj, dict):
		return [s for k, v in obj.items() if k not in skip for s in strings(v, skip)]
	if isinstance(obj, list):
		return [s for v in obj for s in strings(v, skip)]
	return []


# --------------------------------------------------------------------- loading

def load(raw_path):
	"""(records, invalid, incomplete). A malformed line is INVALID unless it is the last line
	(a truncated write: INCOMPLETE); a last line without newline is INCOMPLETE."""
	invalid, incomplete, records = [], [], []
	text = open(raw_path, "rb").read().decode("utf-8", errors="replace")
	if not text:
		incomplete.append("empty raw file")
		return records, invalid, incomplete
	lines = text.split("\n")
	terminated = lines[-1] == ""
	if terminated:
		lines.pop()
	else:
		incomplete.append("last line not newline-terminated (truncated session)")
	for n, line in enumerate(lines):
		last = n == len(lines) - 1
		try:
			rec = json.loads(line)
		except ValueError:
			(incomplete if last and not terminated else invalid).append(f"line {n + 1}: not JSON")
			continue
		if not isinstance(rec, dict) or rec.get("record") not in ("header", "block", "footer"):
			invalid.append(f"line {n + 1}: not a header/block/footer record")
			continue
		records.append(rec)
	return records, invalid, incomplete


def check_session(records, manifest, manifest_path, raw_path):
	"""The fail-closed schedule, binding and footer checks. Returns (header, blocks, footer,
	invalid, incomplete, structural, n_expected); `structural` errors also suppress the
	descriptive statistics."""
	invalid, incomplete, structural = [], [], []
	raw_sha = sha256_file(raw_path)
	if raw_sha in KNOWN_PRIOR_RAW:
		structural.append(f"refused: this is a real prior session raw file ({KNOWN_PRIOR_RAW[raw_sha]}), not a FUEL session")
	headers = [r for r in records if r["record"] == "header"]
	footers = [r for r in records if r["record"] == "footer"]
	header = headers[0] if len(headers) == 1 else None
	footer = footers[0] if len(footers) == 1 else None
	if not records:
		incomplete.append("no records (session never started timing)")
	elif len(headers) != 1:
		structural.append(f"expected exactly one header, found {len(headers)}")
	elif records[0] is not header:
		structural.append("the header is not the first record")
	if len(footers) > 1:
		structural.append(f"expected exactly one footer, found {len(footers)}")
	elif not footers:
		if records:
			incomplete.append("no footer (session missing, killed or truncated)")
	elif records[-1] is not footer:
		structural.append("records after the footer")

	pins = json.load(open(os.path.join(HERE, "PINS.json")))
	seed = int(open(os.path.join(HERE, "SESSION-SEED.txt")).read().strip())
	if sha256_file(os.path.abspath(__file__)) != pins["files"]["analyze.py"]:
		structural.append("this analyzer differs from its PINS.json pin")
	if sha256_file(manifest_path) != pins["files"]["inputs/MANIFEST.json"]:
		structural.append("manifest sha256 differs from PINS.json")
	for cell, (k1, k2) in SEALED_K.items():
		info = manifest["cells"].get(cell)
		if info is None or (info["k1"], info["k2"]) != (k1, k2):
			structural.append(f"manifest K1/K2 for {cell} differ from the seal ({k1}, {k2})")
	if header is not None:
		want = {"probe": PROBE, "seed": seed, "manifest_seed": manifest.get("seed"), "pins": pins,
			"rounds_per_cell": ROUNDS, "cells": json.loads(json.dumps(CELLS)), "subjects": ALL,
			"child_timeout_s": CHILD_TIMEOUT_S, "session_bound_s": SESSION_BOUND_S,
			"expected_blocks": SEAL_BLOCKS, "expected_children": SEAL_CHILDREN,
			"controller_sha256": sha256_file(os.path.join(HERE, "controller.py"))}
		for key, value in want.items():
			if header.get(key) != value:
				structural.append(f"header {key} differs from the sealed value")

	expected = {}
	for i, rnd in enumerate(schedule(seed, manifest)):
		for j, blk in enumerate(rnd["blocks"]):
			ident = (f"{rnd['kernel']}/{rnd['stream']}", rnd["round"], blk["subject"])
			expected[ident] = {"round_index": i, "block": j, "order": blk["order"]}
	blocks = {}
	for b in (r for r in records if r["record"] == "block"):
		try:
			ident = (f"{b['kernel']}/{b['stream']}", b["round"], b["subject"])
		except (KeyError, TypeError):
			structural.append("block record without kernel/stream/round/subject")
			continue
		if ident not in expected:
			structural.append(f"foreign block {ident}")
			continue
		if ident in blocks:
			structural.append(f"duplicate block {ident}")
			continue
		e = expected[ident]
		if (b.get("round_index"), b.get("block"), b.get("position"), b.get("order")) != (e["round_index"], e["block"], e["block"], e["order"]):
			structural.append(f"block {ident} differs from the sealed schedule position/order")
			continue
		k1, k2 = SEALED_K[ident[0]]
		s = b.get("samples")
		if not isinstance(s, dict) or set(s) != {str(k1), str(k2)}:
			structural.append(f"block {ident} does not hold exactly its K1/K2 samples")
			continue
		bad = [k for k, rec in s.items() if not isinstance(rec, dict) or not isinstance(rec.get("valid"), bool)
			or (rec["valid"] and not isinstance(rec.get("wall_ns"), int))]
		if bad or not isinstance(b.get("flagged"), bool):
			structural.append(f"block {ident} has a malformed sample or flag")
			continue
		blocks[ident] = b
	missing = sorted(set(expected) - set(blocks))
	if missing:
		incomplete.append(f"{len(missing)} scheduled block(s) missing, first {missing[:3]}")

	# The complete-footer check (ctl4).
	if footer is not None:
		if footer.get("complete") is not True:
			incomplete.append("footer does not record completion")
		if footer.get("stopped"):
			incomplete.append(f"session stopped: {footer['stopped']}")
		if footer.get("error"):
			incomplete.append("session ended with an exception (footer error)")
		if footer.get("complete") is True:
			if missing:
				structural.append("footer claims completion but scheduled blocks are missing")
			if (footer.get("blocks_collected"), footer.get("expected_blocks"), footer.get("samples_checked")) != (SEAL_BLOCKS, SEAL_BLOCKS, SEAL_CHILDREN):
				structural.append(f"footer counts differ from the sealed {SEAL_BLOCKS} blocks / {SEAL_CHILDREN} samples")
			if not isinstance(footer.get("valid"), bool) or footer.get("rc") not in (0, 3, 4):
				structural.append("footer valid/rc missing or inconsistent with a complete session")
			else:
				any_invalid = any(not smp["valid"] for b in blocks.values() for smp in b["samples"].values())
				if footer["valid"] == any_invalid or (footer["rc"] == 0) != footer["valid"]:
					structural.append("footer valid/rc inconsistent with the block samples")
	invalid.extend(structural)
	return header, blocks, footer, invalid, incomplete, structural, len(expected)


# ------------------------------------------------------------------- statistics

def joint_bootstrap(series, n, rng, ratios, diffs=(), keep=False):
	"""series: {name: [value per used round, 0..n-1]}, the SAME n rounds for every name.
	ratios: [(id, num, den)]; diffs: [(id, a, b)] (median(a) - median(b)). Each of B resamples
	draws ONE index vector and applies it to every series; every statistic of that resample comes
	from those medians. Denominators must be finite and > 0 at the point, in every resample, and
	at their own bootstrap lower bound. Returns ({id: record}, keep_data or None)."""
	for name, xs in series.items():
		if len(xs) != n:
			raise ValueError("unequal round sets: the joint bootstrap needs complete tuples")
	ids = [r[0] for r in ratios] + [d[0] for d in diffs]
	if n < 2:
		return {i: {"unresolved": f"fewer than 2 complete rounds ({n})"} for i in ids}, None
	names = sorted(series)
	if any(not all(isinstance(x, (int, float)) and math.isfinite(x) for x in series[nm]) for nm in names):
		return {i: {"unresolved": "a non-finite value in the series"} for i in ids}, None
	point = {nm: statistics.median(series[nm]) for nm in names}
	draws = {i: [] for i in ids}
	med_draws = {nm: [] for nm in names}
	failed = {}
	idx_log = [] if keep else None
	for rid, num, den in ratios:
		if not finite_pos(point[den]):
			failed[rid] = "point estimate"
	for b in range(B):
		idx = rng.choices(range(n), k=n)
		if keep:
			idx_log.append(idx)
		med = {nm: statistics.median(series[nm][i] for i in idx) for nm in names}
		for nm in names:
			med_draws[nm].append(med[nm])
		for rid, num, den in ratios:
			if not finite_pos(med[den]):
				failed.setdefault(rid, f"bootstrap resample {b}")
				draws[rid].append(None)
			else:
				draws[rid].append(med[num] / med[den])
		for did, a, c in diffs:
			draws[did].append(med[a] - med[c])
	out = {}
	for rid, num, den in ratios:
		rec = {"rounds": n, "method": f"joint percentile bootstrap over complete round tuples, B={B}; one index vector per resample for every subject of the cell"}
		den_lo = pct(sorted(med_draws[den]), 0.025)
		if rid in failed:
			rec["unresolved"] = f"denominator {den} not finite and strictly positive ({failed[rid]})"
		elif not finite_pos(den_lo):
			rec["unresolved"] = f"denominator {den}: its own bootstrap lower bound is not finite and strictly positive"
		else:
			xs = sorted(draws[rid])
			rec.update({"ratio": point[num] / point[den], "ci95": [pct(xs, 0.025), pct(xs, 0.975)],
				"denominator_lower_bound": den_lo})
		out[rid] = rec
	for did, a, c in diffs:
		xs = sorted(draws[did])
		out[did] = {"rounds": n, "difference": point[a] - point[c], "ci95": [pct(xs, 0.025), pct(xs, 0.975)],
			"method": f"joint percentile bootstrap, B={B}"}
	return out, ({"draws": draws, "idx": idx_log, "point_medians": point} if keep else None)


def rng_for(seed, cell, which):
	return random.Random(f"fuel:{seed}:{cell}:{which}")


def complete_unflagged_rounds(flags, subjects):
	"""flags: {(subject, round): flagged}. The rounds in which EVERY subject's block is unflagged."""
	rounds = sorted({r for _, r in flags})
	return [r for r in rounds if all(flags.get((s, r)) is False for s in subjects)]


def cell_ratios(cell):
	"""The joint ratio set of a cell: (id, num, den)."""
	kernel, stream = cell.split("/")
	if stream == "tiny":
		return [("fuel-on/luajit", "fuel-on", "luajit"), ("fuel-on/luajit-joff", "fuel-on", "luajit-joff"),
			("fuel-on/fuel-off", "fuel-on", "fuel-off")]
	if kernel in ("fib", "shared_rows"):
		return [("on_over_off", "fuel-on", "fuel-off")]
	return [("R_jit", "fuel-on", "luajit"), ("R_joff", "fuel-on", "luajit-joff"), ("S_off_over_on", "fuel-off", "fuel-on")]


# ---------------------------------------------------------------------- analysis

def analyze(raw_path, manifest_path):
	"""Returns (results, exit status)."""
	expected_blocks, expected_children = derived_counts()
	seed_b = boot_seed()
	manifest = json.load(open(manifest_path))
	records, invalid, incomplete = load(raw_path)
	header, blocks, footer, inv2, inc2, structural, n_expected = check_session(records, manifest, manifest_path, raw_path)
	invalid += inv2
	incomplete += inc2
	assert n_expected == expected_blocks, (n_expected, expected_blocks)
	out = {"probe": PROBE, "boot_seed": seed_b, "B": B, "session_seed": header.get("seed") if header else None,
		"session_status": None, "acceptance_verdicts": False,
		"errors": {"invalid": invalid, "incomplete": incomplete},
		"schedule": {"expected_blocks": expected_blocks, "expected_children": expected_children,
			"accepted_blocks": len(blocks), "accepted_children": 2 * len(blocks),
			"identity_check": "every (cell, round, subject) of the seeded schedule exactly once, at its round_index/block/position with its K order"},
		"session_stopped": (footer.get("stopped") if footer else "no footer (incomplete session)"),
		"invalid_blocks": [], "invalid_native_exit": False, "cells": {}, "verdicts": {}}
	if structural:
		blocks = {}
		out["descriptive_suppressed"] = "structural or binding error: provenance unknown"

	slopes, flags, firsts, e2e = {}, {}, {}, {}
	for (cell, rnd, subject), b in sorted(blocks.items()):
		info = manifest["cells"][cell]
		k1, k2 = str(info["k1"]), str(info["k2"])
		s = b["samples"]
		flags.setdefault(cell, {})[(subject, rnd)] = b["flagged"]
		if not (s[k1]["valid"] and s[k2]["valid"]):
			out["invalid_blocks"].append({"cell": cell, "round": rnd, "subject": subject,
				"reasons": {k: s[k].get("reason") for k in (k1, k2)}})
			continue
		slope = (s[k2]["wall_ns"] - s[k1]["wall_ns"]) / (info["k2"] - info["k1"])
		if not math.isfinite(slope):
			out["invalid_blocks"].append({"cell": cell, "round": rnd, "subject": subject, "reasons": "non-finite slope"})
			continue
		slopes.setdefault(cell, {}).setdefault(subject, {})[rnd] = slope
		f = []
		for k in (k1, k2):
			p = phases(s[k].get("phases"))
			if p and p.get("first") is not None and p.get("ready") is not None:
				f.append(p["first"] - p["ready"])
		if f:
			firsts.setdefault(cell, {}).setdefault(subject, {})[rnd] = f
		e2e.setdefault(cell, {}).setdefault(subject, {})[rnd] = s[k2]["wall_ns"]
	# A native invalid exit anywhere in the raw file makes the session globally invalid.
	for rec in records:
		if rec["record"] == "block" and isinstance(rec.get("samples"), dict):
			for smp in rec["samples"].values():
				if isinstance(smp, dict) and (INVALID_EXIT_TEXT in (smp.get("stderr") or "") or smp.get("reason") == "INVALID NATIVE EXIT"):
					out["invalid_native_exit"] = True
	if out["invalid_native_exit"]:
		invalid.append("INVALID NATIVE EXIT observed: the session is globally invalid")
	if out["invalid_blocks"]:
		invalid.append(f"{len(out['invalid_blocks'])} invalid block(s): ALL inferential intervals and verdicts suppressed in every cell (no round is dropped)")

	status = "INVALID" if invalid else "INCOMPLETE" if incomplete else "COMPLETE"
	out["session_status"] = status
	allowed = status == "COMPLETE"
	if allowed:
		for kernel, stream, subjects in CELLS:
			cell = f"{kernel}/{stream}"
			for sub in subjects:
				if set(slopes.get(cell, {}).get(sub, {})) != set(range(ROUNDS)):
					allowed = False
	out["acceptance_verdicts"] = allowed
	why = None if allowed else (f"session {status} or a missing/invalid pair, subject or sample: ALL inferential intervals "
		"and verdicts suppressed in every cell")

	# Descriptive per-subject statistics (no interval; kept unless provenance is unknown).
	for kernel, stream, subjects in CELLS:
		cell = f"{kernel}/{stream}"
		info = manifest["cells"][cell]
		c = {}
		for sub in subjects:
			xs = list(slopes.get(cell, {}).get(sub, {}).values())
			rec = {"n_valid_blocks": len(xs), "median_slope_ns": statistics.median(xs) if xs else None, "label": "descriptive"}
			if "tail_body_iterations" in info and xs:
				per = [v * (info["k2"] - info["k1"]) / info["tail_body_iterations"] for v in xs]
				rec["derived_per_iteration_ns"] = {"median": statistics.median(per),
					"tail_body_iterations": info["tail_body_iterations"], "label": "DERIVED, descriptive"}
			f = [x for v in firsts.get(cell, {}).get(sub, {}).values() for x in v]
			rec["first_invocation_ns_literal"] = ({"n": len(f), "median": statistics.median(f), "min": min(f), "max": max(f)} if f else None)
			e = list(e2e.get(cell, {}).get(sub, {}).values())
			rec["end_to_end_k2_ns"] = {"n": len(e), "median": statistics.median(e)} if e else None
			c[sub] = rec
		if stream == "tiny":
			c["label"] = ("fixed-cost-dominated diagnostic (harness overhead, invoke, entry/guard, iterator read/commit, "
				"checksum and 0..3 loop iterations included)")
		out["cells"][cell] = c

	def contrast_sets(cell, subjects):
		"""(primary, sensitivity) joint records for a cell; break-even terms included for the
		calls/while/numeric cells when every round has a first-invocation figure for both Rune
		subjects."""
		ratios = cell_ratios(cell)
		res = {}
		for which, rounds, label in (
				("primary", list(range(ROUNDS)), f"PRIMARY: all {ROUNDS} scheduled rounds (the whole session is valid)"),
				("sensitivity", complete_unflagged_rounds(flags[cell], subjects),
					"SENSITIVITY: only rounds in which every block of this cell is unflagged; beside the primary, never instead")):
			series = {s: [slopes[cell][s][r] for r in rounds] for s in subjects}
			diffs = []
			if cell.split("/")[1] != "tiny" and "luajit" in subjects and all(r in firsts.get(cell, {}).get(s, {}) for s in RUNE for r in rounds):
				for s in RUNE:
					series["first:" + s] = [statistics.median(firsts[cell][s][r]) for r in rounds]
				diffs = [("warmed_saving_ns", "fuel-off", "fuel-on"), ("first_invocation_extra_ns", "first:fuel-on", "first:fuel-off")]
			recs, _ = joint_bootstrap(series, len(rounds), rng_for(seed_b, cell, which), ratios, diffs)
			res[which] = {"label": label, "rounds_used": rounds, "n_rounds": len(rounds), "records": recs}
		return res

	v = out["verdicts"]
	stop = []
	sets = {}
	if allowed:
		for kernel, stream, subjects in CELLS:
			cell = f"{kernel}/{stream}"
			sets[cell] = contrast_sets(cell, subjects)

	def beside(cell, rid, category_fn):
		"""The primary record of a ratio with its sensitivity beside it (category only, no verdict)."""
		p = dict(sets[cell]["primary"]["records"][rid])
		srec = dict(sets[cell]["sensitivity"]["records"][rid])
		srec["category"] = category_fn(srec.get("ci95"))
		srec["label"] = sets[cell]["sensitivity"]["label"] + f" ({sets[cell]['sensitivity']['n_rounds']} rounds)"
		p["sensitivity_unflagged_rounds"] = srec
		p["category"] = category_fn(p.get("ci95"))
		p["interval"] = "marginal 95% interval, read on its own (see multiplicity)"
		return p

	def break_even(cell):
		if not allowed:
			return {"suppressed": why}
		recs = sets[cell]["primary"]["records"]
		saving, extra = recs.get("warmed_saving_ns"), recs.get("first_invocation_extra_ns")
		if saving and extra and saving["ci95"][0] > 0:
			be = extra["difference"] / saving["difference"]
			return {"invocations": be if be > 0 else 0, "first_invocation_extra_ns": extra, "warmed_saving_ns": saving,
				"label": "DERIVED, report only (joint resampling over the same rounds)"}
		return {"undefined": "no positive warmed saving established", "warmed_saving_ns": saving,
			"label": "DERIVED, report only"}

	for kernel, cell in (("calls", "calls/calls_main"), ("while", "while/loop_main"), ("numeric", "numeric/loop_main")):
		if kernel == PRIMARY:
			role = ("SOLE PRIMARY (R_jit = fuel-on / bare luajit, the LuaJIT target, declared before measurement; judged on its "
				"own interval, no aggregate); R_joff = fuel-on / luajit-joff (secondary comparator): STOP for design review "
				"if not established faster")
		else:
			role = ("CURRENT ACCEPTANCE SCREEN (R_jit target rule upper <= 1.25: not established, including unresolved, "
				"means gate not met -> STOP for review; R_joff: current within-session acceptance gate)")
		entry = {"role": role, "r1_context": {"label": R1_CONTEXT_LABEL, **R1_CONTEXT[kernel]}, "code_note": CODE_NOTES[kernel]}
		if not allowed:
			entry.update({"R_jit": {"suppressed": why}, "R_joff": {"suppressed": why}, "S_off_over_on": {"suppressed": why},
				"break_even": {"suppressed": why}})
			v[kernel] = entry
			continue
		jit = beside(cell, "R_jit", jit_category)
		joff = beside(cell, "R_joff", joff_category)
		speed = beside(cell, "S_off_over_on", lambda ci: "descriptive")
		speed["label"] = f"descriptive: fuel-off / fuel-on on {kernel} (no threshold)"
		jit["verdict"] = jit_target_verdict(jit)
		joff["verdict"] = joff_verdict(joff)
		joff_ok = joff["category"] == "faster"
		jit_ok = jit["category"] in ("met", "met_equal_edge")
		if kernel == PRIMARY:
			if not joff_ok:
				stop.append(f"{kernel}: R_joff not established faster (upper >= 1.0) -> STOP for design review of the inline/Replay/entry path")
		else:
			joff["verdict"] += "; current acceptance gate " + ("met" if joff_ok else "not met")
			jit["verdict"] += "; current acceptance gate " + ("met" if jit_ok else "not met")
			if not joff_ok:
				stop.append(f"{kernel}: current acceptance gate not met (R_joff upper >= 1.0) -> STOP for review")
			if not jit_ok:
				stop.append(f"{kernel}: current acceptance gate not met (R_jit target not established: "
					f"{jit['verdict'].split(':')[0]}) -> STOP for review")
		entry.update({"R_jit": jit, "R_joff": joff, "S_off_over_on": speed, "break_even": break_even(cell)})
		v[kernel] = entry

	def text_of(kernel, key):
		x = v[kernel][key]
		return x.get("verdict", x.get("suppressed"))

	v["primary"] = {"label": ("calls R_jit is the SOLE PRIMARY, judged on its own interval; while and numeric are current "
		"acceptance screens reported separately; no aggregate or joint verdict is formed; sensitivity results are beside, "
		"never instead"), "calls": text_of("calls", "R_jit")}
	v["screens"] = {"label": "while and numeric, each on its own interval (R_jit target gate and R_joff gate); no aggregate",
		**{k: {"R_jit": text_of(k, "R_jit"), "R_joff": text_of(k, "R_joff")} for k in SCREENS}}

	cell = "calls/tiny"
	label = ("fixed-cost-dominated diagnostic (entry, guard, iterator read/commit; harness overhead included); no threshold; "
		"unresolved when a denominator is not strictly positive")
	if allowed:
		v[cell] = {"label": label, **{rid: beside(cell, rid, lambda ci: "descriptive") for rid, _, _ in cell_ratios(cell)}}
	else:
		v[cell] = {"label": label, "suppressed": why}

	for kernel, stream in (("fib", "fib_main"), ("shared_rows", "shared_rows_main")):
		cell = f"{kernel}/{stream}"
		if not allowed:
			ctl = {"suppressed": why}
		else:
			ctl = beside(cell, "on_over_off", control_category)
			ctl["verdict"] = control_verdict(ctl)
			if ctl["category"] not in ("met", "met_equal_edge"):
				stop.append(f"{kernel}: control margin not met ({ctl['category']}) -> STOP: revisit hook selection (J0 rule 5)")
		ctl["role"] = "control: fuel-on / fuel-off, margin upper <= 1.01 (else STOP)"
		ctl["r1_context"] = {"label": R1_CONTEXT_LABEL, **R1_CONTEXT[kernel]}
		if kernel == "fib":
			ctl["b1_fib_stop_history"] = HISTORY[0]
		v[f"control/{kernel}"] = ctl

	if out["invalid_blocks"]:
		stop.insert(0, f"{len(out['invalid_blocks'])} invalid block(s): reported, not dropped; ALL verdicts suppressed")
	if out["invalid_native_exit"]:
		stop.insert(0, "INVALID NATIVE EXIT observed: the probe's validity FAILS (globally invalid, no passing verdict)")
	if status != "COMPLETE":
		stop.insert(0, f"SESSION {status}: NO acceptance verdicts ({'; '.join((invalid + incomplete)[:5])})")
	elif not allowed:
		stop.insert(0, "a scheduled (cell, round, subject) has no valid slope: NO acceptance verdicts")
	out["stop_or_review"] = stop
	out["observed_categories"] = ({k: {"R_jit": v[k]["R_jit"]["category"], "R_joff": v[k]["R_joff"]["category"]}
		for k in ("calls", "while", "numeric")} | {f"control/{k}": v[f"control/{k}"]["category"] for k in ("fib", "shared_rows")}
		if allowed else {"suppressed": why})
	out["history_verbatim"] = HISTORY
	out["disclosures"] = {
		"design": ("current acceptance screen of the FUEL binaries (346623b6) against LuaJIT in this session; four subjects; "
			"bare luajit is the primary comparator and luajit -joff the secondary"),
		"no_cross_session": NO_CROSS_SESSION, "no_gate_change": NO_GATE_CHANGE, "multiplicity": MULTIPLICITY,
		"tradeoffs": TRADEOFFS,
		"qualification": "any qualification attaches to these exact pinned binaries (fuel-on, fuel-off sha256 in PINS.json)",
		"no_aggregate": "each kernel is reported separately; no aggregate verdict is formed"}
	out["scope"] = (f"Concludes only about calls (the SOLE PRIMARY, R_jit versus bare LuaJIT on its own interval), the while "
		f"and numeric current acceptance screens (R_jit target gate and R_joff gate, each on its own interval), the calls "
		f"R_joff gate, all as a CURRENT ACCEPTANCE SCREEN of the FUEL binaries, and the feature-on cost on fib/shared_rows "
		f"(fuel-on versus fuel-off); every statement holds {SCOPE} only. R1 is not a paired comparator and its figures are "
		f"descriptive context only; R3 is quoted history only. Nothing about fib or shared_rows versus LuaJIT. LuaJIT performs no overflow or fuel "
		f"checks; Rune performs both (for calls: one guard covering the header and callee charges, their folded "
		f"decrement, and the Add's overflow branch per iteration). LuaJIT uses host CPU features; the Cranelift target is baseline x86-64. Harness overhead "
		f"(process start, input reading, stdout and the MAPS line) is included in every wall time, including the tiny "
		f"diagnostic, and differs between subjects; it is not claimed to be identical process work. The Step 0 mapping "
		f"counts are INDIRECT evidence that a region is loaded; they are not a production-entry counter. The calls region "
		f"enters its slow copy only with fuel 0 or 1 at the guard and Replays only at a callee fuel exhaustion or fault, "
		f"which this probe's fuel and inputs never reach: slow-copy and Replay cost are not measured.")
	texts = strings({k: val for k, val in out.items() if k != "history_verbatim"})
	out["wording_violations"] = [list(x) for x in wording_violations(texts)]
	if out["wording_violations"]:
		out["acceptance_verdicts"] = False
		out["errors"]["invalid"].append("wording guard fired: verdicts withdrawn")
		return out, RC["INVALID"]
	return out, RC[status]


def main(raw_path, manifest_path):
	out, rc = analyze(raw_path, manifest_path)
	json.dump(out, sys.stdout, indent=1)
	print()
	return rc


if __name__ == "__main__":
	if len(sys.argv) != 3:
		print(__doc__)
		sys.exit(2)
	sys.exit(main(sys.argv[1], sys.argv[2]))
