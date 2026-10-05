#!/usr/bin/env bash
# 0170 S2: release + line tables, NO frame pointers (the agreed replacement after the frame-pointer stop).
# Run under: flock --exclusive --timeout 1800 /tmp/rnx-runtime-bench.lock ./build-s2.sh
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
test "$(git -C /home/me/work/rune rev-parse HEAD)" = bb8e69372353c50e271c9f115bc771c77aa6b83e
git -C /home/me/work/rune diff --quiet
git -C /home/me/work/rune diff --cached --quiet
for base in old new; do
	env -u RUSTFLAGS CARGO_INCREMENTAL=0 cargo build --profile profiling2 --manifest-path "$here/$base/Cargo.toml"
	cp "$here/$base/target/profiling2/interp-$base" "$here/$base/target/profiling2/s2"
done
