#!/usr/bin/env python3
"""Real PTY completion gate without depending on an emulator model."""
import errno, fcntl, json, os, pathlib, pty, re, select, subprocess, sys, tempfile, termios, time
root=pathlib.Path(__file__).resolve().parents[2]
out=root/'results/extensions-0051'
with tempfile.TemporaryDirectory(prefix='rnx extension pty ') as tmp:
    master,slave=pty.openpty()
    def setup():
        os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
    env=dict(os.environ,TERM='xterm-256color',RNX_CONFIG=tmp+'/absent',RNX_HISTORY=tmp+'/history')
    env.pop('RNX_FIXTURE_MARKER',None)
    p=subprocess.Popen([str(pathlib.Path(sys.argv[1]).resolve()),'--color=never','--no-splash'],stdin=slave,stdout=slave,stderr=slave,env=env,preexec_fn=setup)
    os.close(slave);raw=bytearray()
    def until(needle):
        end=time.monotonic()+10
        while needle not in raw:
            assert time.monotonic()<end,(needle,bytes(raw))
            if select.select([master],[],[],.1)[0]:
                data=os.read(master,65536);raw.extend(data)
                if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
    try:
        until(b'[1] >')
        os.write(master,b'fixture::ans\t')
        until(b'fixture::answer')
        os.write(master,b'()\n')
        until(b'[2] >')
        assert b'42' in raw,bytes(raw)
        os.write(master,b':reset\n')
        # Verify completion from the retained inventory after reset too.
        time.sleep(.1)
        os.write(master,b'fixture::lat\t')
        until(b'fixture::later')
        os.write(master,b'(1).await?\n')
        time.sleep(.1)
        os.write(master,b':q\n');p.wait(timeout=10)
        while select.select([master],[],[],.05)[0]:
            try:data=os.read(master,65536)
            except OSError as e:
                if e.errno==errno.EIO:break
                raise
            if not data:break
            raw.extend(data)
        assert p.returncode==0
        (out/'completion.ansi').write_bytes(raw)
        (out/'completion.json').write_text(json.dumps({'completed_before_reset':'fixture::answer','completed_after_reset':'fixture::later','exit':p.returncode})+'\n')
    finally:
        if p.poll() is None:p.kill();p.wait()
        os.close(master)
print('PTY completion before and after reset passed')
