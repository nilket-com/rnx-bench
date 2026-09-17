#!/usr/bin/env python3
"""Use the real product commands with the accepted PostgreSQL/plain assembly."""
import hashlib,json,os,pathlib,subprocess,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';TOOL=pathlib.Path(os.environ.get('RNX_PROJECT_TOOL',str(ROOT/'tools/project/target/debug/rnx-project')))
OUT=BENCH/'results/adapter-commands-0062/regression/workflow';OUT.mkdir(parents=True,exist_ok=True)
WORK=BENCH/'probes/adapter-commands/target/regression/postgres';WORK.mkdir(parents=True,exist_ok=True)
PLAIN=BENCH/'probes/package-assembly/target/plain';WORDS=BENCH/'probes/package-assembly/target/words'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};ENV.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(WORK/'missing'))
manifest=WORK/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(ROOT))+'\n[sources.words]\npath='+json.dumps(str(WORDS))+'\n[native.local]\npath='+json.dumps(str(PLAIN))+'\npackage="gate-four-plain"\nbuilder="build"\nhook="plain"\n[native.postgres]\npath='+json.dumps(str(ROOT/'adapters/postgres'))+'\npackage="rnx-postgres"\nbuilder="build"\nhook="lifecycle"\n')
ENV['RNX_PROJECT_CACHE']=str(BENCH/'probes/adapter-commands/target/regression/postgres-cache')
sys.path.insert(0,str(HERE.parent/'postgres'));from cluster import Cluster
results={}
with Cluster() as c:
    source='mod words; pub async fn main(args) { let r=postgres::query('+json.dumps(c.url)+', "SELECT $1::text AS text, $2::int8 AS n", [args[0], 39], #{}).await?; [r.rows[0].text, r.rows[0].n+words::one()+local::answer()] }'
    (WORK/'main.rn').write_text(source)
    def run(op,args=(),timeout=600):
        p=subprocess.run([str(TOOL),op,'--manifest',str(manifest),*args],env=ENV,capture_output=True,text=True,timeout=timeout)
        (OUT/('postgres-'+op+'.log')).write_text(p.stdout+p.stderr)
        assert p.returncode==0,(op,p.stdout,p.stderr)
        return p
    run('lock',['--offline']);run('build',['--offline'])
    payload="quotes ' ; SQL \\ 🦀";p=run('run',['--',payload],30);assert json.loads(p.stdout)==[payload,42] and not p.stderr
    results['query']=json.loads(p.stdout);results['lock_sha256']=hashlib.sha256((WORK/'rnx.lock').read_bytes()).hexdigest();results['receipt']=json.loads((WORK/'.rnx/receipt.json').read_text())
    results['visible_files']=sorted(p.name for p in WORK.iterdir() if p.name!='.rnx');assert results['visible_files']==['main.rn','rnx.Cargo.lock','rnx.lock','rnx.toml']
    c.wait_idle();results['postmaster']=c.postmaster
assert not pathlib.Path('/proc',str(results['postmaster'])).exists();results['postmaster_reaped']=True
(OUT/'postgres.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS real lock/build/run, mapped query, receipt and private-cluster cleanup')
