#!/usr/bin/env python3
"""Read-only independent audit of retained 0178 diagnostic receipts."""
import json
import lzma
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
diagnostic = json.loads((root / 'diagnostic.json').read_text())
assert diagnostic['status'] == 'complete'
ledger = [json.loads(line) for line in lzma.open(root / 'commands.jsonl.xz', 'rt')]
assert len(ledger) == 4 + 6 + sum(len(x['disassembly']) for x in diagnostic['subjects'].values()) + 24 * 3
for row in ledger:
	assert row['status'] == 0 and row['reaped']
	assert not row['timed_out'] and not row['interrupted'] and not row['group_survivors']
assert sum(row['kind'] == 'callgrind' for row in ledger) == 24
assert sum(row['kind'] == 'annotate' for row in ledger) == 48
runs = {}
for key, run in diagnostic['runs'].items():
	subject, workload = key.split('/')
	raw = lzma.open(root / f'callgrind.out.{subject}.{workload}.xz', 'rt').read()
	assert re.search(r'^events: Ir$', raw, re.M)
	summaries = re.findall(r'^summary: (\d+)$', raw, re.M)
	assert len(summaries) == 1 and int(summaries[0]) == run['ir_total'] > 0
	rows = [row for row in ledger if row['kind'] == 'callgrind'
			and row['subject'] == subject and row['workload'] == workload]
	assert len(rows) == 1
	collected = re.search(r'Collected\s*:\s*([\d,]+)', rows[0]['stderr'])
	assert collected and int(collected[1].replace(',', '')) == run['ir_total']
	for table in run['tables'].values():
		text = (root / table).read_text()
		total = re.search(r'([\d,]+)\s+\(100\.0%\)\s+PROGRAM TOTALS', text)
		assert total and int(total[1].replace(',', '')) == run['ir_total']
	runs[key] = run['ir_total']
symbols = {}
for subject, data in diagnostic['subjects'].items():
	nm = lzma.open(root / f'nm.{subject}.txt.xz', 'rt').read()
	rows = [row for row in ledger if row['kind'] == 'nm' and row['subject'] == subject]
	assert len(rows) == 1 and rows[0]['stdout'] == nm
	parsed = [line.split(maxsplit=3) for line in nm.splitlines()]
	for name, entries in data['symbols'].items():
		if isinstance(entries, list):
			for entry in entries:
				assert any(len(row) == 4 and row[3] == entry['symbol']
						   and int(row[0], 16) == entry['address']
						   and int(row[1], 16) == entry['bytes'] for row in parsed)
		else:
			assert not any(len(row) == 4 and row[3] == f'<rune::runtime::vm::Vm>::{name}'
						   for row in parsed)
	symbols[subject] = {
		'run_bytes': data['symbols']['run'][0]['bytes'],
		'op_call_bytes': data['symbols']['op_call'][0]['bytes'],
		'repr_drop_symbols': sum(len(row) == 4 and row[3] ==
			'core::ptr::drop_glue::<rune::runtime::value::Repr>' for row in parsed),
	}
print(json.dumps({'status': 'PASS', 'commands': len(ledger), 'runs': runs,
				  'symbols': symbols, 'limits': [
					  'Ir is Callgrind instrumented events, not native PMU instructions.',
					  'Exclusive attribution may move across function boundaries.',
					  'Repr drop symbols exist in both base and candidate; absence from a thresholded table does not mean absent work.',
					  'No causal intervention identifies why the compiled code changed.'
				  ]}, indent=2))
