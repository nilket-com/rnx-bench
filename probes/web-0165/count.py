"""Frozen sources and a transparent line census; helpers/content stay byte-identical."""
import ast,hashlib,json,pathlib
here=pathlib.Path(__file__).resolve().parent
old=(here/'main.rn').read_text();new=(here/'routes.rn').read_text()
shared=old[:old.index('pub fn main(request)')]
assert new.startswith(shared)
def count(text,python=False):
 lines=text.splitlines()
 code_lines=lines
 if python:
  first=ast.parse(text).body[0]
  assert isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str)
  code_lines=lines[:first.lineno-1]+lines[first.end_lineno:]
 return {'physical':len(lines),'nonblank':sum(bool(l.strip()) for l in lines),'nonblank_noncomment':sum(bool(l.strip()) and not l.lstrip().startswith(('//','#')) for l in code_lines)}
result={}
for name,text in [('main_total',old),('routes_total',new),('unchanged_helpers_and_content',shared),('main_dispatch',old[len(shared):]),('routes_declarations_and_handlers',new[len(shared):]),('flask_total',(here.parent/'web-0162/c/app.py').read_text())]:
 result[name]={**count(text,python=name=='flask_total'),'sha256':hashlib.sha256(text.encode()).hexdigest()}
print(json.dumps(result,indent=2))
