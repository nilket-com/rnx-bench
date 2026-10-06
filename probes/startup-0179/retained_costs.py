#!/usr/bin/env python3
"""Read retained 0178 base evidence only; execute no engine or benchmark."""
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = ROOT / 'probes/profile-paired-0178/edges.py'
spec = importlib.util.spec_from_file_location('retained_edges', parser)
edges_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edges_module)
assert edges_module.controls() == 7
profile = ROOT / 'results/profile-paired-0178/diagnostic1/callgrind.out.p0-base.context.xz'
compressed = profile.read_bytes()
raw = lzma.decompress(compressed)
total, nodes, edges = edges_module.parse(raw.decode())
assert total == 27355056

def one(name):
	found = [ident for ident, row in nodes.items() if row['name'] == name]
	assert len(found) == 1, (name, found)
	return found[0]

assoc = one('<rune::compile::context::Context>::install_associated')
format_id = one('core::fmt::write')
item = one('<rune_core::item::item::Item as core::fmt::Display>::fmt')
clone = one('<rune::compile::context::ContextType as rune_alloc::clone::TryClone>::try_clone')
callee_rows = []
for (caller, callee), (calls, ir) in sorted(edges.items(), key=lambda row: -row[1][1]):
	if caller == assoc:
		callee_rows.append({'profile_id': callee, 'name': nodes[callee]['name'],
			'calls': calls, 'inclusive_edge_ir': ir})
format_calls, format_ir = edges[(assoc, format_id)]
assert (format_calls, format_ir) == (1785, 4929893)
item_callers = [{'profile_id': caller, 'name': nodes[caller]['name'], 'calls': calls,
	'inclusive_edge_ir': ir} for (caller, callee), (calls, ir) in edges.items() if callee == item]
assert sum(row['inclusive_edge_ir'] for row in item_callers) == 5078623
pmu_path = ROOT / 'results/profile-paired-0178/official1/p0-s75/pmu.json'
pmu = json.loads(pmu_path.read_text())
context = pmu['context']['instructions']['base_median']
answer = pmu['run-answer']['instructions']['base_median']
assert context == 26868541.5 and answer == 29905482.5
result = {
	'parser_sha256': hashlib.sha256(parser.read_bytes()).hexdigest(),
	'parser_controls': 7,
	'profile_compressed_sha256': hashlib.sha256(compressed).hexdigest(),
	'profile_raw_sha256': hashlib.sha256(raw).hexdigest(),
	'pmu_sha256': hashlib.sha256(pmu_path.read_bytes()).hexdigest(),
	'context_ir_total': total,
	'item_display_callers': item_callers,
	'associated_install_callees': callee_rows,
	'proposed_formatting_edge': {'calls': format_calls, 'inclusive_ir': format_ir,
		'fraction_of_context_ir': format_ir / total},
	'container_clone_edge': {'calls': edges[(assoc, clone)][0],
		'inclusive_ir': edges[(assoc, clone)][1]},
	'native_base_instructions': {'context': context, 'run-answer': answer,
		'run_answer_to_context': answer / context,
		'ten_percent_context': context * 0.1, 'ten_percent_run_answer': answer * 0.1},
	'illustrative_uniform_scaling_only': {
		'format_edge_context_fraction': format_ir / total,
		'format_edge_run_answer_fraction': format_ir / total * context / answer,
		'fraction_of_edge_needed_for_context_gate': 0.1 / (format_ir / total),
		'fraction_of_edge_needed_for_answer_gate': 0.1 / (format_ir / total * context / answer)},
	'limits': ['Ir and native instructions:u are distinct metrics; uniform scaling is a hypothesis, not a bound or prediction.',
		'Formatting edge is inclusive of string construction which the candidate still performs.',
		'Do not add ancestor, descendant or clone costs to claim an eliminated total.',
		'Profile ids are compressed Callgrind identities, not unique machine addresses.',
		'No candidate code, subject execution, compilation or new performance samples.']}
print(json.dumps(result, indent=2) + '\n', end='')
