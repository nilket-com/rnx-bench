"""Resolve original benchmark inputs from a checksummed, explicit archive."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_INDEX = None


def digest(path):
	h = hashlib.sha256()
	with path.open('rb') as stream:
		while chunk := stream.read(1048576): h.update(chunk)
	return h.hexdigest()


def evidence(relative, root=ROOT):
	local = root/relative
	if not local.resolve().is_relative_to(root.resolve()): raise ValueError('unsafe evidence path')
	if local.is_file(): return local
	global _INDEX
	if _INDEX is None:
		setting = os.environ.get('RNX_DATA_ARCHIVE')
		if not setting: raise ValueError('set RNX_DATA_ARCHIVE to the verified 0240-data archive')
		archive = Path(setting).resolve();index = archive/'INDEX.json'
		catalog = json.loads((ROOT/'ci/data_archive.json').read_text())
		if digest(index) != catalog['index_sha256']: raise ValueError('archive index checksum mismatch')
		_INDEX = archive, {r['path']:r for r in json.loads(index.read_text())['files'] if r['repository']=='rnx-bench'}
	archive, rows = _INDEX
	selected = [r for p,r in rows.items() if p==relative or p.startswith(relative.rstrip('/')+'/')]
	if not selected: raise ValueError('missing archived evidence: '+relative)
	for row in selected:
		path = (archive/row['archive']).resolve()
		if not path.is_relative_to(archive) or digest(path) != row['sha256']: raise ValueError('archive artifact changed: '+row['path'])
	return archive/'files/rnx-bench'/relative
