"""rnx 0172 base-only A/A diagnostic of the FIFO reproduction windows (agreed with Codex after run3's STOP).

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 diag_aa.py OUT_DIR

No candidate binary is used anywhere. Two conditions, both the byte-identical base counter build (0ae53261...):
	mine: this probe's base/target/release/counter, launched as measure.py launches it.
	0169: 0169's own counter at its original path (from 0169 counters.json "command"). The 0169 environment and cwd
		were not recorded (subjects.json "environment" is {}), so they are NOT reconstructed; this run inherits this
		controller's environment, and the cwd is listed.
Pre-registered: 3 blocks; in each block, for each condition (order AB, BA, AB) and mode (floor, empty-context,
context), 30 fresh processes. Original FIFO method, target affinity {4} verified, observer on core 0. Every raw
record, running percentage, output and individual count is saved, with block summaries.
"""
import hashlib, json, os, pathlib, select, signal, statistics, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
BIN = {"mine": HERE / "base/target/release/counter",
	"0169": pathlib.Path("/home/me/work/.worktrees/rnx-bench-0169/probes/rune-runtime/new/target/release/counter")}
WANT = "0ae53261dc10ad05826d"
MODES = ["floor", "empty-context", "context"]


def run_one(exe, mode, tmp):
	ctl, ack, raw = tmp / "c.ctl", tmp / "c.ack", tmp / "c.jsonl"
	for p in (ctl, ack, raw):
		if p.exists():
			p.unlink()
	os.mkfifo(ctl)
	os.mkfifo(ack)
	cf, af = os.open(ctl, os.O_RDWR | os.O_NONBLOCK), os.open(ack, os.O_RDWR | os.O_NONBLOCK)
	child = perf = None
	try:
		child = subprocess.Popen([str(exe), mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
		assert select.select([child.stderr], [], [], 10)[0] and child.stderr.readline() == "READY\n"
		affinity = sorted(os.sched_getaffinity(child.pid))
		assert affinity == [4], affinity
		perf = subprocess.Popen(["taskset", "-c", "0", "perf", "stat", "-j", "--cputype", "core", "-e", "instructions:u,cycles:u", "-p", str(child.pid),
			"-D", "-1", "--control", f"fifo:{ctl},{ack}", "-o", str(raw)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

		def control(m):
			os.write(cf, (m + "\n").encode())
			assert select.select([af], [], [], 10)[0], m
			assert os.read(af, 1024).rstrip(b"\0") == b"ack\n"
		control("enable")
		child.stdin.write("go\n")
		child.stdin.flush()
		deadline = time.monotonic() + 60
		while True:
			assert time.monotonic() < deadline
			line = child.stderr.readline()
			assert line
			if line == "DONE\n":
				break
		control("disable")
		child.stdin.write("stop\n")
		child.stdin.flush()
		out, err = child.communicate(timeout=10)
		assert child.returncode == 0 and out == "" and err == "", (child.returncode, out[:80], err[:80])
		perf.send_signal(signal.SIGINT)
		perf.communicate(timeout=10)
		text = raw.read_text()
		rows = [json.loads(l) for l in text.splitlines() if l.startswith("{")]
		counts = {}
		for row in rows:
			for n in ("instructions", "cycles"):
				if row.get("event") in (n + ":u", f"cpu_core/{n}/u"):
					counts[n] = {"value": float(row["counter-value"]), "pcnt_running": float(row["pcnt-running"])}
		assert set(counts) == {"instructions", "cycles"} and all(c["pcnt_running"] >= 99 and c["value"] > 0 for c in counts.values()), text[-300:]
		return {"affinity": affinity, "raw": text, "counts": counts}
	finally:
		for p in (child, perf):
			if p is not None and p.poll() is None:
				p.kill()
				p.wait()
		os.close(cf)
		os.close(af)
		ctl.unlink()
		ack.unlink()


def summary(v):
	q = statistics.quantiles(v, n=10)
	return {"n": len(v), "median": statistics.median(v), "p10": q[0], "p90": q[-1], "min": min(v), "max": max(v)}


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	tmp = out / "tmp"
	tmp.mkdir()
	os.sched_setaffinity(0, {4})
	for name, exe in BIN.items():
		assert hashlib.sha256(exe.read_bytes()).hexdigest().startswith(WANT), (name, "not the byte-identical base counter")
	meta = {"binaries": {k: str(v) for k, v in BIN.items()}, "cwd": os.getcwd(), "controller_affinity": sorted(os.sched_getaffinity(0)),
		"environment_inherited": dict(os.environ), "load_before": open("/proc/loadavg").read().split()[0], "started": time.time(),
		"limitation": "0169's launch environment and cwd were not recorded; condition '0169' reproduces only its binary path/argv."}
	samples = []
	for block in range(3):
		order = ("mine", "0169") if block % 2 == 0 else ("0169", "mine")
		for cond in order:
			for mode in MODES:
				for i in range(30):
					r = run_one(BIN[cond], mode, tmp)
					samples.append({"block": block, "condition": cond, "mode": mode, "index": i, **r})
		print("block", block, "done", flush=True)
	summ = {}
	for cond in BIN:
		for mode in MODES:
			for block in range(3):
				v = [s["counts"]["instructions"]["value"] for s in samples if s["condition"] == cond and s["mode"] == mode and s["block"] == block]
				summ[f"{cond}-{mode}-block{block}"] = summary(v)
			v = [s["counts"]["instructions"]["value"] for s in samples if s["condition"] == cond and s["mode"] == mode]
			summ[f"{cond}-{mode}-all"] = summary(v)
	meta.update(ended=time.time(), load_after=open("/proc/loadavg").read().split()[0])
	(out / "diag_aa.json").write_text(json.dumps({"meta": meta, "summary": summ, "samples": samples}, indent=1) + "\n")
	for k, s in summ.items():
		if k.endswith("-all"):
			print(f"{k:28} median {s['median']:14.1f} p10 {s['p10']:14.1f} p90 {s['p90']:14.1f} min {s['min']:14.1f} max {s['max']:14.1f}")



# HISTORICAL PRODUCER (rnx 0172). It records the raw inherited environment; the retained output was redacted after
# capture (results/borrow-context-type-0172/REDACTION.md). Do not rerun as is: a new run must redact at capture and include a fake-secret sentinel control.
if __name__ == "__main__" and not __import__("os").environ.get("RNX_ALLOW_HISTORICAL_RERUN"):
	raise SystemExit("historical producer; see the comment above")

if __name__ == "__main__":
	main(sys.argv[1])
