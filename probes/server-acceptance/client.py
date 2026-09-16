#!/usr/bin/env python3
"""Separate HTTP client process; commands and observations use JSON lines."""
import concurrent.futures,http.client,json,sys,threading,time
port=int(sys.argv[1]);lock=threading.Lock()
def emit(value):
    with lock:print(json.dumps(value),flush=True)
def request(command):
    started=time.perf_counter_ns();connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        body=command.get('body','hello').encode()
        connection.request('POST',command['path'],body,{'X-Probe-Tag':command['tag']})
        response=connection.getresponse();payload=response.read()
        emit({'tag':command['tag'],'status':response.status,'body_hex':payload.hex(),
              'started_ns':started,'ended_ns':time.perf_counter_ns()})
    except BaseException as error:emit({'tag':command['tag'],'error':repr(error)})
    finally:connection.close()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    emit({'ready':True})
    for line in sys.stdin:
        command=json.loads(line)
        if command.get('quit'):break
        pool.submit(request,command)
