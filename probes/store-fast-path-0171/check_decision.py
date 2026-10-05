"""Independent recomputation of 0171's frozen decision from the retained arrays (written separately from measure.py).

	python3 check_decision.py MEASURE_JSON
"""
import json, sys


def median(xs):
	s = sorted(xs)
	n = len(s)
	return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def p10_p90(xs):
	# Linear interpolation on the sorted sample (numpy's default method), stated so it can be compared.
	s = sorted(xs)

	def q(p):
		k = (len(s) - 1) * p
		f = int(k)
		c = min(f + 1, len(s) - 1)
		return s[f] + (s[c] - s[f]) * (k - f)
	return q(0.1), q(0.9)


def main(path):
	d = json.load(open(path))
	works = sorted({k.split("-", 1)[1] for k in d["pmu"]})
	regress, disagree, wins = [], [], []
	for w in works:
		bi, ci = median(d["pmu"][f"base-{w}"]["instructions"]), median(d["pmu"][f"cand-{w}"]["instructions"])
		bw, cw = median(d["wall_ms"][f"base-{w}"]), median(d["wall_ms"][f"cand-{w}"])
		assert len(d["pmu"][f"base-{w}"]["instructions"]) == 5 and len(d["wall_ms"][f"base-{w}"]) == 30, w
		lo, hi = p10_p90(d["wall_ms"][f"base-{w}"])
		di, dw = ci / bi - 1, cw / bw - 1
		if di > 0.005:
			regress.append((w, "instr", round(di * 100, 2)))
		if cw - bw > hi - lo:
			regress.append((w, "wall", round(dw * 100, 2)))
		if not (abs(di) <= 0.005 or abs(cw - bw) <= hi - lo) and di * dw < 0 and abs(di) > 0.03 and abs(dw) > 0.03:
			disagree.append(w)
		if w in ("while", "fib", "calls") and di <= -0.03:
			wins.append(w)
	decision = "STOP" if regress or disagree else ("WIN" if len(wins) >= 2 else "NO-WIN")
	print(path.split("/")[-2], decision, "regressions", regress, "disagreements", disagree, "gate wins", sorted(wins))
	assert decision == d["decision"]["decision"], (decision, d["decision"]["decision"])


if __name__ == "__main__":
	main(sys.argv[1])
