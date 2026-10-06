"""Synthetic parser and contrast controls; no subject execution."""
import copy
import importlib.util
import json
import pathlib
import sys

spec = importlib.util.spec_from_file_location('static0180', pathlib.Path(__file__).with_name('static.py'))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def run():
	out = []
	def check(name, f, refusal=False):
		try:
			f()
		except ValueError:
			if not refusal:
				raise
		else:
			if refusal:
				raise AssertionError('accepted corruption: ' + name)
		out.append({'name': name, 'passed': True})
	def require(v):
		s.require(v, 'fixture mismatch')
	text = '0000000000000100 <foo>:\n 100: 90 nop\n 101: eb fd jmp 100 <foo>\n'
	xs = s.disassembly(text)[0x100]['instructions']
	check('contiguous extent', lambda: require(len(s.validate_region(0x100, 3, {'instructions': xs})) == 2))
	check('truncated extent', lambda: s.validate_region(0x100, 4, {'instructions': xs}), True)
	check('missing region', lambda: s.validate_region(0x100, 3, {'instructions': []}), True)
	check('duplicate disassembly address', lambda: s.disassembly(text + text), True)
	check('aliases preserved', lambda: require(len(s.symbols('100 3 t one\n100 3 t two')[0x100, 3]) == 2))
	check('unsupported symbol format', lambda: s.symbols('not an nm table'), True)
	shifted = copy.deepcopy(xs)
	for r in shifted:
		r['address'] += 0x80
	shifted[1]['operand'] = '180 <foo>'
	check('relocated local branch equality', lambda: require(s.normalized(xs, 0x100, 3, {}) == s.normalized(shifted, 0x180, 3, {})))
	changed = copy.deepcopy(xs)
	changed[0]['op'] = 'pause'
	check('opcode change survives', lambda: require(s.normalized(xs, 0x100, 3, {}) != s.normalized(changed, 0x100, 3, {})))
	for name, one, two in [('register', '%rax,%rbx', '%rax,%rcx'), ('immediate', '$4,%rax', '$8,%rax'), ('dependency', '(%rax),%rax', '(%rbx),%rax')]:
		a, b = copy.deepcopy(xs), copy.deepcopy(xs)
		a[0].update(op='mov', operand=one)
		b[0].update(op='mov', operand=two)
		check(name + ' change survives', lambda a=a,b=b: require(s.normalized(a, 0x100, 3, {}) != s.normalized(b, 0x100, 3, {})))
	call = [{'address': 0x100, 'bytes': 'e800000000', 'length': 5, 'op': 'call', 'operand': '200 <target>'}]
	check('unresolved direct target', lambda: s.normalized(call, 0x100, 5, {}), True)
	check('resolved target', lambda: require(s.normalized(call, 0x100, 5, {0x200: ['raw_target']}) == [['call', 'target:raw_target']]))
	cross = [{'address': 63, 'bytes': '9090', 'length': 2, 'op': 'nop', 'operand': ''}]
	check('64-byte crossing', lambda: require(s.boundary_rows(cross, 63)['instruction_crossings']['64'] == [63]))
	row = {'address': 0x100, 'size': 3, 'demangled_names': ['same'], 'instructions': xs, 'normalized': s.normalized(xs, 0x100, 3, {}), 'bytes_sha256': 'x'}
	check('ambiguous clone not matched', lambda: require(s.compare([row, row], [row])[0]['classification'].startswith('unresolved')))
	check('same name at new address retained', lambda: require(s.compare([row], [{**row,'address': 0x180}])[0]['cand_extents'] == [[0x180,3]]))
	check('NaN counter refused', lambda: s.counter_values(json.dumps({'event':'instructions:u','counter-value':'nan','pcnt-running':'100'})), True)
	check('missing counter refused', lambda: s.counter_values(''), True)
	check('numeric predicted remainder not erased', lambda: require((-11999746 - (-12 * 1000000)) == 254))
	return {'completed': True, 'controls': out, 'count': len(out)}


if __name__ == '__main__':
	result = run()
	print(json.dumps(result, indent=1))
