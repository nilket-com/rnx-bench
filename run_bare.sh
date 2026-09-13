#!/usr/bin/env bash
# Bare startup: evaluate the literal 42 and exit. Pinned to one core, 50 runs.
set -u
export R_LIBS_USER=$HOME/R/library
export PATH=$HOME/.cargo/bin:$HOME/.bun/bin:$HOME/.deno/bin:$HOME/.juliaup/bin:$HOME/.local/bin:$PATH
B=$(cd "$(dirname "$0")" && pwd); cd "$B/scripts"
NODE=$HOME/opt/node-v22.22.1-linux-x64/bin/node
RNX=$HOME/work/rnx/target/release/rnx
taskset -c 4 hyperfine -N --warmup 5 --runs 50 --export-json "$B/results/bare.json" --export-markdown "$B/results/bare.md" \
 -n 'true' /bin/true \
 -n 'rnx eval' "$RNX eval 42" \
 -n 'rnx run' "$RNX run bare.rn" \
 -n 'rnx version' "$RNX version" \
 -n python3 'python3 -c 42' \
 -n perl 'perl -e 42' \
 -n ruby 'ruby -e 42' \
 -n Rscript 'Rscript -e 42' \
 -n bun 'bun -e 42' \
 -n node_official "$NODE -e 42" \
 -n node_distro '/usr/bin/node -e 42' \
 -n deno 'deno eval 42' \
 -n lua54 'lua54 -e x=42' \
 -n luajit 'luajit -e x=42' \
 -n scala_jar 'java -jar jvm/bare-scala.jar' \
 -n kotlin_jar 'java -jar jvm/bare-kotlin.jar' \
 -n julia 'julia --startup-file=no -e 42'
