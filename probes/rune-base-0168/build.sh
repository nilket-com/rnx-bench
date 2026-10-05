#!/usr/bin/env bash
set -euo pipefail
probe_dir=$(cd -- "$(dirname -- "$0")" && pwd)
# The path dependency deliberately uses the pinned local fork; never update it here.
test "$(git -C /home/me/work/rune rev-parse HEAD)" = bb8e69372353c50e271c9f115bc771c77aa6b83e
git -C /home/me/work/rune diff --quiet
git -C /home/me/work/rune diff --cached --quiet
for base in old new; do
  manifest="$probe_dir/$base/Cargo.toml"
  cargo build --locked --release --manifest-path "$manifest"
  cp "$probe_dir/$base/target/release/rune-base-$base" "$probe_dir/$base/target/release/primary"
  cargo build --locked --release --features counter --manifest-path "$manifest"
  cp "$probe_dir/$base/target/release/rune-base-$base" "$probe_dir/$base/target/release/counter"
  cargo build --locked --release --features allocation --manifest-path "$manifest"
  cp "$probe_dir/$base/target/release/rune-base-$base" "$probe_dir/$base/target/release/allocation"
done
