"""0052 SQL contract against a fresh cluster, with byte/shape assertions."""
import json
import os
import pathlib
import subprocess
import sys
import time
from cluster import Cluster

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIN = ROOT.parent/'rnx/adapters/postgres/target/release/rnx-pg'
OUT = pathlib.Path(os.environ.get('RNX_PG_CONTRACT_OUT', ROOT/'results/postgres-0052-adapter'))
OUT.mkdir(exist_ok=True, parents=True)
results = {}
stock=subprocess.run([str(ROOT.parent/'rnx/target/release/rnx'),'eval','postgres::query("", "", [], #{}).await'],capture_output=True,text=True)
assert stock.returncode==1 and 'Missing item {root}::postgres::query' in stock.stderr,stock
results['stock refusal']=dict(exit=stock.returncode,stdout=stock.stdout,stderr=stock.stderr)

with Cluster() as c:
    env = dict(os.environ, TERM='xterm', NO_COLOR='1', RNX_CONFIG=str(c.root/'absent'), RNX_HISTORY=str(c.root/'history'))
    def run(source):
        r = subprocess.run([str(BIN), 'eval', source], env=env, capture_output=True, text=True, timeout=10)
        assert r.returncode == 0, (source, r.stdout, r.stderr)
        assert not r.stderr, (source, r.stderr)
        return r.stdout.strip()
    def call(sql, params='[]', options='#{}', url=None):
        return f'postgres::query({json.dumps(url or c.url, ensure_ascii=False)}, {json.dumps(sql, ensure_ascii=False)}, {params}, {options}).await'
    def good(name, sql, params='[]'):
        value = json.loads(json.loads(run('json::stringify('+call(sql, params)+'?)?')))
        results[name] = value
        return value
    def bad(name, sql, params='[]', needle='', options='#{}', url=None):
        value = json.loads(run('match '+call(sql, params, options, url)+' { Ok(_) => "unexpected success", Err(e) => format!("Err({})", e) }'))
        assert value.startswith('Err(') and needle in value, (name, value, needle)
        assert 'cannot query ' in value and ' at ' in value, value
        results[name] = value
        assert good(name+' recovery', 'SELECT 1 AS n')['rows'] == [{'n': 1}]
        return value

    c.sql('CREATE TABLE binding(v text); CREATE TABLE ints(v int4); CREATE TABLE affected(v int8); CREATE TABLE unique_values(v int8 UNIQUE); INSERT INTO unique_values VALUES(1)')
    text = '\'); DROP TABLE t; -- "x" \\ 😀'
    assert good('bind insert', 'INSERT INTO binding VALUES($1) RETURNING v', '['+json.dumps(text, ensure_ascii=False)+']')['rows'] == [{'v': text}]
    assert good('bind select', 'SELECT v FROM binding WHERE v=$1', '['+json.dumps(text, ensure_ascii=False)+']')['rows'] == [{'v': text}]
    bad('spliced', "INSERT INTO binding VALUES('"+text+"')", needle='42601')
    for name, sql, param, expected in [
        ('null inferred', 'SELECT $1 AS v', '()', None), ('null typed', 'SELECT $1::int8 AS v', '()', None),
        ('bool', 'SELECT $1 AS v', 'true', True), ('min', 'SELECT $1 AS v', '-9223372036854775808', -9223372036854775808),
        ('max', 'SELECT $1 AS v', '9223372036854775807', 9223372036854775807),
        ('text', 'SELECT $1 AS v', '"x"', 'x'), ('cast', 'SELECT $1::int8 AS v', '7', 7),
        ('negative zero', 'SELECT $1 AS v', '-0.0', -0.0),
    ]:
        assert good(name, sql, '['+param+']')['rows'] == [{'v': expected}]
    assert run('let v = '+call('SELECT $1 AS v', '[-0.0]')+'?.rows[0].v; 1.0 / v == -1.0 / 0.0') == 'true'
    for name, number, condition in [('nan', '0.0 / 0.0', 'v != v'), ('infinity', '1.0 / 0.0', 'v == 1.0 / 0.0'), ('minus infinity', '-1.0 / 0.0', 'v == -1.0 / 0.0')]:
        result = run('let v = '+call('SELECT $1 AS v', '['+number+']')+'?.rows[0].v; '+condition)
        assert result == 'true', (name, result)
        results[name] = result
    binary = 'b"'+''.join('\\x%02x'%i for i in range(256))+'"'
    assert run(call('SELECT $1 AS v', '['+binary+']')+'?.rows[0].v == '+binary) == 'true'
    results['bytes'] = 'all 256 equal'
    good('int4 assignment', 'INSERT INTO ints VALUES($1) RETURNING v', '[42]')
    bad('int4 overflow', 'INSERT INTO ints VALUES($1)', '[2147483648]', '22003')
    bad('nul', 'SELECT $1', '["a\\0b"]', 'parameter 1')
    bad('unsigned', 'SELECT $1', '[1u64]', 'parameter 1')
    bad('more than one statement', 'SELECT 1; SELECT 2', needle='42601')
    bad('count', 'SELECT $1::int8, $2::int8', '[1]', 'parameter count is 1, statement expects 2')
    assert good('unused typed parameter', 'SELECT $1::int8 AS n', '[1,2]')['rows']==[{'n':1}]
    assert good('all unused typed parameters', 'SELECT 1 AS n', '[1]')['rows']==[{'n':1}]
    c.sql("CREATE TABLE supported AS SELECT true b, 2::int2 i2, 4::int4 i4, 8::int8 i8, 1.5::float4 f4, 2.5::float8 f8, 'text'::text t, 'var'::varchar v, 'c'::char(2) c, 'name'::name n, NULL::int8 z, '1969-12-31 23:59:59.999999+00'::timestamptz ts")
    supported = good('types', 'SELECT * FROM supported')
    assert supported['rows'][0] == dict(b=True, i2=2, i4=4, i8=8, f4=1.5, f8=2.5, t='text', v='var', c='c ', n='name', z=None, ts=-1)
    for index, (ty, literal) in enumerate([('numeric','1'),('timestamp',"'2000-01-01'"),('date',"'2000-01-01'"),('uuid',"'00000000-0000-0000-0000-000000000001'"),('int4[]','ARRAY[1]')]):
        table='unsupported_'+str(index)
        c.sql(f'CREATE TABLE {table}(unsupported {ty}); INSERT INTO {table} VALUES({literal}::{ty})')
        bad(ty+' populated', f'SELECT * FROM {table}', needle='unsupported PostgreSQL type')
        c.sql(f'TRUNCATE {table}')
        bad(ty+' empty', f'SELECT * FROM {table}', needle='unsupported PostgreSQL type')
    c.sql('CREATE SEQUENCE duplicate_guard')
    bad('duplicates', "SELECT nextval('duplicate_guard') AS x, 2 AS x", needle='duplicate column')
    assert c.sql('SELECT is_called FROM duplicate_guard').stdout.strip() == 'f'
    for ty in ['json', 'jsonb']:
        sql = "SELECT '{\"n\":18446744073709551615}'::"+ty+' AS v'
        assert run('json::parse('+call(sql)+'?.rows[0].v)?.n == 18446744073709551615u64') == 'true'
        good(ty, sql)
    for name, instant, expected in [('epoch', '1970-01-01 00:00:00+00', 0), ('server minimum', '4713-01-01 00:00:00+00 BC', -210863520000000), ('upper', '9999-12-30 22:00:00.999+00', 253402207200999)]:
        assert good(name, f"SELECT '{instant}'::timestamptz AS ts")['rows'] == [{'ts': expected}]
    assert run('time::rfc3339('+call("SELECT '2024-03-04 05:06:07.008+00'::timestamptz AS ts")+'?.rows[0].ts, "UTC")?') == '"2024-03-04T05:06:07.008Z"'
    for name, instant in [('upper plus microsecond', '9999-12-30 22:00:00.999001+00'), ('infinite timestamp', 'infinity'), ('negative infinite timestamp', '-infinity')]:
        bad(name, f"SELECT '{instant}'::timestamptz AS ts", needle='timestamptz')
    lower = c.sql("SELECT '10000-01-02 01:59:59+00 BC'::timestamptz", check=False)
    assert lower.returncode and 'out of range' in lower.stderr
    results['lower endpoint SQL unavailable'] = lower.stderr
    for name, sql, count in [('select count', 'SELECT generate_series(1,3) AS n', 3), ('insert count', 'INSERT INTO affected VALUES(1) RETURNING v', 1), ('setup count', 'INSERT INTO affected VALUES(2)', 1), ('update count', 'UPDATE affected SET v=v+1', 2), ('ddl count', 'CREATE TABLE ddl(v int8)', 0)]:
        assert good(name, sql)['affected'] == count
    for name, options, needle in [('zero timeout', '#{timeout_ms:0}', 'timeout_ms'), ('large timeout', '#{timeout_ms:90001}', 'timeout_ms'), ('float timeout', '#{timeout_ms:1.5}', 'timeout_ms'), ('unknown', '#{wat:1}', 'wat')]:
        bad(name, 'SELECT 1 AS n', needle=needle, options=options, url='postgresql:///postgres?host=/missing')
    for name, url, sql, needle in [('connect', 'postgresql:///postgres?host=/missing', 'SELECT 1 AS n', 'cannot query'), ('authentication', c.url.replace('///', '//locked:DISTINCTIVE_PASSWORD_MARKER@/'), 'SELECT 1 AS n', '28P01'), ('syntax', c.url, 'SELECT ???', '42601'), ('unique', c.url, 'INSERT INTO unique_values VALUES(1)', '23505'), ('type', c.url, "SELECT $1::int8", '22P02')]:
        value = bad(name, sql, '["abc"]' if name == 'type' else '[]', needle, url=url)
        assert 'DISTINCTIVE_PASSWORD_MARKER' not in value
    bad('tls', 'SELECT 1', needle='sslmode', url=c.url+'&sslmode=require')
    for v in ['verify-ca', 'verify-full']:
        bad(v, 'SELECT 1', needle='sslmode', url=c.url+'&sslmode='+v)
    bad('row limit', 'SELECT generate_series(1,10001) AS n', needle='row 10001')
    start = time.monotonic()
    value = json.loads(run('match '+call('SELECT 1 AS n FROM pg_sleep(5)', options='#{timeout_ms:200}')+' { Ok(_) => "unexpected success", Err(e) => format!("Err({})", e) }'))
    elapsed = time.monotonic()-start
    assert value.startswith('Err(') and ('deadline' in value or '57014' in value), value
    assert elapsed < .3, elapsed
    c.wait_idle()
    results['deadline'] = dict(seconds=elapsed, error=value)
    # Exactly one parameter contributes 16 bytes; output is compared inside Rune
    # to avoid the renderer and worker capture limits becoming this gate's limit.
    sql = 'SELECT repeat(\'x\', $1::int4) AS v'
    n = 8*1024*1024 - len(sql.encode()) - 16 - 16 - 1 - 16
    assert run(call(sql, '['+str(n)+']')+'?.rows[0].v.len() == '+str(n)) == 'true'
    bad('logical limit plus one', sql, '['+str(n+1)+']', 'row 1')
    results['exact charge'] = dict(sql_bytes=len(sql.encode()), parameter=16, row=16, name=1, value_header=16, payload=n, total=8*1024*1024)
    for name, setup, sql_arg, params_arg, needle in [
        ('SQL cap','let s="x"; for _ in 0..21 { let more=s.clone(); s.push_str(more); }','s','[]','SQL exceeds 1048576'),
        ('parameter cap','let p=[]; for _ in 0..1001 { p.push(1); }','"SELECT 1"','p','params exceeds 1000')]:
        expr=f'postgres::query("postgresql:///postgres?host=/missing", {sql_arg}, {params_arg}, #{{}}).await'
        result=json.loads(run(setup+' match '+expr+' { Ok(_) => "wrong", Err(e) => e }'))
        assert needle in result,(name,result)
        results[name]=result
    c.wait_idle()
    results['cleanup'] = dict(directory=str(c.root), postmaster=c.postmaster)
(OUT/'contract.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
print(f'{len(results)} contract observations passed; cluster removed')
