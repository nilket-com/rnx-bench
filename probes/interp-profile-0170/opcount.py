"""rnx 0170 step E: dynamic instruction counts by kind (diagnostic builds, never timed) plus on/off semantic checks.

	flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock python3 opcount.py OUT_DIR
"""
import json, os, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts import EXPECT, binary, kernel, held_lock, sha

WORKS = ["empty", "answer", "numeric", "while", "fib", "calls", "compare", "vector", "strings"]
CORPUS = sorted(pathlib.Path("/home/me/work/rnx-bench/probes/rune-base-0168/fixtures").glob("*.rn"))


# Only these two known nondeterministic fields are normalized; everything else must match exactly.
NORMALIZE = [
	(re.compile(r"full_name: 0x[0-9a-f]+"), "full_name: <ptr>"),
	(re.compile(r"thread 'main' \(\d+\)"), "thread 'main' (<tid>)"),
]


def normalized(r):
	text = r[2]
	for rx, rep in NORMALIZE:
		text = rx.sub(rep, text)
	return (r[0], r[1], text)


def same(on, off):
	"""on/off are (status, stdout, stderr); equal after normalizing only the known fields."""
	return normalized(on) == normalized(off)


def controls():
	base = (1, "", "vm: VmError { kind: MissingInstanceFunction { instance: Any(AnyTypeInfo { full_name: 0x5b6, hash: 0xf4 }) } }")
	ok = same(base, (1, "", base[2].replace("0x5b6", "0x7ff"))) and same((-6, "", "thread 'main' (123) has overflowed its stack"), (-6, "", "thread 'main' (456) has overflowed its stack"))
	print("pass" if ok else "WRONG", ": known pointer/thread-id fields normalize")
	for name, other in [("changed stdout", (1, "x", base[2])), ("changed status", (0, "", base[2])),
			("unrelated VmError", (1, "", base[2].replace("MissingInstanceFunction", "StackOutOfBounds"))),
			("stack text but different status", (134, "", "thread 'main' (1) has overflowed its stack"))]:
		refused = not same(base, other)
		ok &= refused
		print("pass" if refused else "WRONG", ":", name, "refused")
	return ok


def main(out):
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=False)
	assert held_lock(), "run under the shared lock"
	builds = {b: HERE / f"opcount-{b}/target/release/opcount-{b}" for b in ("old", "new")}
	res = {"subjects": {b: sha(p) for b, p in builds.items()}, "patches": {p.name: sha(p) for p in (HERE / "opcount-patches").glob("*.patch")}, "workloads": {}, "corpus": {}}
	for base, exe in builds.items():
		for w in WORKS:
			f = out / f"{base}-{w}.json"
			r = subprocess.run([str(exe), "run", str(kernel(w))], capture_output=True, text=True, timeout=300, env={**os.environ, "RUNE_OP_COUNT_OUT": str(f)})
			assert r.returncode == 0 and r.stdout == EXPECT[w] and not r.stderr, (base, w, r.stdout[:100], r.stderr[:300])
			assert f.exists(), (base, w, "opcode count file missing")
			counts = json.loads(f.read_text())
			assert counts and all(isinstance(v, int) and v > 0 for v in counts.values()), (base, w, counts)
			res["workloads"][f"{base}-{w}"] = {"counts": counts, "total": sum(counts.values())}
			print(base, w, sum(counts.values()), flush=True)
		# On/off semantic check over the whole 0168 corpus: status, stdout, stderr identical to the unmodified primary.
		for fx in CORPUS:
			args = [str(fx)] + (["2000000"] if fx.stem == "budget" else [])
			mode = "async" if fx.stem == "async" else "run"
			on = subprocess.run([str(exe), mode, *args], capture_output=True, text=True, timeout=300)
			off = subprocess.run([str(binary(base, "primary")), mode, *args], capture_output=True, text=True, timeout=300)
			a, b = (on.returncode, on.stdout, on.stderr), (off.returncode, off.stdout, off.stderr)
			res["corpus"][f"{base}-{fx.stem}"] = {"raw_identical": a == b, "identical_after_normalizing": same(a, b),
				"on": list(a), "off": list(b)}
			assert same(a, b), (base, fx.stem, a[0], b[0], a[2][:200], b[2][:200])
	(out / "opcount.json").write_text(json.dumps(res, indent=1) + "\n")
	raw = sum(v["raw_identical"] for v in res["corpus"].values())
	print("corpus on/off: raw identical", raw, "/", len(res["corpus"]), "; all identical after normalizing the two known fields")


if __name__ == "__main__":
	if sys.argv[1:] == ["--controls"]:
		sys.exit(0 if controls() else 1)
	main(sys.argv[1])
