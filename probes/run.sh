#!/usr/bin/env bash
set -eu
export PATH=$HOME/.cargo/bin:$PATH
P=$(cd "$(dirname "$0")" && pwd); B=$(dirname "$P")
for c in context-phases companion-modules; do (cd "$P/$c" && cargo build --release --locked 2>&1 | tail -1); done
CP=$P/context-phases/target/release/phase; CM=$P/companion-modules/target/release/mods
{ rustc --version; echo "rune 0.14.2, rune-modules 0.14.2"; echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2)"; echo "host: $(hostname) $(uname -r)"; echo "date: $(date -Is)"; ls -la "$CP" "$CM" | awk '{print $NF, $5/1048576 " MiB"}'; } > "$B/results/probes_versions.txt"
taskset -c 4 hyperfine -N --warmup 10 --runs 100 --export-json "$B/results/probes.json" --export-markdown "$B/results/probes.md" \
 -n 'phases: none' "$CP none" -n 'phases: context' "$CP context" -n 'phases: runtime' "$CP runtime" -n 'phases: compile' "$CP compile" -n 'phases: run' "$CP run" \
 -n 'modules: none' "$CM none" -n 'modules: default context' "$CM context" -n 'modules: + all but http' "$CM nohttp" -n 'modules: + all incl http' "$CM modules" -n 'modules: + tokio rt + async call' "$CM run"
