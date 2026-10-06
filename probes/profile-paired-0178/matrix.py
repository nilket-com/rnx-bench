"""rnx 0178 official matrix: the four (profile, candidate) pairs in the frozen order P0:S75, P1:S75, P1:S76, P0:S76
(plan rnx 31ca480 section 4), each a complete measure.py pair run into OUT_DIR/<profile>-<source>. A scientific
STOP decision is a result and the next pair still runs; any infrastructure, safety or semantic failure (an exception)
stops the whole matrix with every earlier cell and the partial cell retained.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 matrix.py OUT_DIR
"""
import json, pathlib, sys, time
import measure
from common import PAIRS


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	ledger = {"pairs": [], "started": time.time()}
	try:
		for profile, source in PAIRS:
			row = {"profile": profile, "source": source, "started": time.time()}
			ledger["pairs"].append(row)
			(out / "matrix.json").write_text(json.dumps(ledger, indent=1) + "\n")
			measure.main(out / f"{profile}-{source}", profile, source)
			d = json.loads((out / f"{profile}-{source}" / "measure.json").read_text())["decision"]
			row.update(ended=time.time(), decision=d["decision"], regressions=d["regressions"], disagreements=d["disagreements"])
			(out / "matrix.json").write_text(json.dumps(ledger, indent=1) + "\n")
			print("PAIR", profile, source, d["decision"], flush=True)
		ledger["status"] = "complete"
	except BaseException as error:
		ledger["status"] = "STOPPED (infrastructure/semantic failure)"
		ledger["failure"] = repr(error)
		raise
	finally:
		ledger["ended"] = time.time()
		(out / "matrix.json").write_text(json.dumps(ledger, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
