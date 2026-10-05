#!/usr/bin/env bash
# 0170: symbolized frame-pointer builds of the unmodified 0168 harnesses (old 0.14.2, new fork main).
# Run under the shared lock: flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock ./build.sh
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
test "$(git -C /home/me/work/rune rev-parse HEAD)" = bb8e69372353c50e271c9f115bc771c77aa6b83e
git -C /home/me/work/rune diff --quiet
git -C /home/me/work/rune diff --cached --quiet
for base in old new; do
	# The lock files are the 0168 ones; package renames don't change the dependency graph.
	RUSTFLAGS="-C force-frame-pointers=yes" CARGO_INCREMENTAL=0 cargo build --profile profiling --manifest-path "$here/$base/Cargo.toml"
	cp "$here/$base/target/profiling/interp-$base" "$here/$base/target/profiling/symbolized"
done
