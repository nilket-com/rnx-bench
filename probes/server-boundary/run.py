#!/usr/bin/env python3
"""Private-cluster, real-Rune step-four boundary measurements; no root changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'postgres'))
from cluster import Cluster


def run(argv, *, env=None, timeout=120):
    p = subprocess.Popen(list(map(str, argv)), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except BaseException:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise
    if p.returncode:
        raise RuntimeError(f'{argv}: exit {p.returncode}\n{stdout}\n{stderr}')
    return stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--cpus', default='2,4')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    binary = HERE/'target/release/rnx-server-boundary-probe'
    conditions = dict(date=run(['date', '--iso-8601=seconds']).strip(),
                      platform=platform.platform(), cpus=args.cpus,
                      rustc=run(['rustc', '-Vv']),
                      lscpu=run(['lscpu']),
                      root_head=run(['git', '-C', HERE.parents[2]/'rnx', 'rev-parse', 'HEAD']).strip(),
                      bench_head=run(['git', '-C', HERE, 'rev-parse', 'HEAD']).strip(),
                      binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                      lock_sha256=hashlib.sha256((HERE/'Cargo.lock').read_bytes()).hexdigest(),
                      source_sha256={str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted((HERE/'src').glob('*.rs'))},
                      postgres=run(['/usr/lib/postgresql/18/bin/postgres', '--version']).strip())
    (args.output/'conditions.json').write_text(json.dumps(conditions, indent=2)+'\n')
    summaries = []
    for repeat in range(2):
        output = run(['taskset', '-c', args.cpus, binary, 'scheduling'])
        (args.output/f'scheduling-{repeat}.jsonl').write_text(output)
        rows = [json.loads(line) for line in output.splitlines()]
        assert len(rows) == 35
        for model in sorted({r['model'] for r in rows}):
            samples = [next(o['latency_ms'] for o in r['observations'] if o['id'] == 2)
                       for r in rows if r['model'] == model]
            summaries.append(dict(repeat=repeat, model=model, healthy_median_ms=statistics.median(samples),
                                  healthy_min_ms=min(samples), healthy_max_ms=max(samples)))
        with Cluster() as c:
            c.sql('CREATE TABLE pool_probe (id bigint PRIMARY KEY, n bigint); INSERT INTO pool_probe VALUES (1,0); CREATE TABLE pool_audit (n bigint)')
            env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
            env['PROBE_DATABASE_URL'] = c.url
            output = run(['taskset', '-c', args.cpus, binary, 'pool'], env=env)
            (args.output/f'pool-{repeat}.jsonl').write_text(output)
            rows = [json.loads(line) for line in output.splitlines()]
            assert len(rows) == 4
            remaining = c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'server-probe-%'").stdout.strip()
            assert remaining == '0', remaining
            cleanup = dict(postmaster=c.postmaster, directory=str(c.root), backends=0)
        cleanup.update(postmaster_gone=not Path(f'/proc/{cleanup["postmaster"]}').exists(), directory_gone=not Path(cleanup['directory']).exists())
        assert cleanup['postmaster_gone'] and cleanup['directory_gone']
        (args.output/f'cleanup-{repeat}.json').write_text(json.dumps(cleanup, indent=2)+'\n')
    (args.output/'summary.json').write_text(json.dumps(summaries, indent=2)+'\n')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
