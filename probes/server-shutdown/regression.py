#!/usr/bin/env python3
"""The accepted 57-case HTTP corpus with the server-owned pool enabled."""
import argparse,json,pathlib,sys,hashlib
from wire import Server,run
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'postgres'))
from cluster import Cluster

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args()
    s=None;rows=[]
    with Cluster() as c:
        c.sql('CREATE TABLE audit(tag text NOT NULL)')
        try:
            s=Server(args.output,extra_env={'RNX_POOL_URL':c.url})
            run(s,rows)
        finally:
            if s is not None:s.close()
        end=__import__('time').monotonic()+3
        while c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()!='0':
            assert __import__('time').monotonic()<end
        assert len(rows)==57,len(rows)
        pg=c.postmaster
    assert not pathlib.Path(f'/proc/{pg}').exists()
    (args.output/'results.json').write_text(json.dumps({'cases':rows,'postmaster_reaped':pg,'driver_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    print(f'{len(rows)} wire cases passed with pool enabled')
if __name__=='__main__':main()
