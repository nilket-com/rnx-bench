"""Negative controls for the evidence used by the published column report."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import render_column_0205 as render


class EvidenceControls(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.evidence = render.load()

	def rejected(self, change):
		objects = copy.deepcopy(self.evidence)
		change(*objects)
		with self.assertRaises(AssertionError):
			render.validate(*objects)

	def test_missing_case(self):
		self.rejected(lambda cli, *rest: cli['cases'].pop())

	def test_wrong_path(self):
		self.rejected(lambda cli, *rest: cli['cases'][0]['observations'][0].update(path='scalar-fallback'))

	def test_missing_worker(self):
		self.rejected(lambda cli, *rest: cli['cases'][0]['gdb'].update(workers=[]))

	def test_wrong_checksum(self):
		self.rejected(lambda cli, matched, *rest: matched['records'][0]['data']['samples'][0].update(checksum=0))

	def test_invalid_headline_timing(self):
		self.rejected(lambda cli, matched, *rest: matched['records'][0].update(thermal_stable=False))

	def test_profiled_wall_time_excluded(self):
		cli, matched, *_ = copy.deepcopy(self.evidence)
		before = render.tables(cli, matched)
		for row in matched['records']:
			if row['profiled']:
				row['data']['measured_ns'] = 1
				for sample in row['data'].get('samples', []):
					sample['elapsed_ns'] = 1
		self.assertEqual(render.tables(cli, matched), before)

	def test_cli_thermal_exclusion(self):
		cli, matched, *_ = self.evidence
		matrix = render.tables(cli, matched)[1]
		self.assertEqual(matrix.count('unavailable †'), 6)
		self.assertIn('| <1 | <1 |', matrix)

	def test_changed_archive(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / 'bad.json').write_text('{}')
			(root / 'MANIFEST.json').write_text(json.dumps({'files': {'bad.json': '0' * 64}}))
			with patch.object(render, 'ROOT', root), patch.object(render, 'ARCHIVE', root):
				with self.assertRaisesRegex(AssertionError, 'archive changed'):
					render.load()


if __name__ == '__main__':
	unittest.main()
