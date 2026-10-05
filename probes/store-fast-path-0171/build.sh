#!/usr/bin/env bash
# 0171: base = fork main bb8e6937 (~/work/rune), candidate = branch w3-0171-store-fast-path (~/work/rune-w3-0171).
# Same harness source, lock, release profile and features. Run under the shared lock.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
test "$(git -C /home/me/work/rune rev-parse HEAD)" = bb8e69372353c50e271c9f115bc771c77aa6b83e
git -C /home/me/work/rune diff --quiet && git -C /home/me/work/rune diff --cached --quiet
test "$(git -C /home/me/work/rune-w3-0171 rev-parse --short=8 HEAD)" = "${CANDIDATE_REV:?set CANDIDATE_REV}"
git -C /home/me/work/rune-w3-0171 diff --quiet && git -C /home/me/work/rune-w3-0171 diff --cached --quiet
for v in base cand; do
	env -u RUSTFLAGS CARGO_INCREMENTAL=0 cargo build --release --manifest-path "$here/$v/Cargo.toml"
	cp "$here/$v/target/release/sfp-$v" "$here/$v/target/release/primary"
done
rustc -O -o "$here/clock" "$here/clock.rs"
