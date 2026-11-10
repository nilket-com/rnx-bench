#!/usr/bin/env python3
"""Check reviewed data retention and duplicate limits."""
import json
from pathlib import Path
from data_hygiene import scan

if __name__ == '__main__':
	failures=scan(Path(__file__).resolve().parents[1])
	print(json.dumps({'status':'FAIL' if failures else 'PASS','failures':failures},indent=2))
	raise SystemExit(bool(failures))
