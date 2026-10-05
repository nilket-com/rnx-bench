#!/usr/bin/env bash
# 0171 diagnostic (descriptive, pre-agreed): S2 instruction samples of whole context-mode invocations
# (process start, default-context construction and drop, teardown), base vs candidate.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
out=$1
for v in base cand; do
	exe="$here/$v/target/profiling2/sfp-$v"
	for i in 1 2 3; do
		taskset -c 4 perf stat -x, --cputype core -e instructions:u -- "$exe" context 2>&1 | grep instructions | cut -d, -f1 | sed "s/^/s2-$v context /"
	done
	for r in 0 1 2; do
		taskset -c 4 perf record -q -e cpu_core/instructions/u -c 500000 -o "$out/$v-$r.data" -- bash -c 'for i in $(seq 130); do "$0" context; done' "$exe"
	done
done
