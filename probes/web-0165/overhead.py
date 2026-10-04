"""The predeclared dispatch gate; no cross-host or Flask performance claim."""
import json
import pathlib
import sys

folder = pathlib.Path(sys.argv[1])
rows = json.loads((folder / "summary.json").read_text())
conditions = sorted({(x["route"], x["c"], x["ka"]) for x in rows})
assert len(conditions) == 5 and len(rows) == 10
out = []
for route, concurrency, keepalive in conditions:
    pair = {
        x["impl"]: x for x in rows
        if (x["route"], x["c"], x["ka"]) == (route, concurrency, keepalive)
    }
    assert set(pair) == {"A", "B"}
    before, after = pair["A"], pair["B"]
    ratio = after["rps"] / before["rps"]
    out.append({
        "route": route, "concurrency": concurrency, "keepalive": keepalive,
        "main_rps": before["rps"], "routes_rps": after["rps"],
        "routes_over_main": ratio, "percent": 100 * (ratio - 1),
        "passed": ratio >= 0.95,
    })
result = {"passed": all(x["passed"] for x in out), "conditions": out}
print(json.dumps(result, indent=2))
if not result["passed"]:
    raise SystemExit(1)
