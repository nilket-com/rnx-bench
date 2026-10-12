#!/usr/bin/env python3
"""Launch-readiness wait for the R2 timing session (rnx 0184, revision 6; Codex 8173: "wait for
load <1.5 ... and check memory/headroom too; no silent prelaunch exception").

Reads only (/proc/loadavg, /proc/meminfo, statvfs); runs no subject and times nothing. Prints
ONE line per reading, ready or not, so every refusal is kept. Exit status:
  0  the first reading with ALL of: load1 < 1.5 (strict), MemAvailable >= 4 GiB, and at least
     40 GiB available on / and on /home/me/work/.reviews. Step 3 may start.
  2  no such reading within BOUND_S (3,600 s, polling every POLL_S = 30 s): STOP, do not
     launch, preserve the file and report. There is no other exit path to step 3.

usage: python3 -I -B launch_ready.py </dev/null > S/pre/launch-ready.txt 2>&1; echo "rc=$?" > S/pre/launch-ready.rc
"""
import os, shutil, sys, time

LOAD1_LT = 1.5
MEM_MIN = 4 << 30
DISK_MIN = 40 << 30
DISKS = ("/", "/home/me/work/.reviews")
POLL_S = 30
BOUND_S = 3600


def mem_available():
	for line in open("/proc/meminfo"):
		if line.startswith("MemAvailable:"):
			return int(line.split()[1]) * 1024
	return 0


def reading():
	load = os.getloadavg()
	mem = mem_available()
	disks = {d: shutil.disk_usage(d).free for d in DISKS}
	ready = load[0] < LOAD1_LT and mem >= MEM_MIN and all(v >= DISK_MIN for v in disks.values())
	return load, mem, disks, ready


def main():
	start = time.monotonic()
	n = 0
	print(f"launch readiness rule: load1 < {LOAD1_LT} AND MemAvailable >= {MEM_MIN} B AND available >= {DISK_MIN} B on "
		f"{', '.join(DISKS)}; poll {POLL_S} s; bound {BOUND_S} s", flush=True)
	while True:
		n += 1
		load, mem, disks, ready = reading()
		print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} reading={n} loadavg={load[0]:.2f}/{load[1]:.2f}/{load[2]:.2f} "
			f"mem_available={mem} " + " ".join(f"avail[{d}]={v}" for d, v in disks.items())
			+ (" READY" if ready else " NOT READY"), flush=True)
		if ready:
			print("LAUNCH READY: step 3 may start now", flush=True)
			return 0
		if time.monotonic() - start + POLL_S > BOUND_S:
			print(f"NOT READY within {BOUND_S} s: STOP, do not launch; preserve this file and report", flush=True)
			return 2
		time.sleep(POLL_S)


if __name__ == "__main__":
	sys.exit(main())
