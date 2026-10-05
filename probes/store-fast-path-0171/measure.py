"""rnx 0171: store fast-path experiment, base (fork main bb8e6937) vs candidate (branch commit), pre-registered.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 measure.py OUT_DIR

Order (plan section 4 and amendment A4): correctness gates; base reproduction of the retained 0168/0170 counts;
5 interleaved whole-process PMU repetitions; ABBA native wall clock (3 rounds x 10); the decision, computed by the
frozen rules below. Nothing is retried or dropped after seeing a result.
"""
import json, math, os, pathlib, re, statistics, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from oracle import EXPECTED

BIN = {"base": HERE / "base/target/release/primary", "cand": HERE / "cand/target/release/primary"}
CLOCK = HERE / "clock"
FIX = HERE / "fixtures"
CORPUS = pathlib.Path("/home/me/work/rnx-bench/probes/rune-base-0168/fixtures")
WORKS = ["empty", "answer", "numeric", "while", "fib", "calls", "compare", "vector", "strings",
	"overwrite_inline", "overwrite_mixed", "overwrite_deep", "overwrite_alias"]
GATE = ("while", "fib", "calls")
# Retained whole-process run-mode instructions:u medians of the unmodified main primary (0170 step D).
BASE_REF = {"numeric": 1757.10e6, "fib": 831.06e6}

_t = [f"item:{i}" for i in range(1, 20001)]
_s = "|".join(_t)
EXPECT = {"empty": "", "answer": "42\n", "numeric": "3\n", "fib": "196418\n",
	"strings": f"{len(_s)}\n{_s[0:19]}\n{_s[len(_s) - 21:]}\n"}
EXPECT.update({k: f"{v}\n" for k, v in EXPECTED.items()})

NORMALIZE = [(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"), (re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)")]


def norm(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


def run(v, mode, path, *extra):
	r = subprocess.run([str(BIN[v]), mode, str(path), *extra], capture_output=True, text=True, timeout=300)
	return (r.returncode, r.stdout, r.stderr)


def perf(v, work):
	r = subprocess.run(["taskset", "-c", "4", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "--",
		str(BIN[v]), "run", str(FIX / f"{work}.rn")], capture_output=True, text=True, timeout=300)
	assert r.returncode == 0 and r.stdout == EXPECT[work], (v, work, r.stdout[:80], r.stderr[-300:])
	out = {}
	for line in r.stderr.splitlines():
		if line.startswith("{"):
			row = json.loads(line)
			name = next((n for n in ("instructions", "cycles") if row.get("event") in (n + ":u", f"cpu_core/{n}/u")), None)
			if name:
				assert float(row["pcnt-running"]) >= 99, row
				val = float(row["counter-value"])
				assert math.isfinite(val) and val > 0, row
				out[name] = val
	assert set(out) == {"instructions", "cycles"}, r.stderr[-300:]
	return out


def wall(v, work):
	r = subprocess.run(["taskset", "-c", "4", str(CLOCK), "1", "3", str(BIN[v]), "run", str(FIX / f"{work}.rn")],
		capture_output=True, text=True, timeout=300)
	assert r.returncode == 0, r.stderr[-300:]
	lines = r.stdout.split("\n", 2)
	ns = int(lines[0])
	assert int(lines[1]) == 0, (v, work, "status", lines[1])
	assert ns > 0
	return ns / 1e6


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	ledger = {"started": time.time(), "load_before": open("/proc/loadavg").read().split()[0]}
	res = {"binaries": {v: subprocess.run(["sha256sum", str(p)], capture_output=True, text=True).stdout.split()[0] for v, p in BIN.items()}}
	# 1. Correctness: the 0168 corpus and every fixture, base vs candidate, strict after the two known normalizations.
	corr = {}
	for fx in sorted(CORPUS.glob("*.rn")) + sorted(FIX.glob("*.rn")):
		mode = "async" if fx.stem == "async" else "run"
		extra = ["2000000"] if fx.stem == "budget" else []
		a, b = run("base", mode, fx, *extra), run("cand", mode, fx, *extra)
		same = norm(a) == norm(b)
		corr[f"{fx.parent.name}/{fx.stem}"] = {"same": same, "raw_identical": a == b, "base": list(a), "cand": list(b)}
		assert same, (fx, a[:2], b[:2], a[2][:200], b[2][:200])
		if fx.parent == FIX:
			assert a == (0, EXPECT[fx.stem], ""), (fx.stem, a)
	res["correctness"] = corr
	print("correctness: all", len(corr), "identical (after the two known normalizations); fixtures match oracles", flush=True)
	# 2. Base reproduction of retained counts (2%).
	repro = {}
	for w, ref in BASE_REF.items():
		vals = [perf("base", w)["instructions"] for _ in range(3)]
		repro[w] = {"median": statistics.median(vals), "ref": ref, "ratio": statistics.median(vals) / ref}
	res["base_reproduction"] = repro
	assert all(abs(r["ratio"] - 1) <= 0.02 for r in repro.values()), repro
	print("base reproduction:", {w: round(r["ratio"], 4) for w, r in repro.items()}, flush=True)
	# 3. PMU: 5 repetitions, interleaved, ABBA order per repetition.
	pmu = {f"{v}-{w}": {"instructions": [], "cycles": []} for v in BIN for w in WORKS}
	for rep in range(5):
		order = ("base", "cand") if rep % 2 == 0 else ("cand", "base")
		for w in WORKS:
			for v in order:
				c = perf(v, w)
				pmu[f"{v}-{w}"]["instructions"].append(c["instructions"])
				pmu[f"{v}-{w}"]["cycles"].append(c["cycles"])
	res["pmu"] = pmu
	print("pmu done", flush=True)
	# 4. Wall: 3 rounds x 10 samples, ABBA per round, native clock.
	walls = {f"{v}-{w}": [] for v in BIN for w in WORKS}
	for rnd in range(3):
		for w in WORKS:
			order = ("base", "cand", "cand", "base") if rnd % 2 == 0 else ("cand", "base", "base", "cand")
			for v in order:
				for _ in range(5):
					walls[f"{v}-{w}"].append(wall(v, w))
	res["wall_ms"] = walls
	print("wall done", flush=True)
	# 5. The frozen decision.
	rows, regress, disagree, gate_wins = {}, [], [], []
	for w in WORKS:
		bi, ci = statistics.median(pmu[f"base-{w}"]["instructions"]), statistics.median(pmu[f"cand-{w}"]["instructions"])
		bw, cw = statistics.median(walls[f"base-{w}"]), statistics.median(walls[f"cand-{w}"])
		q = statistics.quantiles(walls[f"base-{w}"], n=10)
		band = q[-1] - q[0]  # base p10..p90
		di, dw = ci / bi - 1, cw / bw - 1
		rows[w] = {"base_instr": bi, "cand_instr": ci, "instr_change": di, "base_wall_ms": bw, "cand_wall_ms": cw, "wall_change": dw,
			"base_wall_p10_p90_ms": band}
		if di > 0.005:
			regress.append((w, "instructions", di))
		if cw - bw > band:
			regress.append((w, "wall", dw))
		inside = abs(di) <= 0.005 or abs(cw - bw) <= band
		if not inside and di * dw < 0 and abs(di) > 0.03 and abs(dw) > 0.03:
			disagree.append((w, di, dw))
		if w in GATE and di <= -0.03:
			gate_wins.append(w)
	if regress or disagree:
		decision = "STOP"
	elif len(gate_wins) >= 2:
		decision = "WIN"
	else:
		decision = "NO-WIN"
	res["decision"] = {"decision": decision, "rows": rows, "regressions": regress, "disagreements": disagree, "gate_wins": gate_wins}
	ledger.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	res["ledger"] = ledger
	(out / "measure.json").write_text(json.dumps(res, indent=1) + "\n")
	print(json.dumps(res["decision"], indent=1))


if __name__ == "__main__":
	main(sys.argv[1])
