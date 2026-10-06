"""rnx 0178: replay 0177's reviewed caller-edge parser (edges.py, copied verbatim from bench dadf1477) over the retained
0178 diagnostic, for all six (profile, source) subjects. Read-only: executes no subject.

	python3 edges0178.py DIAGNOSTIC_DIR > edges.json

Only the report loop is generalized: subjects come from the 0178 matrix, and the executed fast path is recognised by
either candidate's helper name (S75 try_range_next, S76 try_range_dispatch). parse() and controls() are 0177's own, and
the parser fixtures must pass before any real file is opened. No display threshold: every caller edge of each target
is kept. Profile ids are local compressed identities, not unique nm addresses; edge Ir is inclusive and must not be
summed with exclusive Ir or across recursive paths.
"""
import hashlib, json, lzma, sys
from pathlib import Path
import edges
from common import PROFILES, SOURCES

SUBJECTS = [f"{p}-{s}" for p in PROFILES for s in SOURCES]
WORKLOADS = ("context", "run-fib", "run-calls", "run-numeric")
TARGETS = ["drop_glue::<rune::runtime::value::Repr>", "drop_glue::<rune::runtime::value::Value>", "::pop_call_frame", "infallible_cmp"]
FAST = ("::try_range_dispatch", "::try_range_next")


def report(root):
	diagnostic = json.loads((root / "diagnostic.json").read_text())
	reports = {}
	for subject in SUBJECTS:
		for workload in WORKLOADS:
			path = root / f"callgrind.out.{subject}.{workload}.xz"
			if not path.exists():
				path = root / f"callgrind.out.{subject}.{workload}"
				raw = path.read_bytes()
				compressed = None
			else:
				compressed = path.read_bytes()
				raw = lzma.decompress(compressed)
			total, nodes, graph = edges.parse(raw.decode())
			if total != diagnostic["runs"][f"{subject}/{workload}"]["ir_total"]:
				raise SystemExit(("STOP: Ir total differs from the diagnostic record", subject, workload))
			fast = {ident for ident, node in nodes.items() if any(name in node["name"] for name in FAST)}
			reachable = set(fast)
			while True:
				grown = reachable | {b for (a, b), (calls, _) in graph.items() if a in reachable and calls > 0}
				if grown == reachable:
					break
				reachable = grown
			selected = []
			for ident, node in nodes.items():
				if not any(target in node["name"] for target in TARGETS):
					continue
				callers = [{"profile_id": caller, "name": nodes[caller]["name"], "calls": calls, "inclusive_edge_ir": ir,
					"reachable_from_executed_fast_path": caller in reachable}
					for (caller, target), (calls, ir) in graph.items() if target == ident]
				selected.append({"profile_id": ident, **node,
					"nm_identity": "ambiguous" if node["name"].startswith("core::ptr::drop_glue") else "check retained nm",
					"callers": sorted(callers, key=lambda x: -x["inclusive_edge_ir"])})
			reports[f"{subject}/{workload}"] = {
				"compressed_sha256": hashlib.sha256(compressed).hexdigest() if compressed else None,
				"raw_sha256": hashlib.sha256(raw).hexdigest(), "ir_total": total,
				"exclusive_sum": sum(x["exclusive_ir"] for x in nodes.values()),
				"executed_fast_path_ids": sorted(fast),
				"fast_path_direct_callees": [{"profile_id": t, "name": nodes[t]["name"], "calls": c, "inclusive_edge_ir": ir}
					for (a, t), (c, ir) in graph.items() if a in fast],
				"targets": selected}
	return {"controls": edges.controls(), "profiles": reports,
		"limits": ["Profile ids are local compressed function identities, not unique nm addresses.",
			"Reachability covers executed edges in this profile only; absent edges are not absent static callers.",
			"Edge Ir is inclusive; do not sum it with exclusive Ir or recursive edges.",
			"No subject executions, new disassembly, compilation or measurements."]}


if __name__ == "__main__":
	edges.controls()  # must pass before opening any real profile
	print(json.dumps(report(Path(sys.argv[1])), indent=1, default=sorted))
