#!/bin/bash
# Builds the two Rune subjects of the FUEL probe (rnx 0184, revision fuel) ONCE each, from ONE source
# (346623b6, detached worktree rune-fuel-probe), ONE harness Cargo.lock (b65e3a87..., byte-identical to
# revisions 6's and r3's) and ONE profile (harness-rune/Cargo.toml [profile.release]), with --locked; only the
# `native` feature differs. Bounded: per build `timeout 3600`; admission: refused (rc 98, nothing built)
# unless / has >= 30 GiB available; disk watchdog: below 25 GiB available while building, the build's
# timeout process gets SIGINT (logged as WATCHDOG; a STOP). The exclusive runtime lock
# /tmp/rnx-runtime-bench.lock is held for each build (no concurrent runtime measurement).
# Per subject it writes ../logs/probe-build-<subject>.{txt,rc,meta}. No retry, no rebuild.
set -u
P=/home/me/work/.reviews/0184-fuel-probe1/probe
R=/home/me/work/.reviews/0184-fuel-probe1
W=/home/me/work/.worktrees/rune-fuel-probe
for subject in fuel-on fuel-off; do
	if [ $subject = fuel-on ]; then feat=(--features native); td=/home/me/work/.targets/rune-fuel-probe-on; else feat=(); td=/home/me/work/.targets/rune-fuel-probe-off; fi
	meta=$R/logs/probe-build-$subject.meta
	avail=$(df -BG --output=avail / | tail -n 1 | tr -d ' G')
	if [ "$avail" -lt 30 ]; then
		echo "REFUSED $(date -Iseconds): df avail=${avail}G < 30G; nothing built" > $meta
		echo "rc=98" > $R/logs/probe-build-$subject.rc
		echo "$subject REFUSED (df ${avail}G)"; exit 98
	fi
	if [ -e $td ]; then
		echo "REFUSED $(date -Iseconds): target dir $td already exists (new targets only); nothing built" > $meta
		echo "rc=97" > $R/logs/probe-build-$subject.rc
		echo "$subject REFUSED (target exists)"; exit 97
	fi
	argv=(flock /tmp/rnx-runtime-bench.lock nice -n 19 ionice -c3 timeout --signal=INT --kill-after=10 3600 env -u PERF_BUILDID_DIR CARGO_TARGET_DIR=$td CARGO_INCREMENTAL=0 cargo build --release --locked -j8 "${feat[@]}")
	{
		echo "## probe-build-$subject start $(date -Iseconds)"
		echo "worktree HEAD=$(git -C $W -c color.ui=false -c color.diff=false rev-parse HEAD </dev/null) dirty=$(git -C $W -c color.ui=false -c color.diff=false status --porcelain --untracked-files=no </dev/null | wc -l)"
		echo "harness Cargo.lock=$(sha256sum $P/harness-rune/Cargo.lock | cut -c1-64) workspace Cargo.lock=$(sha256sum $W/Cargo.lock | cut -c1-64) Cargo.toml=$(sha256sum $P/harness-rune/Cargo.toml | cut -c1-64) main.rs=$(sha256sum $P/harness-rune/src/main.rs | cut -c1-64)"
		echo "df_avail_start=${avail}G"
		echo "\$ (cd $P/harness-rune) ${argv[*]} </dev/null > logs/probe-build-$subject.txt 2>&1"
	} > $meta
	start=$(date +%s.%N)
	(cd $P/harness-rune && exec "${argv[@]}" </dev/null > $R/logs/probe-build-$subject.txt 2>&1) &
	pid=$!
	wd=""
	while kill -0 $pid 2>/dev/null; do
		a=$(df -BG --output=avail / | tail -n 1 | tr -d ' G')
		if [ "$a" -lt 25 ]; then
			wd="WATCHDOG df=${a}G"
			pkill -INT -f "^timeout --signal=INT --kill-after=10 3600 env -u PERF_BUILDID_DIR CARGO_TARGET_DIR=$td" 2>/dev/null
			echo "$wd" >> $R/logs/probe-build-$subject.txt
			break
		fi
		sleep 2
	done
	wait $pid
	rc=$?
	end=$(date +%s.%N)
	echo "rc=$rc" > $R/logs/probe-build-$subject.rc
	{
		echo "end $(date -Iseconds) rc=$rc wall_s=$(python3 -I -B -c "print(f'{$end-$start:.3f}')") ${wd}"
		echo "binary=$td/release/p2-probe-harness sha256=$(sha256sum $td/release/p2-probe-harness 2>/dev/null | cut -c1-64)"
		echo "harness Cargo.lock after=$(sha256sum $P/harness-rune/Cargo.lock | cut -c1-64) workspace Cargo.lock after=$(sha256sum $W/Cargo.lock | cut -c1-64) dirty_after=$(git -C $W -c color.ui=false -c color.diff=false status --porcelain --untracked-files=no </dev/null | wc -l)"
		echo "df_avail_end=$(df -BG --output=avail / | tail -n 1 | tr -d ' ')"
	} >> $meta
	echo "$subject rc=$rc $wd"
	if [ $rc -ne 0 ] || [ -n "$wd" ]; then echo "STOP: $subject build failed (rc=$rc $wd); no further build"; exit 1; fi
done
