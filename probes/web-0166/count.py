"""Rune AST spans categorize declarations; Rune tokens count call-site syntax, including ? in templates."""
import hashlib,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
paths=[HERE/'before.rn',HERE/'after.rn']
p=subprocess.run(['cargo','run','--quiet','--locked','--manifest-path',str(HERE/'census/Cargo.toml'),'--',*map(str,paths)],capture_output=True,text=True,check=True)
data=json.loads(p.stdout)
result={name:{**data[str(path)],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in zip(('before','after'),paths)}
assert result['before']['constants']==result['after']['constants']
assert result['before']['routes']==result['after']['routes']
print(json.dumps(result,indent=2))
