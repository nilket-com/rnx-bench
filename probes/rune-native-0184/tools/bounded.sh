#!/bin/bash
# Bounded seal-time build/test runner (rnx 0184 FUEL probe): bounded.sh LABEL TIMEOUT_S CWD -- ENV=... cmd args...
# Admission: refused (rc 98, nothing run) unless / has >= 30 GiB available. Watchdog: below 25 GiB available while
# running, the timeout process gets SIGINT (logged as WATCHDOG; a STOP). Holds /tmp/rnx-runtime-bench.lock (exclusive;
# no concurrent runtime measurement). Writes ../logs/LABEL.{log,rc,meta}; never retries.
set -u
R=/home/me/work/.reviews/0184-fuel-probe1
label=$1; to=$2; cwd=$3; shift 3
[ "$1" = "--" ] && shift
meta=$R/logs/$label.meta
avail=$(df -BG --output=avail / | tail -n 1 | tr -d ' G')
if [ "$avail" -lt 30 ]; then echo "REFUSED $(date -Iseconds): df avail=${avail}G < 30G" > $meta; echo "rc=98" > $R/logs/$label.rc; exit 98; fi
argv=(flock /tmp/rnx-runtime-bench.lock nice -n 19 ionice -c3 timeout --signal=INT --kill-after=10 "$to" env -u PERF_BUILDID_DIR "$@")
{ echo "## $label start $(date -Iseconds) df_avail_start=${avail}G"; echo "\$ (cd $cwd) ${argv[*]} </dev/null > logs/$label.log 2>&1"; } > $meta
start=$(date +%s.%N)
(cd "$cwd" && exec "${argv[@]}" </dev/null > $R/logs/$label.log 2>&1) &
pid=$!
wd=""
while kill -0 $pid 2>/dev/null; do
	a=$(df -BG --output=avail / | tail -n 1 | tr -d ' G')
	if [ "$a" -lt 25 ]; then
		wd="WATCHDOG df=${a}G"
		pkill -INT -f "^timeout --signal=INT --kill-after=10 $to env -u PERF_BUILDID_DIR" 2>/dev/null
		echo "$wd" >> $R/logs/$label.log
		break
	fi
	sleep 2
done
wait $pid
rc=$?
end=$(date +%s.%N)
echo "rc=$rc" > $R/logs/$label.rc
echo "end $(date -Iseconds) rc=$rc wall_s=$(python3 -I -B -c "print(f'{$end-$start:.3f}')") df_avail_end=$(df -BG --output=avail / | tail -n 1 | tr -d ' ') $wd" >> $meta
exit $rc
