"""Candidate routing policy only; production manifest/parser is unchanged."""
from common import *
def select(env):
 if 'RNX_DEP_RUNTIME' not in env:return {'kind':'git','url':URL,'rev':REV}
 p=Path(env['RNX_DEP_RUNTIME'])
 if not p.is_absolute() or not p.is_dir():raise ValueError('RNX_DEP_RUNTIME must name an absolute existing source root; no Git fallback')
 return {'kind':'path','root':str(p.resolve())}
if __name__=='__main__':
 rows={'default':select({}),'override':select({'RNX_DEP_RUNTIME':str(T/'developer-runtime')})}
 assert rows['default']['kind']=='git' and rows['override']['kind']=='path'
 for bad in ['relative',str(T/'missing-runtime')]:
  try:select({'RNX_DEP_RUNTIME':bad});raise AssertionError('fallback')
  except ValueError as e:rows[bad]=str(e)
 save('selection.json',rows)
