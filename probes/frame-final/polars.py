"""Polars costs on one pinned core: through the generated application's notebook worker,
cells that present, suppress, preview explicitly, collect, and collect-then-present, on a
5-row frame and a 200,000-row frame, randomized and interleaved; and spawn-to-first-prompt
for the `presentation = true` application against the same application without the field."""
from common import *
import random, secrets, statistics as st
term = load('term', B / 'probes/project-interactive/common.py')
cpu = min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {cpu})
projects = json.loads((O / 'projects.json').read_text())
data = T / 'data'
journal = O / 'polars-samples.jsonl'
assert not journal.exists()
rows = []


def record(x):
    rows.append(x)
    with journal.open('a') as f:
        f.write(json.dumps(x) + '\n')


class Worker:
    def __init__(self, exe):
        cr, pw = os.pipe(); pr, cw = os.pipe()
        self.p = subprocess.Popen([exe, 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, cwd=data)
        os.close(cr); os.close(cw)
        self.send = os.fdopen(pw, 'wb', buffering=0)
        self.control = os.fdopen(pr, 'rb', buffering=0)
        self.n = 0
        assert self.reply()['type'] == 'ready'

    def reply(self):
        line = self.control.readline(4 * 1024 * 1024)
        assert line, self.p.stderr.read()[-2000:]
        return json.loads(line)

    def cell(self, source):
        """Wall clock from the request write to the settled reply, acknowledgement excluded."""
        self.n += 1
        msg = json.dumps({'op': 'execute', 'id': self.n, 'source': source, 'nonce': secrets.token_hex(32)}).encode() + b'\n'
        begin = time.perf_counter_ns()
        self.send.write(msg)
        while True:
            r = self.reply()
            if r['type'] == 'settled':
                ns = time.perf_counter_ns() - begin
                self.send.write(json.dumps({'op': 'ack', 'id': self.n}).encode() + b'\n')
                assert r['failure'] is None, (source, r)
                return ns, r

    def close(self):
        self.n += 1
        self.send.write(json.dumps({'op': 'shutdown', 'id': self.n, 'nonce': secrets.token_hex(32)}).encode() + b'\n')
        while self.reply()['type'] != 'settled':
            pass
        self.send.write(json.dumps({'op': 'ack', 'id': self.n}).encode() + b'\n')
        assert self.p.wait(timeout=10) == 0


w = Worker(projects['present']['artifact'])
SCHEMA = '[("region","string"),("item","string"),("qty","i64"),("price","f64")]'
BIG = '[' + ','.join(f'("c{i}","i64")' for i in range(12)) + ']'
ns, _ = w.cell(f'let sales = polars::read_csv("sales.csv", {SCHEMA})?;')
reads = {'sales_read_ms': ns / 1e6}
ns, _ = w.cell(f'let big = polars::read_csv("big.csv", {BIG})?;')
reads['big_read_ms'] = ns / 1e6
cells = {
    'small-present': 'sales',
    'small-suppress': 'let _s = sales;',
    'small-preview': 'sales.preview()?',
    'small-format': 'format!("{sales}").len()',
    'large-present': 'big',
    'large-suppress': 'let _b = big;',
    'large-preview': 'big.preview()?',
    'large-collect': 'let _c = big.lazy().filter(polars::col("c0").gt(polars::lit(1_000_000)?)).collect()?;',
    'large-collect-present': 'big.lazy().filter(polars::col("c0").gt(polars::lit(1_000_000)?)).collect()?',
    'plain-value': '42',
}
texts = {}
for name, source in cells.items():
    for _ in range(3):
        _, r = w.cell(source)
    texts[name] = {'bytes': len((r['text_plain'] or '').encode()), 'render_bounded': r.get('render_bounded'), 'head': (r['text_plain'] or '')[:80]}
assert texts['large-present']['head'].startswith('DataFrame: 200000 rows × 12 columns') and texts['large-present']['bytes'] < 8192
assert texts['large-collect-present']['head'].startswith('DataFrame: 116666 rows × 12 columns'), texts
for repeat in range(2):
    jobs = [(name, i) for name in cells for i in range(30)]
    random.Random(680200 + repeat).shuffle(jobs)
    for name, i in jobs:
        ns, _ = w.cell(cells[name])
        record({'section': 'worker', 'repeat': repeat, 'sample': i, 'cell': name, 'ns': ns})
    print('worker repeat', repeat, 'complete', flush=True)
w.close()
# Spawn to first prompt: the presenting application against the same application without the field.
bins = {'present': projects['present']['artifact'], 'plain': projects['plain']['artifact']}
def prompt(kind):
    begin = time.perf_counter_ns()
    t = term.Terminal([bins[kind], '--no-splash', '--color=never', 'repl'], T, ENV)
    try:
        out = t.read()
        ns = time.perf_counter_ns() - begin
        assert out == '\r[1] > \r', repr(out)
    finally:
        try:
            os.write(t.master, b':q\n'); t.read(False); assert t.p.wait(timeout=5) == 0
        finally:
            t.close()
    return ns
for kind in bins:
    for _ in range(5):
        prompt(kind)
for repeat in range(2):
    jobs = [(kind, i) for kind in bins for i in range(100)]
    random.Random(680300 + repeat).shuffle(jobs)
    for kind, i in jobs:
        record({'section': 'prompt', 'repeat': repeat, 'sample': i, 'cell': kind, 'ns': prompt(kind)})
    print('prompt repeat', repeat, 'complete', flush=True)
summary = {'reads_ms': reads, 'texts': texts, 'worker': {}, 'prompt': {}}
for section in ['worker', 'prompt']:
    names = list(cells) if section == 'worker' else list(bins)
    for name in names:
        per = []
        for repeat in range(2):
            v = sorted(x['ns'] / 1e6 for x in rows if x['section'] == section and x['cell'] == name and x['repeat'] == repeat)
            per.append({'median_ms': st.median(v), 'p10_ms': v[len(v) // 10], 'p90_ms': v[len(v) * 9 // 10]})
        summary[section][name] = per
w_ = summary['worker']
derived = {
    'small_render_ms': [w_['small-present'][r]['median_ms'] - w_['small-suppress'][r]['median_ms'] for r in range(2)],
    'large_render_ms': [w_['large-present'][r]['median_ms'] - w_['large-suppress'][r]['median_ms'] for r in range(2)],
    'large_collect_ms': [w_['large-collect'][r]['median_ms'] - w_['plain-value'][r]['median_ms'] for r in range(2)],
    'large_present_after_collect_ms': [w_['large-collect-present'][r]['median_ms'] - w_['large-collect'][r]['median_ms'] for r in range(2)],
    'prompt_delta_ms': [summary['prompt']['present'][r]['median_ms'] - summary['prompt']['plain'][r]['median_ms'] for r in range(2)],
}
summary['derived'] = derived
save('polars-summary.json', summary)
save('polars-conditions.json', {'cpu': cpu, 'samples': len(rows), 'cells': cells, 'seeds': [680200, 680300], 'warmups': {'worker': 3, 'prompt': 5},
                                'clock': 'worker: request write to settled reply; prompt: PTY create-to-prompt; pinned core, interleaved'})
print(json.dumps({'worker_median_ms': {k: [round(x['median_ms'], 3) for x in v] for k, v in w_.items()}, 'prompt_median_ms': {k: [round(x['median_ms'], 2) for x in v] for k, v in summary['prompt'].items()}, 'derived': {k: [round(x, 3) for x in v] for k, v in derived.items()}}, indent=1), flush=True)
# A bounded render must not scale with the frame: the large render costs about what the small one does.
assert all(abs(large - small) < 5.0 for large, small in zip(derived['large_render_ms'], derived['small_render_ms'])), derived
