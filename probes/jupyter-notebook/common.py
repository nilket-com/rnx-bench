import json,os,pathlib,shutil,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/jupyter-0047-notebook';OUT.mkdir(exist_ok=True)
VENV=ROOT/'probes/jupyter-notebook/.venv'
class Environment:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rnx notebook acceptance ')
        self.root=pathlib.Path(self.temp.name);self.bin=self.root/'bin with spaces';self.bin.mkdir()
        self.kernel=self.bin/'rnx-jupyter';self.worker=self.bin/'rnx'
        shutil.copy2(ROOT.parent/'rnx/jupyter/target/release/rnx-jupyter',self.kernel)
        shutil.copy2(ROOT.parent/'rnx/target/release/rnx',self.worker)
        self.env=os.environ.copy()
        for key in list(self.env):
            if key.startswith(('JUPYTER','IPYTHON','RNX_')) or key.lower().endswith('_proxy'):self.env.pop(key,None)
        self.env.update(PATH=str(VENV/'bin')+os.pathsep+self.env.get('PATH',''),HOME=str(self.root),JUPYTER_DATA_DIR=str(self.root/'data'),JUPYTER_CONFIG_DIR=str(self.root/'config'),JUPYTER_RUNTIME_DIR=str(self.root/'runtime'),JUPYTER_PREFER_ENV_PATH='0',PYTHONDONTWRITEBYTECODE='1')
        self.notebooks=self.root/'notebooks';self.notebooks.mkdir()
    def install(self,replace=False):
        command=[str(self.kernel),'install','--rnx',str(self.worker)]+(['--replace'] if replace else [])
        return subprocess.run(command,env=self.env,capture_output=True,text=True,timeout=30)
    def close(self):self.temp.cleanup()
def log(case,**data):print(json.dumps(dict(case=case,**data)),flush=True)
