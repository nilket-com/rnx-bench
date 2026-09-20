"""Shared paths and helpers for the 0069 gate 1 probe: the wrapper name, the build kind and the identity."""
import hashlib, json, os, subprocess, sys, re
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/shared-build-seam-0069'
T = H / 'target'
BASELINE_REV = '339c6e3'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_', 'GIT_'))}
ENV.update(POLARS_MAX_THREADS='1', TERM='xterm-256color', PYTHONDONTWRITEBYTECODE='1')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(name, value):
    O.mkdir(parents=True, exist_ok=True)
    (O / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(argv, cwd=None, timeout=600, check=True, env=None, input=None):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, env=env or ENV, capture_output=True, timeout=timeout, input=input)
    if check and p.returncode != 0:
        raise SystemExit(f'{argv[0]} failed ({p.returncode}):\n{p.stdout.decode(errors="replace")[-3000:]}\n{p.stderr.decode(errors="replace")[-3000:]}')
    return p


def git(root, *args):
    return run(['git', '--no-pager', '-c', 'color.ui=false', '-C', root, '-c', 'user.name=probe', '-c', 'user.email=probe@localhost',
                '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args])


def tool(kind):
    return {
        'candidate': T / 'candidate/tools/project/target/release/rnx-project',
        'candidate-probe': T / 'candidate/tools/project/target/debug/rnx-project-assembly-probe',
        'baseline': T / 'baseline-tool/release/rnx-project',
    }[kind]


def origin():
    """The fixture Git origin (the baseline tree) and its revision."""
    d = json.loads((O / 'prepare.json').read_text())
    return d['origin_url'], d['origin_rev']


def project(name, natives, runtime=None, extra=None, seed=None):
    """A format-2 project declaring the fixture origin; natives is [(name, package, hook, fields)]."""
    url, rev = origin()
    d = T / 'projects' / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    text = 'format = 2\n[application]\nentry = "main.rn"\n'
    text += runtime if runtime is not None else f'[runtime]\ngit = "{url}"\nrev = "{rev}"\n'
    for n, package, hook, fields in natives:
        text += f'\n[native.{n}]\ngit = "{url}"\nrev = "{rev}"\npackage = "{package}"\nbuilder = "build"\nhook = "{hook}"\n{fields}'
    if extra:
        text += extra
    (d / 'rnx.toml').write_text(text)
    return d


def identity_of(d):
    lock = json.loads((d / 'rnx.lock').read_text())
    return json.loads(lock['assembly']['identity'])


def env_for(cache, cargo_home=None):
    e = dict(ENV, RNX_PROJECT_CACHE=str(cache), RNX_HISTORY=str(T / 'history'), RNX_CONFIG=str(T / 'absent-config'))
    if cargo_home:
        e['CARGO_HOME'] = str(cargo_home)
    return e


def package_name(manifest):
    return re.search(r'^name = "([^"]+)"', manifest, re.M).group(1)
