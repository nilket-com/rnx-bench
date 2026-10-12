#!/bin/bash
# Live toolchain capture for the FUEL probe builds (rnx 0184, revision fuel). Reads only.
set -u
cd /home/me/work/.reviews/0184-fuel-probe1/probe/harness-rune || exit 1
echo "date: $(date -Iseconds)"
echo "rustup active toolchain (from harness-rune): $(rustup show active-toolchain)"
echo "--- rustc -vV"; rustc -vV
echo "--- cargo -V"; cargo -V
echo "--- which"; which rustc cargo cc
SR=$(rustc --print sysroot); echo "sysroot: $SR"
LLD=$SR/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld
echo "--- rust-lld: $LLD"; "$LLD" -flavor gnu --version; sha256sum "$LLD" "$SR"/lib/rustlib/x86_64-unknown-linux-gnu/bin/gcc-ld/ld.lld 2>&1
echo "--- rustc/cargo binaries"; sha256sum "$SR/bin/rustc" "$SR/bin/cargo" "$(readlink -f "$(which cc)")"
echo "--- cc --version"; cc --version | head -1
echo "--- rustc --print cfg (target features, linker flavour)"; rustc --print cfg | grep -E 'target_feature|target_arch|target_os'
echo "--- env keys (lengths only) relevant to builds"; env | grep -E '^(RUST|CARGO|CC|CFLAGS|LDFLAGS)' | while IFS='=' read -r k v; do echo "$k len=${#v}"; done; echo "(end of env list)"
echo "--- cargo config files"; ls -la ~/.cargo/config.toml ~/.cargo/config /home/me/work/.cargo/config.toml /home/me/work/.reviews/.cargo 2>&1 | sed 's/^/  /'
