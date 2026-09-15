#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${1:?before binary required}"
: "${2:?after binary required}"
out="$PWD/results/namespaces-0049"
mkdir -p "$out"
export PYTHONDONTWRITEBYTECODE=1
export RNX_NOTEBOOK_RESULTS="$out"
export RNX_JUPYTER_RESULTS="$out/supervision"
mkdir -p "$RNX_JUPYTER_RESULTS"
python3 probes/namespaces/measure.py "$1" "$2" > "$out/measure.txt" 2> "$out/measure-stderr.txt"
py=probes/jupyter-notebook/.venv/bin/python
"$py" probes/namespaces/notebook.py > "$out/notebook.jsonl" 2> "$out/notebook-stderr.txt"
"$py" probes/jupyter-notebook/browser.py > "$out/browser.jsonl" 2> "$out/browser-stderr.txt"
for name in probe extended boundaries notebook; do
 "$py" "probes/jupyter-supervision/$name.py" > "$RNX_JUPYTER_RESULTS/$name.jsonl" 2> "$RNX_JUPYTER_RESULTS/$name-stderr.txt"
done
