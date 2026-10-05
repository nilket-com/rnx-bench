"""Immutable plan receipts bind buffered native records to actual ordered argv."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
def encode(commands):
 return (str(len(commands))+'\n'+''.join(str(len(c))+'\n'+''.join(str(a).encode().hex()+'\n' for a in c) for c in commands)).encode()
def parse(payload,commands):
 lines=payload.decode().splitlines();assert len(lines)==len(commands)*6,'missing/extra resident records'
 rows=[];executed=[]
 for i,c in enumerate(commands):
  record=lines[i*6:(i+1)*6];assert record[0]=='EXEC '+str(i),'resident order/index mismatch'
  argv=[bytes.fromhex(a).decode() for a in record[1].split(' ')];assert argv==list(map(str,c)),'resident command/order mismatch'
  ns=int(record[2]);assert ns>0
  status=int(record[3]);stdout=bytes.fromhex(record[4]);stderr=bytes.fromhex(record[5])
  rows.append(dict(ns=ns,status=status,stdout=stdout,stderr=stderr,raw='\n'.join(record[2:])+'\n'));executed.append(argv)
 return rows,encode(executed)
def run_plan(j,out,commands,label,deadline=120):
 commands=[list(map(str,c)) for c in commands];directory=pathlib.Path(out)/'plans';directory.mkdir(exist_ok=True)
 plan=directory/(label+'.plan');assert not plan.exists(),'duplicate plan label';declared=encode(commands);plan.write_bytes(declared)
 _,so,se=j.run([P/'target/plan-clock',plan],label,deadline=deadline);assert not se
 rows,executed=parse(so,commands);assert executed==declared
 receipt=dict(native_raw=str((j.out/(f'{j.serial:05d}-'+label+'.stdout')).relative_to(out)),plan=str(plan.relative_to(out)),declared_sha256=hashlib.sha256(declared).hexdigest(),executed_sha256=hashlib.sha256(executed).hexdigest(),count=len(rows),commands=commands)
 (directory/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 rawdir=pathlib.Path(out)/'resident-raw';rawdir.mkdir(exist_ok=True)
 for i,r in enumerate(rows):
  raw=rawdir/(label+f'-{i:04d}.stdout');raw.write_text(r.pop('raw'));r['raw']=str(raw.relative_to(out));r['plan']=str((directory/(label+'.json')).relative_to(out));r['index']=i
 return rows
