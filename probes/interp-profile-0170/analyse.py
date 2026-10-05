"""rnx 0170 step B analysis (R2/R3 revision): target-process self samples by symbol family, fail-closed.

	python3 analyse.py STEP_A_S2_DIR STEP_B_DIR STEP_B_TARGET.json OUT.json OUT.md
	python3 analyse.py --controls STEP_A_S2_DIR STEP_B_DIR STEP_B_TARGET.json

Inputs: step A's S2 whole-process counts (the per-invocation scale), step B's plan (invocations per repeat) and the
re-extracted target-process samples (reextract.py; wrapper processes excluded, target build-id bound).
Validation refuses: a missing or extra profile in the 2 engines x 9 workloads x 2 events matrix; anything other than
exactly 3 distinct repeats; non-positive or non-finite counts; LOST or THROTTLE above 0; fewer than 10,000 target
samples per profile. Families are disjoint and ordered (first match wins). Families named "mixed" mean the symbol
family is not exclusive to one operation. Shares carry a model-based (Wilson, independent-sample) descriptive
interval, not a calibrated uncertainty for net cost. Moving work between `Vm::run` and out-of-line helpers can be an
inlining change, not added work; only the net totals (step D) are robust.
"""
import copy, json, math, pathlib, re, sys

ENGINES = ("old", "new")
WORKS = ("empty", "answer", "numeric", "while", "fib", "calls", "compare", "vector", "strings")
EVENTS = ("instructions", "cycles")
MIN_SAMPLES = 10000

RULES = [  # (family, dso regex, symbol regex)
	("loader/kernel/unknown", r"kernel|ld-linux|\[unknown\]", r""),
	("vm: Vm::run self (dispatch + inlined handlers)", r"", r"^<rune::runtime::vm::Vm>::run$"),
	("vm: comparison helpers", r"", r"^<rune::runtime::vm::Vm>::internal_cmp|value::inline::Inline>::partial_cmp|^<<rune::runtime::vm::Vm>::op_op::\{closure"),
	("vm: call/return/frame helpers", r"", r"^<rune::runtime::vm::Vm>::(op_call|call_offset_fn|push_call_frame|pop_call_frame|op_return\w*|call_function\w*|call_instance_fn)|ProtocolCaller>::try_call_protocol_fn"),
	("vm: range iterator next (native fn)", r"", r"rune::runtime::range::RangeIter"),
	("vm: value/AnyObj construction and conversion", r"", r"^<rune::runtime::value::Value>::new::|^<rune::runtime::any_obj::AnyObj>::new::|IntoReturn>::into_return|from_value::Unsafe(ToMut|ToRef)|any_obj::drop_value|AnyObjDecShared"),
	("vm: Value clone/drop glue and dismantle", r"", r"drop_glue::<rune::runtime::value::Value>|^<rune::runtime::value::Value as core::clone::Clone>|value::dismantle::Worklist|drop_glue::<rune::runtime::value::dismantle"),
	("vm: rune Stack methods", r"", r"^<rune::runtime::(memory|stack)::Stack[^>]*>::|rune::runtime::(memory|stack)::Memory>::"),
	("mixed: Vec<Value> resize/truncate/collect", r"", r"rune_alloc::vec::Vec<rune::runtime::value::Value>"),
	("vm: integer conversion/arith helpers", r"", r"^<i64>::checked_|value::inline::Inline>::as_integer"),
	("vm: other rune::runtime symbols", r"", r"rune::runtime::"),
	("allocator (glibc + rust shims + rune_alloc)", r"", r"^(malloc|_int_malloc|cfree|free|_int_free\w*|unlink_chunk\S*|realloc|_int_realloc|tcache\S*|malloc_consolidate)(@|$)|__rustc::__rd?l_|__rust_(dealloc|alloc|realloc|no_alloc\w*)|rune_alloc::alloc::|rune_alloc::limit::|raw_vec::finish_grow|Global>::take"),
	("formatting and strings (mixed)", r"", r"core::fmt::|fmt::Write>::write_str|TryWrite|rune_alloc::string::String|__mem(move|cpy|set|cmp)\S*|core::str::"),
	("compile::context install/insert (registration)", r"", r"^<rune::compile::context::Context>::|compile::context::ContextType"),
	("mixed: native module fns (__rune_fn__)", r"", r"__rune_fn__"),
	("mixed: item paths/hashing/maps (mostly registration)", r"", r"rune_core::item|xxhash|ahash|hashbrown|btree|rune_core::hash|names::Node|const_value|FunctionHandler|function_meta|rune::module::"),
	("compiler", r"", r"rune::(compile|parse|ast|indexing|query|hir|grammar|macros)::|syntree"),
	("libc other", r"libc", r""),
	("other (unmapped)", r"", r""),
]
FAMILIES = [r[0] for r in RULES]


class Refused(Exception):
	pass


def family(dso, sym):
	for name, dre, sre in RULES:
		if (not dre or re.search(dre, dso)) and (not sre or re.search(sre, sym)):
			return name
	return "other (unmapped)"


def wilson(k, n, z=1.96):
	p = k / n
	d = 1 + z * z / n
	c = (p + z * z / (2 * n)) / d
	h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
	return (c - h, c + h)


def finite_positive(x, what):
	if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or x <= 0:
		raise Refused(f"{what} = {x!r}")


def validate(counts, plan, target):
	want = {f"{b}-{w}-{e}" for b in ENGINES for w in WORKS for e in EVENTS}
	got = {}
	for label, rep in target.items():
		m = re.fullmatch(r"(old|new)-(\w+)-(instructions|cycles)-(\d+)", label)
		if not m:
			raise Refused(f"unexpected profile label {label}")
		key = "-".join(m.group(1, 2, 3))
		got.setdefault(key, []).append(int(m.group(4)))
		finite_positive(rep["target_samples"], f"{label} target_samples")
		if rep["lost"] != 0 or rep["throttle"] != 0:
			raise Refused(f"{label}: lost {rep['lost']}, throttle {rep['throttle']}")
		if sum(r["samples"] for r in rep["rows"]) != rep["target_samples"] or not rep["rows"]:
			raise Refused(f"{label}: rows do not sum to the target total")
		for r in rep["rows"]:
			finite_positive(r["samples"], f"{label} row {r['symbol'][:40]}")
	if set(got) != want:
		raise Refused(f"profile matrix mismatch: missing {sorted(want - set(got))[:4]} extra {sorted(set(got) - want)[:4]}")
	for key, reps in got.items():
		if sorted(reps) != [0, 1, 2]:
			raise Refused(f"{key}: repeats {sorted(reps)}")
		total = sum(target[f"{key}-{i}"]["target_samples"] for i in range(3))
		if total < MIN_SAMPLES:
			raise Refused(f"{key}: {total} target samples < {MIN_SAMPLES}")
		if key not in plan:
			raise Refused(f"{key}: no predeclared invocation count")
	for b in ENGINES:
		for w in WORKS:
			for e in EVENTS:
				finite_positive(counts[f"{b}-s2-{w}"][f"{e}_median"], f"{b}-{w} {e} scale")


def analyse(counts, plan, target):
	validate(counts, plan, target)
	result, inventory = {}, {}
	for b in ENGINES:
		for w in WORKS:
			for e in EVENTS:
				key = f"{b}-{w}-{e}"
				per = {f: 0 for f in FAMILIES}
				for i in range(3):
					for r in target[f"{key}-{i}"]["rows"]:
						f = family(r["dso"], r["symbol"])
						per[f] += r["samples"]
						inventory.setdefault(f, {})
						inventory[f][r["symbol"]] = inventory[f].get(r["symbol"], 0) + r["samples"]
				n = sum(per.values())
				scale = counts[f"{b}-s2-{w}"][f"{e}_median"]
				fams = {}
				for f in FAMILIES:
					k = per[f]
					lo, hi = wilson(k, n)
					fams[f] = {"samples": k, "share": k / n, "share_model_interval": [lo, hi]}
					if e == "instructions":
						fams[f]["instructions_est"] = k / n * scale
				result[key] = {"target_samples": n, "per_repeat": [target[f"{key}-{i}"]["target_samples"] for i in range(3)],
					"excluded_wrapper": sum(sum(target[f"{key}-{i}"]["excluded_by_comm"].values()) for i in range(3)), "families": fams}
	inv = {f: sorted(((n, s) for s, n in syms.items()), reverse=True) for f, syms in inventory.items()}
	return result, inv


def load(step_a, step_b, target_json):
	counts = json.loads((pathlib.Path(step_a) / "counts.json").read_text())
	if counts.get("candidate") != "s2" or not counts.get("gate_representative_3pct") or not counts.get("gate_baseline_2pct"):
		raise Refused("step A is not the passed S2 run")
	plan = json.loads((pathlib.Path(step_b) / "plan.json").read_text())["invocations_per_repeat"]
	return counts["counts"], plan, json.loads(pathlib.Path(target_json).read_text())


def report(result, out_md):
	short = {f: f.split(" (")[0] for f in FAMILIES}
	lines = ["# 0170 target-process self samples by symbol family (retired instructions; S2; period 1e6)", "",
		"Model-based descriptive shares; families named 'mixed' are not exclusive to one operation; Vm::run vs helper moves may be inlining.", ""]
	works = ["numeric", "while", "fib", "calls", "compare", "vector", "strings", "answer", "empty"]
	for b in ENGINES:
		lines += [f"## {b}: share of target instruction samples (%)", "", "| family | " + " | ".join(works) + " |", "|---|" + "---|" * len(works)]
		for f in FAMILIES:
			vals = [result[f"{b}-{w}-instructions"]["families"][f]["share"] * 100 for w in works]
			if max(vals) >= 0.5:
				lines.append(f"| {short[f]} | " + " | ".join(f"{v:.1f}" for v in vals) + " |")
		lines.append("| target samples | " + " | ".join(str(result[f"{b}-{w}-instructions"]["target_samples"]) for w in works) + " |")
		lines.append("| wrapper samples excluded | " + " | ".join(str(result[f"{b}-{w}-instructions"]["excluded_wrapper"]) for w in works) + " |")
		lines.append("")
	pathlib.Path(out_md).write_text("\n".join(lines) + "\n")


def controls(step_a, step_b, target_json):
	counts, plan, target = load(step_a, step_b, target_json)
	ok = True

	def expect(name, mutate):
		nonlocal ok
		t = copy.deepcopy(target)
		c = copy.deepcopy(counts)
		mutate(t, c)
		try:
			analyse(c, plan, t)
			refused = False
		except Refused as e:
			refused, name = True, f"{name}: {e}"
		ok &= refused
		print(("pass" if refused else "WRONG") + ": " + name)
	analyse(counts, plan, target)
	print("pass: the real retained inputs are accepted")
	expect("missing profile repeat", lambda t, c: t.pop("new-fib-instructions-2"))
	expect("duplicated repeat label", lambda t, c: t.__setitem__("new-fib-instructions-3", t["new-fib-instructions-0"]))
	expect("insufficient samples", lambda t, c: [t[f"old-empty-cycles-{i}"].update(target_samples=100, rows=[{"samples": 100, "dso": "s2", "space": ".", "symbol": "x"}]) for i in range(3)])
	expect("non-finite count", lambda t, c: t["old-numeric-instructions-1"]["rows"][0].update(samples=float("nan")))
	expect("lost samples", lambda t, c: t["new-while-cycles-0"].update(lost=1))
	expect("throttle", lambda t, c: t["new-while-cycles-0"].update(throttle=2))
	expect("rows not summing to total", lambda t, c: t["old-calls-instructions-0"].update(target_samples=t["old-calls-instructions-0"]["target_samples"] + 1))
	expect("missing scale count", lambda t, c: c["new-s2-vector"].update(instructions_median=float("inf")))
	return ok


def main(argv):
	if argv[0] == "--controls":
		sys.exit(0 if controls(*argv[1:4]) else 1)
	step_a, step_b, target_json, out_json, out_md = argv
	counts, plan, target = load(step_a, step_b, target_json)
	result, inv = analyse(counts, plan, target)
	pathlib.Path(out_json).write_text(json.dumps({"rules": RULES, "profiles": result, "symbol_inventory": inv}, indent=1) + "\n")
	report(result, out_md)


if __name__ == "__main__":
	main(sys.argv[1:])
