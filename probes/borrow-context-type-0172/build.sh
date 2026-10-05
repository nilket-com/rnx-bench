#!/usr/bin/env bash
# 0172: base = fork main bb8e6937 (~/work/rune), candidate = branch w2-0172-borrow-context-type (~/work/rune-w2-0172).
# Harness sources are exact copies of rnx-bench fb56b1d probes/rune-runtime (SOURCES-fb56b1d.sha256).
# Builds primary, counter and allocation variants of each, plus 0169's resident driver. Run under the shared lock.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
test "$(git -C /home/me/work/rune rev-parse HEAD)" = bb8e69372353c50e271c9f115bc771c77aa6b83e
git -C /home/me/work/rune diff --quiet && git -C /home/me/work/rune diff --cached --quiet
test "$(git -C /home/me/work/rune-w2-0172 rev-parse HEAD)" = "${CANDIDATE_REV:?set CANDIDATE_REV to the full hash}"
git -C /home/me/work/rune-w2-0172 diff --quiet && git -C /home/me/work/rune-w2-0172 diff --cached --quiet
(cd "$here" && sed 's|  new/|  base/|' SOURCES-fb56b1d.sha256 | sed 's|^\(.*\)  \(harness.rs\|alloc_track.rs\|plan_clock.rs\)$|\1  \2|' | grep -v Cargo.toml | sha256sum -c --quiet)
for v in base cand; do
	m="$here/$v/Cargo.toml"
	for kind in primary counter allocation; do
		feat=(); [ "$kind" = primary ] || feat=(--features "$kind")
		env -u RUSTFLAGS CARGO_INCREMENTAL=0 cargo build --release "${feat[@]}" --manifest-path "$m"
		cp "$here/$v/target/release/rune-base-new" "$here/$v/target/release/$kind"
	done
done
mkdir -p "$here/target"
rustc -O "$here/plan_clock.rs" -o "$here/target/plan-clock"
