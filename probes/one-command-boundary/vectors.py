from common import *
import copy,sys
V=P/'vectors';V.mkdir(exist_ok=True);exe=T/'schema-tool/target/debug/rnx-project-assembly-probe';tmp=T/'vector-input';out=T/'vector-output';records={};cases=[]
def enc(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
def call(kind,b,ok=True):
 tmp.write_bytes(b);p=run([exe,'schema',kind,tmp,out],ok=ok)
 return (out.read_bytes(),p.stdout.decode().strip()) if p.returncode==0 else (None,p.stderr.decode())
def vector(name,kind,data):
 b,h=call(kind,data)
 records[name]={'kind':kind,'sha256':sha(b),'blake3':h}
 if '--record-vectors' in sys.argv:(V/name).write_bytes(data)
 else:assert (V/name).read_bytes()==data,(name,'vector changed')
 assert call(kind,(V/name).read_bytes())[0]==b
 return b,h
url='https://github.com/nilket-com/rnx';rev='1'*40
loc={'git':url,'rev':rev};path={'path':'/fixture/runtime'}
# Existing, canonical path identity is passed through the untouched decoder.
native={'platform':'linux','packages':[{'id':'path-runtime','name':'rnx','manifest':'/fixture/runtime/Cargo.toml','root':'/fixture/runtime'}],'trees':[{'root':'/fixture/runtime','blake3':'b'*64,'files':[{'path':'Cargo.toml','executable':False,'bytes':8,'blake3':'c'*64}]}],'external':[{'path':'/fixture/config.toml','file':None}]}
ctx={'cache_root':'/fixture/cache','cargo_home':'/fixture/cargo','rustup_home':None,'rustup_toolchain':None,'rustc':'rustc fixture','cargo':'cargo fixture','target':'x86_64-unknown-linux-gnu','profile':'release','features':['count-allocations','project-sources']}
oldid={'format':2,'generator':2,'context':ctx,'manifest':'[dependencies.rnx]\npath="/fixture/runtime"\n','main':'fn main(){rnx::main_with(rnx::Extensions::none())}','cargo_lock_blake3':'a'*64,'native':native}
oldbytes,oldkey=vector('path.identity.json','identity',enc(oldid))
decl={'format':1,'application':{'entry':'main.rn'},'runtime':path,'sources':{},'native':{}}
olddecl='format=1\n[application]\nentry="main.rn"\n[runtime]\npath="/fixture/runtime"\n'
vector('path.manifest.toml','declaration',olddecl.encode())
sources={'format':1,'entry':'/fixture/app/main.rn','mounts':[]};source={'packages':[],'trees':[],'outside_manifests':[]}
oldlock={'format':3,'declarations':decl,'sources':sources,'inputs':{'source':source,'native':native},'assembly':{'kind':'shared','identity':oldbytes.decode()}}
_,lockhash=vector('path.lock.json','lock',enc(oldlock))
stamp={'bytes':42,'mtime_seconds':1,'mtime_nanoseconds':2,'executable':True,'device':3,'inode':4}
oldrec={'format':4,'assembly_key':oldkey,'lock_blake3':lockhash,'executable_blake3':'d'*64,'stamp':stamp}
vector('path.receipt.json','receipt',enc(oldrec));oldready={'format':2,'key':oldkey,'identity':oldbytes.decode(),'executable_blake3':'d'*64,'artifact':'artifacts/'+'d'*64};vector('path.ready.json','ready',enc(oldready))
# Git-only identity keeps context, external audit and canonical checkout locations.
gitpkg={'id':'git-runtime','name':'rnx','url':url,'revision':rev,'checkout':'/fixture/cargo/git/checkouts/rnx/1111111','manifest':'Cargo.toml'}
gitnative={'platform':'linux','packages':[],'trees':[],'external':native['external']}
newid={'format':3,'generator':3,'context':ctx,'manifest':f'[dependencies.rnx]\ngit="{url}"\nrev="{rev}"\ndefault-features=false\nfeatures=["count-allocations","project-sources"]\n','main':oldid['main'],'cargo_lock_blake3':'a'*64,'native':gitnative,'git':[gitpkg]}
newbytes=call('canonical-identity',enc(newid))[0];newbytes,newkey=vector('git.identity.json','identity',newbytes)
gitdecl={'format':2,'application':{'entry':'main.rn'},'runtime':loc,'sources':{},'native':{}}
gittext=f'format=2\n[application]\nentry="main.rn"\n[runtime]\ngit="{url}"\nrev="{rev}"\n'
vector('git.manifest.toml','declaration',gittext.encode())
newlock={'format':4,'declarations':gitdecl,'sources':sources,'inputs':{'source':source,'native':gitnative},'git':[gitpkg],'assembly':{'kind':'shared','identity':newbytes.decode()}}
_,nh=vector('git.lock.json','lock',enc(newlock));newrec={'format':5,'assembly_key':newkey,'lock_blake3':nh,'executable_blake3':'d'*64,'stamp':stamp}
vector('git.receipt.json','receipt',enc(newrec));newready={'format':3,'key':newkey,'identity':newbytes.decode(),'executable_blake3':'d'*64,'artifact':'artifacts/'+'d'*64};vector('git.ready.json','ready',enc(newready))
# Explicit mixed source vector and format-2 path/override declarations.
mix=copy.deepcopy(newid);mix['native']=native;mix['manifest']=f'[dependencies.rnx]\npath="/fixture/runtime"\n[dependencies.native_0]\npackage="rnx-polars"\ngit="{url}"\nrev="{rev}"\n';mix['git'][0].update(id='git-polars',name='rnx-polars',manifest='adapters/polars/Cargo.toml')
mixbytes=call('canonical-identity',enc(mix))[0];vector('mixed.identity.json','identity',mixbytes)
mt=f'format=2\n[application]\nentry="main.rn"\n[runtime]\npath="/fixture/runtime"\n[native.polars]\ngit="{url}"\nrev="{rev}"\npackage="rnx-polars"\nbuilder="build"\nhook="plain"\n'
md=json.loads(vector('mixed.manifest.toml','declaration',mt.encode())[0]);ml=copy.deepcopy(newlock);ml.update(declarations=md,git=mix['git'],assembly={'kind':'shared','identity':mixbytes.decode()});ml['inputs']['native']=native;vector('mixed.lock.json','lock',enc(ml))
vector('path2.manifest.toml','declaration',olddecl.replace('format=1','format=2').encode())
vector('override.manifest.toml','declaration',b'format=2\n[application]\nentry="main.rn"\n[executable]\npath="/fixture/rnx"\n')
# Mutations use full candidate validation, including binding and canonical order.
def refuse(name,kind,b):
 result,err=call(kind,b,False);assert result is None,(name,'accepted')
 cases.append({'case':name,'reason':err.strip()})
def mutate(name,kind,obj,fn):
 o=copy.deepcopy(obj);fn(o);refuse(name,kind,enc(o))
for kind,obj in [('identity',newid),('lock',newlock),('receipt',newrec),('ready',newready)]:
 mutate(kind+'-version',kind,obj,lambda x:x.update(format=99))
 mutate(kind+'-unknown',kind,obj,lambda x:x.update(unknown=True))
 refuse(kind+'-duplicate-field',kind,enc(obj).replace(b'"format":',b'"format":99,"format":',1))
for label,edit in [('partial-rev',lambda s:s.replace(rev,'1234')),('no-rev',lambda s:s.replace(f'rev="{rev}"\n','')),('path-and-git',lambda s:s+'path="/fixture/runtime"\n'),('branch',lambda s:s+'branch="main"\n'),('unknown',lambda s:s+'extra=true\n'),('bad-url',lambda s:s.replace(url,'../local'))]:refuse(label,'declaration',edit(gittext).encode())
refuse('source-remains-path','declaration',(gittext+f'[sources.lib]\ngit="{url}"\nrev="{rev}"\n').encode())
refuse('legacy-rejects-git','declaration',gittext.replace('format=2','format=1').encode())
refuse('duplicate-alias','declaration',(mt+mt[mt.index('[native.polars]'):]).encode())
refuse('identity-noncanonical','identity',newbytes+b'\n')
mutate('identity-generator','canonical-identity',newid,lambda x:x.update(generator=2))
mutate('git-duplicate-id','canonical-identity',newid,lambda x:x['git'].append(copy.deepcopy(x['git'][0])))
mutate('git-short-rev','canonical-identity',newid,lambda x:x['git'][0].update(revision='1234'))
mutate('git-relative-checkout','canonical-identity',newid,lambda x:x['git'][0].update(checkout='relative'))
mutate('git-traversal','canonical-identity',newid,lambda x:x['git'][0].update(manifest='../Cargo.toml'))
mutate('git-cache-overlap','canonical-identity',newid,lambda x:x['git'][0].update(checkout='/fixture/cache/input'))
mutate('git-source-partition','canonical-identity',newid,lambda x:x['native']['external'].append({'path':gitpkg['checkout']+'/Cargo.toml','file':None}))
mutate('git-wrapper-revision','canonical-identity',newid,lambda x:x.update(manifest=x['manifest'].replace(rev,'2'*40)))
mutate('features-duplicate','canonical-identity',newid,lambda x:x['context']['features'].append('project-sources'))
mutate('lock-coordinate-binding','lock',newlock,lambda x:x['declarations']['runtime'].update(rev='2'*40))
mutate('lock-package-binding','lock',newlock,lambda x:x['git'][0].update(name='wrong'))
mutate('receipt-nanoseconds','receipt',newrec,lambda x:x['stamp'].update(mtime_nanoseconds=1000000000))
mutate('receipt-no-stamp','receipt',newrec,lambda x:x.pop('stamp'))
mutate('ready-key','ready',newready,lambda x:x.update(key='e'*64))
mutate('ready-traversal','ready',newready,lambda x:x.update(artifact='../elsewhere'))
for kind,obj in [('identity',oldid),('lock',oldlock),('receipt',oldrec),('ready',oldready)]:mutate('legacy-'+kind+'-unknown',kind,obj,lambda x:x.update(git=[]))
# JSON maps in locks must retain the original duplicate-alias refusal too.
mix_wire=enc(ml);nat=enc(md['native']);dup=b'{'+nat[1:-1]+b','+nat[1:-1]+b'}'
refuse('lock-duplicate-native','lock',mix_wire.replace(nat,dup))
# Every retained context dimension changes the new identity key independently.
key_cases={}
for field in ['cache_root','cargo_home','rustup_home','rustup_toolchain','rustc','cargo','target','profile','features']:
 o=copy.deepcopy(newid);o['context'][field]=(['count-allocations','other','project-sources'] if field=='features' else ('/fixture/rustup' if field=='rustup_home' else str(o['context'][field] or '')+'-changed'))
 b,h=call('canonical-identity',enc(o));assert h!=newkey;key_cases[field]=h
for field in ['main','cargo_lock_blake3']:
 o=copy.deepcopy(newid);o[field]=('e'*64 if field=='cargo_lock_blake3' else o[field]+'\n');b,h=call('canonical-identity',enc(o));assert h!=newkey;key_cases[field]=h
if '--record-vectors' in sys.argv:(V/'index.json').write_text(json.dumps(records,indent=2)+'\n')
else:assert json.loads((V/'index.json').read_text())==records
save('schemas.json',{'vectors':records,'refusals':cases,'key_changes':key_cases,'scope':'typed document readers only; filesystem truth and Cargo workflow integration are later gates'})
print(len(records),'fixed vectors,',len(cases),'refusals,',len(key_cases),'retained key inputs pass',flush=True)
