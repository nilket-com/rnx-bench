"""Multi-area path census; all source paths retained, no judgement from commit titles alone."""
import collections,datetime,json,pathlib,subprocess,urllib.request
P=pathlib.Path(__file__).resolve().parent;O=P.parents[1]/'results/rune-base-0168';repo='/home/me/work/rune'
def git(*args):return subprocess.check_output(['git','-C',repo,*args],text=True)
base=git('rev-parse','0.14.2').strip();tip=git('rev-parse','bb8e6937').strip();ids=git('rev-list','--reverse',base+'..'+tip).splitlines();rows=[]
def area(path):
 if path.startswith('crates/rune/src/runtime/'):return 'VM'
 if path.startswith(('crates/rune/src/compile/','crates/rune/src/parse/','crates/rune/src/ast/','crates/rune-macros/','crates/rune/src/indexing/')):return 'compiler'
 if path.startswith('crates/rune/src/fmt/'):return 'fmt'
 if path.startswith('crates/rune-languageserver/'):return 'LSP'
 if path.startswith('crates/rune/src/modules/'):return 'modules'
 if path.startswith(('crates/rune-alloc/','crates/rune-alloc-macros/')):return 'alloc'
 if path.endswith(('Cargo.toml','Cargo.lock')):return 'deps'
 if any(s in path for s in ['/tests/','/benches/','/fixtures/']) or path.startswith(('tests/','benches/','hegel_tests/')):return 'tests'
 return 'other'
for sha in ids:
 date,title=git('show','-s','--format=%cI%n%s',sha).splitlines();paths=git('diff-tree','--no-commit-id','--name-only','-r',sha).splitlines();counts=collections.Counter(area(p) for p in paths);rows.append(dict(sha=sha,date=date,title=title,paths=paths,areas=dict(sorted(counts.items()))))
assert len(rows)==158,len(rows)
counts=collections.Counter(k for r in rows for k in r['areas']);anchors={}
for short in ['7e5e3ab1','20b26957']:
 sha=git('rev-parse',short).strip();anchors[short]=next(r for r in rows if r['sha']==sha)
api=json.load(urllib.request.urlopen('https://crates.io/api/v1/crates/rune'));(O/'crates-rune.json').write_text(json.dumps(api,indent=2)+'\n')
# Upstream tip surveyed read-only, not silently changed into a new candidate base.
up=subprocess.check_output(['git','ls-remote','https://github.com/rune-rs/rune.git','HEAD'],text=True).strip()
(O/'trajectory.json').write_text(json.dumps(dict(base=base,tip=tip,last_commit=git('show','-s','--format=%cI%n%s',tip),upstream_head_survey=up,survey_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),crates_max_stable=api['crate']['max_stable_version'],rows=rows,area_commit_counts=dict(sorted(counts.items())),anchors=anchors),indent=2)+'\n')
print('158 commits; area incidences',dict(counts),'published',api['crate']['max_stable_version'])
