"""rnx 0170 R2: re-extract the retained step-B perf data by target process identity (no new sampling).

	python3 reextract.py STEP_B_DIR OUT.json

For every retained profile: decompress, check that the data's build-id for the sampled executable equals the S2
binary's build-id, then take per-symbol self samples for the target process name only (comm `s2`). Every target
sample is kept, including its libc, loader, kernel and unknown frames. Wrapper samples (bash, seq) are counted
separately and excluded. LOST/THROTTLE statistics are re-read from the data.
"""
import json, lzma, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import binary

ROW = re.compile(r"\s*([\d.]+)%\s+(\d+)\s+(\S+)\s+\[(.)\]\s+(.*?)\s*$")


def build_id(path):
	out = subprocess.run(["readelf", "-n", str(path)], capture_output=True, text=True, check=True).stdout
	return re.search(r"Build ID: ([0-9a-f]+)", out).group(1)


def main(step_b, out):
	step_b = pathlib.Path(step_b)
	ids = {b: build_id(binary(b, "s2")) for b in ("old", "new")}
	paths = {b: str(binary(b, "s2")) for b in ("old", "new")}
	result = {}
	with tempfile.TemporaryDirectory() as tmp:
		data = pathlib.Path(tmp) / "p.data"
		for xz in sorted(step_b.glob("*.data.xz")):
			label = xz.name[: -len(".data.xz")]
			base = label.split("-")[0]
			data.write_bytes(lzma.decompress(xz.read_bytes()))
			bl = subprocess.run(["perf", "buildid-list", "-i", str(data)], capture_output=True, text=True, check=True).stdout
			assert f"{ids[base]} {paths[base]}" in bl, (label, "target build-id not bound", bl[:400])
			comms = {}
			for line in subprocess.run(["perf", "report", "-i", str(data), "--stdio", "-n", "-q", "--sort", "comm"],
				capture_output=True, text=True, check=True).stdout.splitlines():
				m = re.match(r"\s*([\d.]+)%\s+(\d+)\s+(\S+)", line)
				if m:
					comms[m.group(3)] = int(m.group(2))
			r = subprocess.run(["perf", "report", "-i", str(data), "--stdio", "--no-children", "-n", "-q", "-g", "none",
				"--comms", "s2", "--sort", "dso,sym", "--percent-limit", "0"], capture_output=True, text=True, check=True)
			rows = []
			for line in r.stdout.splitlines():
				m = ROW.match(line)
				if m:
					rows.append({"samples": int(m.group(2)), "dso": m.group(3), "space": m.group(4), "symbol": m.group(5)})
			stats = subprocess.run(["perf", "report", "-i", str(data), "--stats"], capture_output=True, text=True).stdout
			lost = sum(int(x) for x in re.findall(r"LOST(?:_SAMPLES)? events:\s+(\d+)", stats))
			throttle = sum(int(x) for x in re.findall(r"THROTTLE events:\s+(\d+)", stats))
			target = sum(x["samples"] for x in rows)
			assert target == comms.get("s2", 0), (label, target, comms)
			result[label] = {"build_id": ids[base], "target_samples": target, "excluded_by_comm": {k: v for k, v in comms.items() if k != "s2"},
				"rows": rows, "lost": lost, "throttle": throttle}
	pathlib.Path(out).write_text(json.dumps(result, indent=1) + "\n")
	excl = sum(sum(v["excluded_by_comm"].values()) for v in result.values())
	print(len(result), "repeats re-extracted; wrapper samples excluded in total:", excl)


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])
