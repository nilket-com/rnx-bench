"""rnx 0174 fork suites: `cargo test -p rune --all-targets --all-features` once per source (base, S71, S72).

	flock --exclusive --timeout 3600 /tmp/rnx-runtime-bench.lock python3 suites.py OUT_DIR

Test profile only; it includes 0172's registration-inventory golden. Release-profile inventory stays unverified.
"""
import json, pathlib, re, subprocess, sys, time
from build import checkout
from common import FORK, SOURCES, EB, Ledger


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	ledger = Ledger(out / "commands.jsonl")
	rows = {}
	for src, rev in SOURCES.items():
		checkout(rev)
		argv = ["cargo", "test", "-p", "rune", "--all-targets", "--all-features"]
		began = time.monotonic()
		r = subprocess.run(argv, capture_output=True, text=True, timeout=3600, cwd=FORK, env=EB)
		elapsed = time.monotonic() - began
		log = r.stdout + r.stderr
		(out / f"suite-{src}.log").write_text(log)
		passed = sum(int(m) for m in re.findall(r"test result: ok\. (\d+) passed", log))
		failed = sum(int(m) for m in re.findall(r"(\d+) failed", log))
		ledger.write(kind="suite", source=src, rev=rev, argv=argv, env=EB, status=r.returncode, seconds=elapsed)
		rows[src] = {"rev": rev, "status": r.returncode, "passed": passed, "failed": failed, "seconds": elapsed}
		print(src, rows[src], flush=True)
	checkout(SOURCES["base"])
	(out / "suites.json").write_text(json.dumps(rows, indent=1) + "\n")
	assert all(v["status"] == 0 and v["failed"] == 0 for v in rows.values()), "STOP: suite failure"


if __name__ == "__main__":
	main(sys.argv[1])
