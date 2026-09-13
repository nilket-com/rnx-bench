#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
unset RNX_PROFILE_MODULES
mkdir -p results
cargo build --release --locked --offline > results/build.log 2>&1
{
  date -Is
  rustc -Vv
  cargo --version
  hyperfine --version
  uname -a
  lscpu
  sha256sum target/release/context-registration Cargo.lock instrumentation.patch
  cargo tree -e features --locked --offline
} > results/environment.txt
python3 measure.py > results/summary.txt
taskset -c 4 hyperfine -N --warmup 10 --runs 100 \
  --export-json results/process.json --export-markdown results/process.md \
  -n empty 'target/release/context-registration empty' \
  -n context 'target/release/context-registration' \
  -n instrumented 'env RNX_PROFILE_MODULES=1 target/release/context-registration' \
  > results/hyperfine.txt 2>&1
