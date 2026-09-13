#!/usr/bin/env bash
# Reproducible 10,000-iteration JSON serialisation benchmark across runtimes.
# Every command is a single argv (no shell), pinned to one core, 30 runs.
set -u
export R_LIBS_USER=$HOME/R/library
export PATH=$HOME/.cargo/bin:$HOME/.bun/bin:$HOME/.deno/bin:$HOME/.juliaup/bin:$HOME/.local/bin:$PATH
B=$(cd "$(dirname "$0")" && pwd); cd "$B/scripts"
NODE=$HOME/opt/node-v22.22.1-linux-x64/bin/node
RNX=$HOME/work/rnx/target/release/rnx
names=(rnx python3 perl_pp perl_xs ruby bun node_official node_distro deno lua54_cjson lua54_pure luajit_cjson luajit_pure scala_jar kotlin_jar rscript julia)
cmds=(
 "$RNX run json.rn"
 "python3 bench_json.py"
 "perl json.pl"
 "perl json_xs.pl"
 "ruby json.rb"
 "bun json.js"
 "$NODE json.js"
 "/usr/bin/node json.js"
 "deno run json.js"
 "lua54 json_cjson.lua"
 "lua54 json_pure.lua"
 "luajit json_cjson.lua"
 "luajit json_pure.lua"
 "java -jar jvm/json-scala.jar"
 "java -cp jvm/json-kotlin.jar:/home/me/opt/json.jar JsonKt"
 "Rscript json.R"
 "julia --startup-file=no json.jl"
)
echo "== output equivalence: exit status 0, stdout exactly one line, canonicalised with sorted keys ==" | tee "$B/results/json_outputs.txt"
ok=1
for i in "${!names[@]}"; do
  out=$(${cmds[$i]} 2>"$B/results/.stderr"); status=$?
  lines=$(printf '%s\n' "$out" | grep -c '')
  canon=$(cd / && python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]),sort_keys=True,separators=(",",":")))' "$out" 2>/dev/null || echo INVALID)
  printf '%-13s status=%s lines=%s canon=%s raw=%s\n' "${names[$i]}" "$status" "$lines" "$canon" "$out" | tee -a "$B/results/json_outputs.txt"
  [ "$status" = 0 ] && [ "$lines" = 1 ] && [ "$canon" = '{"a":[9999,2,3],"b":"hello"}' ] || ok=0
done
rm -f "$B/results/.stderr"
[ $ok = 1 ] && echo "ALL EQUIVALENT" | tee -a "$B/results/json_outputs.txt" || { echo "MISMATCH — not benchmarking"; exit 1; }
{ $RNX version; python3 --version; echo "bun $(bun --version)"; echo "node official $($NODE --version)"; echo "node distro $(/usr/bin/node --version) (node_use_node_snapshot=false)"; deno --version|head -1; lua54 -v; luajit -v; julia --version; perl -e "print \"perl $^V JSON::PP (pure perl) and JSON::XS (C)\\n\""; java -version 2>&1 | head -1; ruby --version; echo "$(Rscript --version) jsonlite $(Rscript -e "cat(as.character(packageVersion(\"jsonlite\")))")"; echo "scala-cli $(scala-cli version 2>/dev/null | head -1 | cut -d: -f2) scala 3.9.0 upickle 4.2.1, AOT assembly jar"; echo "kotlinc $(kotlinc -version 2>&1 | grep -o "kotlinc-jvm [0-9.]*") org.json 20250517, AOT jar"; echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2)"; echo "host: $(hostname) $(uname -r)"; echo "date: $(date -Is)"; echo "hyperfine $(hyperfine --version)"; } > "$B/results/versions.txt" 2>&1
args=(); for i in "${!names[@]}"; do args+=(-n "${names[$i]}" "${cmds[$i]}"); done
taskset -c 4 hyperfine -N --warmup 3 --runs 30 --export-json "$B/results/json_loop.json" --export-markdown "$B/results/json_loop.md" "${args[@]}"
