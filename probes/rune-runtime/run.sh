#!/usr/bin/env bash
set -euo pipefail
probe_dir=$(cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$probe_dir/runner.py" "$@"
