"""rnx 0179 official run: the one frozen P0 (base, candidate) pair, a complete measure.py run into OUT_DIR/p0-cand
(plan rnx a2bea93 section 4). A scientific decision (WIN, NO-WIN or STOP) is a completed result; any infrastructure,
safety or semantic failure (an exception) is recorded as STOPPED with the partial cell retained and no decision.

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 official.py OUT_DIR
"""
import json, pathlib, sys, time
import measure
from common import PAIRS


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	(profile, source), = PAIRS
	ledger = {"pair": [profile, source], "started": time.time()}
	try:
		(out / "official.json").write_text(json.dumps(ledger, indent=1) + "\n")
		measure.main(out / f"{profile}-{source}", profile, source)
		d = json.loads((out / f"{profile}-{source}" / "measure.json").read_text())["decision"]
		ledger.update(decision=d["decision"], regressions=d["regressions"], disagreements=d["disagreements"], status="complete")
		print("PAIR", profile, source, d["decision"], flush=True)
	except BaseException as error:
		ledger["status"] = "STOPPED (infrastructure/semantic failure)"
		ledger["failure"] = repr(error)
		raise
	finally:
		ledger["ended"] = time.time()
		(out / "official.json").write_text(json.dumps(ledger, indent=1) + "\n")


if __name__ == "__main__":
	main(sys.argv[1])
