#!/usr/bin/env python3
"""Admission check for the FUEL probe (rnx 0184, revision fuel; Codex 8330). Reads only.

usage: check_admit.py LOG      exit 0 only when every pre-registered B1ADMIT row matches.

Used twice, on the same sealed expectation:
  - at SEAL, on logs/diag-release-listing.log: the release-profile cfg(test) build of 346623b6 that
    also writes the compile-only listing runs w13_kernel_listings and b1_probe_kernel_admission
    ONLY (B1ADMIT rows carry counts and sizes, no ns; p2_probe_kernel_admission, whose P2ADMIT rows
    carry analysis/compile/load ns, is NOT run at seal);
  - at launch step 1d (after the timing GO), on diag/step1d.log (b1 + p2 admission, as R3's 1d).

Pre-registered (sealed BEFORE the seal run; READINESS.md), release profile, commit 346623b6:
  v2/calls      loaded=1 code_bytes=721
  stage/calls   loaded=1 code_bytes=721
  v2/while      loaded=1 code_bytes=295
  v2/numeric    loaded=1 code_bytes=552
  v2/fib        candidates=0 loaded=0
  v2/shared_rows loaded=0, analysis f1h1:SideEntry { pc: 17 }
All six are OBSERVED at 346623b6 in the DEV profile (0184-fuel-impl1/logs/final-06-test-lib-on.log).
The dev rows are printed beside (descriptive: full-row equality is reported, not gated).
Rows may share a line with libtest's "test ..." prefix under --nocapture, so the match is unanchored.
"""
import re, sys

WANT = {
	"v2/calls": {"loaded": "1", "code_bytes": "721"},
	"stage/calls": {"loaded": "1", "code_bytes": "721"},
	"v2/while": {"loaded": "1", "code_bytes": "295"},
	"v2/numeric": {"loaded": "1", "code_bytes": "552"},
	"v2/fib": {"candidates": "0", "loaded": "0"},
	"v2/shared_rows": {"loaded": "0", "analysis": "f1h1:SideEntry { pc: 17 }"},
}
DEV = {
	"v2/while": "candidates=1\tregions=1\tloaded=1\tcode_bytes=295\tmetadata_bytes=1012\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=f0h1:admitted",
	"v2/numeric": "candidates=1\tregions=1\tloaded=1\tcode_bytes=552\tmetadata_bytes=1028\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=f0h2:admitted",
	"v2/calls": "candidates=1\tregions=1\tloaded=1\tcode_bytes=721\tmetadata_bytes=1012\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=f0h4:admitted",
	"v2/fib": "candidates=0\tregions=0\tloaded=0\tcode_bytes=0\tmetadata_bytes=0\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=",
	"v2/shared_rows": "candidates=1\tregions=0\tloaded=0\tcode_bytes=0\tmetadata_bytes=0\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=f1h1:SideEntry { pc: 17 }",
	"stage/calls": "candidates=1\tregions=1\tloaded=1\tcode_bytes=721\tmetadata_bytes=1012\trefusals=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]\tanalysis=f0h5:admitted",
}


def main(path):
	rows = {}
	for line in open(path, errors="replace"):
		m = re.search(r"B1ADMIT\t(\S+)\t(.*)$", line.rstrip("\n"))
		if m:
			rows.setdefault(m.group(1), []).append(m.group(2))
	ok = True
	for name, want in WANT.items():
		got = rows.get(name, [])
		if len(got) != 1:
			print(f"FAIL {name}: {len(got)} rows (want exactly 1)")
			ok = False
			continue
		fields = dict(f.split("=", 1) for f in got[0].split("\t"))
		bad = {k: (fields.get(k), v) for k, v in want.items() if fields.get(k) != v}
		print(("OK  " if not bad else "FAIL") + f" {name}: {got[0]}" + (f"  mismatched {bad}" if bad else "")
			+ f"  [dev final-06 row {'identical' if got[0] == DEV[name] else 'DIFFERS (descriptive)'}]")
		ok &= not bad
	print("ADMISSION ROWS AS PRE-REGISTERED" if ok else "ADMISSION MISMATCH: STOP (at seal: no timing GO request; at launch: before step 3)")
	return 0 if ok else 1


if __name__ == "__main__":
	sys.exit(main(sys.argv[1]))
