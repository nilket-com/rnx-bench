#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
unset RNX_PROFILE_MODULES RNX_PROFILE_STAGES RNX_PROFILE_TRAITS
mkdir -p results/stages results/traits
cargo build --release --locked --offline > results/stages/build.log 2>&1
{
  date -Is
  rustc -Vv
  cargo --version
  uname -a
  lscpu
  sha256sum target/release/context-registration Cargo.lock *instrumentation.patch
  cargo tree -e features --locked --offline
} > results/stages/environment.txt
python3 measure_stages.py > results/stages/report.txt
python3 measure_traits.py > results/traits/report.txt
