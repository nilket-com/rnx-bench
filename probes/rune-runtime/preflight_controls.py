"""Fatal source gates run before a sentinel standing in for builds/measurements."""
import pathlib, shutil, tempfile
from runner import preflight,P,ROOT
preflight()
passed=[]
with tempfile.TemporaryDirectory(prefix='rune-preflight-') as d:
 p=pathlib.Path(d);shutil.copytree(P/'fixtures',p/'fixtures')
 def refusal(name,fn):
  invoked=False
  try:
   fn();invoked=True
  except AssertionError:passed.append(name)
  assert not invoked,name+' reached downstream sentinel'
 refusal('wrong-fork-pin',lambda:preflight(fork=ROOT))
 f=p/'fixtures/answer.rn';original=f.read_bytes();f.write_bytes(original+b'\n// drift\n')
 refusal('fixture-drift',lambda:preflight(fixtures=p/'fixtures'))
 f.write_bytes(original)
 f.unlink()
 refusal('fixture-missing',lambda:preflight(fixtures=p/'fixtures'))
 f.write_bytes(original)
 (p/'fixtures/extra.rn').write_text('pub fn main(){42}')
 refusal('fixture-extra',lambda:preflight(fixtures=p/'fixtures'))
 (p/'fixtures/extra.rn').unlink()
 preflight(fixtures=p/'fixtures')
print('PASS: unmodified inputs; '+', '.join(passed)+' refused before downstream sentinel')
