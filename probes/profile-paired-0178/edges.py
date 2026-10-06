#!/usr/bin/env python3
"""Inspect retained single-Ir, line-position Callgrind graphs; execute no subjects."""
import collections
import hashlib
import json
import lzma
import re
import sys
from pathlib import Path


def parse(text):
    names = {key: {} for key in ('fn', 'ob', 'fl')}
    nodes = {}
    edges = collections.defaultdict(lambda: [0, 0])
    current = None
    obj = None
    file = None
    callee = None
    pending = None
    summary = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('positions:'):
            assert line == 'positions: line', 'unsupported positions'
        elif line.startswith('events:'):
            assert line == 'events: Ir', 'unsupported events'
        elif line.startswith('summary:'):
            assert summary is None
            summary = int(line.split(':')[1]); assert summary > 0
        elif re.match(r'^(?:c?fn|c?ob|cfi|fi|fe|fl)=', line):
            assert pending is None, 'missing edge cost'
            match = re.fullmatch(r'(fn|cfn|ob|cob|fl|fi|fe|cfi)=\((\d+)\)(?: (.*))?', line)
            assert match, 'unrecognized compressed identity'
            kind, ident, name = match.groups()
            group = 'fn' if kind.endswith('fn') else 'ob' if kind.endswith('ob') else 'fl'
            if name is not None:
                assert ident not in names[group] or names[group][ident] == name, 'identity renamed'
                names[group][ident] = name
            if kind == 'fn':
                current = ident; callee = None
                node = nodes.setdefault(ident, {'exclusive_ir': 0, 'objects': set(), 'files': set()})
                if obj is not None: node['objects'].add(obj)
                if file is not None: node['files'].add(file)
            elif kind == 'ob': obj = ident
            elif kind in ('fl', 'fi', 'fe'): file = ident
            elif kind == 'cfn': callee = ident
        elif line.startswith('calls='):
            assert current is not None and callee is not None and pending is None
            match = re.fullmatch(r'calls=(\d+) (?:\d+|\*|[+-]\d+)', line)
            assert match, 'unrecognized calls'
            pending = int(match[1])
        elif re.match(r'^(?:\d+|\*|[+-]\d+) ', line):
            assert current is not None
            match = re.fullmatch(r'(?:\d+|\*|[+-]\d+) (\d+)', line)
            assert match, 'invalid single-Ir cost'
            cost = int(match[1])
            if pending is not None:
                edge = edges[(current, callee)]; edge[0] += pending; edge[1] += cost
                pending = None
            else: nodes[current]['exclusive_ir'] += cost
        elif line.startswith(('version:', 'creator:', 'pid:', 'cmd:', 'part:', 'desc:', 'totals:')):
            pass
        else:
            raise AssertionError('unrecognized line: ' + line[:100])
    assert pending is None and summary is not None
    for ident, node in nodes.items():
        assert ident in names['fn'], 'unresolved function identity'
        node['name'] = names['fn'][ident]
        node['objects'] = sorted(names['ob'][x] for x in node['objects'])
        node['files'] = sorted(names['fl'][x] for x in node['files'])
    assert sum(node['exclusive_ir'] for node in nodes.values()) == summary, 'exclusive total mismatch'
    for caller, callee in edges:
        assert caller in nodes and callee in names['fn'], 'unresolved edge identity'
    return summary, nodes, edges


def controls():
    fixture = '''positions: line\nevents: Ir\nsummary: 8\nob=(1) binary\nfl=(1) ???\nfn=(1) caller\n0 3\ncfn=(2) target\ncalls=2 0\n0 10\n0 1\nfn=(2)\n0 4\n'''
    total, nodes, edges = parse(fixture)
    assert total == 8 and nodes['1']['exclusive_ir'] == 4 and edges[('1', '2')] == [2, 10]
    variants = [fixture.replace('events: Ir', 'events: Ir Dr'),
                fixture.replace('summary: 8', 'summary: 9'),
                fixture.replace('0 4', '0 -4'),
                fixture.replace('fn=(2)\n', 'fn=(2) renamed\n'),
                fixture.replace('0 10\n', '')]
    for variant in variants:
        try: parse(variant)
        except (AssertionError, ValueError): pass
        else: raise AssertionError('bad fixture accepted')
    duplicate_name = fixture.replace('summary: 8', 'summary: 9') + 'fn=(3) target\n0 1\n'
    _, nodes, _ = parse(duplicate_name)
    assert nodes['2']['name'] == nodes['3']['name'] and len(nodes) == 3
    return 7


def report(root):
    diagnostic = json.loads((root / 'diagnostic.json').read_text())
    targets = ['drop_glue::<rune::runtime::value::Repr>',
               'drop_glue::<rune::runtime::value::Value>', '::pop_call_frame', 'infallible_cmp']
    reports = {}
    for subject in ('base', 'cand'):
        for workload in ('context', 'run-fib', 'run-calls', 'run-numeric'):
            path = root / f'callgrind.out.{subject}.{workload}.xz'
            compressed = path.read_bytes(); raw = lzma.decompress(compressed)
            total, nodes, edges = parse(raw.decode())
            assert total == diagnostic['runs'][f'{subject}/{workload}']['ir_total']
            fast = {ident for ident, node in nodes.items() if '::try_range_dispatch' in node['name']}
            reachable = set(fast)
            while True:
                grown = reachable | {b for (a, b), (calls, _) in edges.items() if a in reachable and calls > 0}
                if grown == reachable: break
                reachable = grown
            selected = []
            for ident, node in nodes.items():
                if not any(target in node['name'] for target in targets): continue
                callers = []
                for (caller, target), (calls, ir) in edges.items():
                    if target != ident: continue
                    callers.append({'profile_id': caller, 'name': nodes[caller]['name'],
                                    'calls': calls, 'inclusive_edge_ir': ir,
                                    'reachable_from_executed_fast_path': caller in reachable})
                selected.append({'profile_id': ident, **node,
                                 'nm_identity': 'ambiguous' if node['name'].startswith('core::ptr::drop_glue') else 'check retained nm',
                                 'callers': sorted(callers, key=lambda x: -x['inclusive_edge_ir'])})
            reports[f'{subject}/{workload}'] = {
                'compressed_sha256': hashlib.sha256(compressed).hexdigest(),
                'raw_sha256': hashlib.sha256(raw).hexdigest(), 'ir_total': total,
                'exclusive_sum': sum(x['exclusive_ir'] for x in nodes.values()),
                'executed_fast_path_ids': sorted(fast),
                'fast_path_direct_callees': [
                    {'profile_id': target, 'name': nodes[target]['name'],
                     'calls': calls, 'inclusive_edge_ir': ir}
                    for (caller, target), (calls, ir) in edges.items() if caller in fast],
                'targets': selected,
            }
    return {'controls': controls(), 'profiles': reports,
            'limits': ['Profile ids are local compressed function identities, not unique nm addresses.',
                       'Reachability covers executed edges in this profile only; absent edges are not absent static callers.',
                       'Edge Ir is inclusive; do not sum it with exclusive Ir or recursive edges.',
                       'No subject executions, new disassembly, compilation or measurements.']}


if __name__ == '__main__':
    controls()  # Must pass before opening any real profile.
    print(json.dumps(report(Path(sys.argv[1])), indent=2))
