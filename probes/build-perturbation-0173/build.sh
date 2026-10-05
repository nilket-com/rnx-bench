#!/usr/bin/env bash
# 0173 builds. Every subject compiles from ONE fork worktree path (~/work/rune-w-0173), checked out at the subject's
# commit, and ONE harness path, into its own equal-length target directory, so embedded source paths are identical.
# A0/A1/A2: three clean builds of the parent 3e7d4da9. C0..C4: the sibling null edits.
# Run under: flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock ./build.sh
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
fork=/home/me/work/rune-w-0173
declare -A rev=(
	[a0]=3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a [a1]=3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a [a2]=3e7d4da9ce908eeb7e0e1ac119dec24f68d5449a
	[c0]=20aeb673ce7eee0831fcd7961b6729a252e4418a [c1]=420fdfcc5264a52ef4c5092ab94fba04553897e1 [c2]=7f84fb769a7a42a25612b5350d0ced95e4b79e32
	[c3]=59aba32ea330c0efb521e685092550fcc24038a3 [c4]=1e2b9ac2e1460f48687580421f3bd0349e0be1af
)
mkdir -p "$here/bin"
for s in a0 a1 a2 c0 c1 c2 c3 c4; do
	git -C "$fork" checkout -q --detach "${rev[$s]}"
	test "$(git -C "$fork" rev-parse HEAD)" = "${rev[$s]}"
	git -C "$fork" diff --quiet && git -C "$fork" diff --cached --quiet
	target="$here/tgt-$s"
	rm -rf -- "${target:?}"
	env -u RUSTFLAGS CARGO_INCREMENTAL=0 CARGO_TARGET_DIR="$target" cargo build --release --manifest-path "$here/harness/Cargo.toml"
	cp "$target/release/rune-base-new" "$here/bin/$s"
	echo "$s ${rev[$s]} $(sha256sum < "$here/bin/$s" | cut -d' ' -f1) text=$(objcopy -O binary --only-section=.text "$here/bin/$s" /dev/stdout | sha256sum | cut -d' ' -f1)"
done
