#!/usr/bin/env python3
"""Record 0039 terminal gates: compare screens/cursors, retain raw traffic.
Run in a venv with requirements.txt, passing the binary and output directory.
Linux PTYs are measured here; this is not Windows execution evidence.
"""
import argparse, errno, fcntl, http.server, json, os, pathlib, pty, select
import struct, subprocess, tempfile, termios, threading, time
import pyte
from PIL import Image, ImageDraw, ImageFont

class Terminal:
    def __init__(self, binary, mode='always', args=(), env=None, pipe_out=False, pipe_err=False):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        self.temp = tempfile.TemporaryDirectory()
        child_env = dict(os.environ, TERM='xterm-256color', RNX_HISTORY=self.temp.name+'/history')
        child_env.pop('NO_COLOR', None)
        for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy'):
            child_env.pop(key, None)
        child_env.update(env or {})
        def terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        self.child = subprocess.Popen([str(binary), '--color='+mode, *args], stdin=slave,
            stdout=subprocess.PIPE if pipe_out else slave,
            stderr=subprocess.PIPE if pipe_err else slave, env=child_env, preexec_fn=terminal)
        os.close(slave)
        self.fds = {self.master: 'tty'}
        if pipe_out: self.fds[self.child.stdout.fileno()] = 'out'
        if pipe_err: self.fds[self.child.stderr.fileno()] = 'err'
        self.raw = dict(tty=b'',out=b'',err=b'')
        self.screen = pyte.Screen(120,40)
        self.stream = pyte.ByteStream(self.screen)
    def pump(self, seconds=.06):
        until = time.monotonic()+seconds
        while time.monotonic()<until:
            ready,_,_ = select.select(list(self.fds),[],[],max(0,until-time.monotonic()))
            for fd in ready:
                try: data=os.read(fd,65536)
                except OSError as e:
                    if e.errno != errno.EIO: raise
                    data=b''
                if not data: del self.fds[fd]; continue
                name=self.fds[fd]; self.raw[name]+=data
                if name=='tty': self.stream.feed(data)
    def until(self, predicate):
        end=time.monotonic()+10
        while not predicate():
            self.pump()
            assert time.monotonic()<end, repr(self.raw)
        self.pump()
    def send(self, text): os.write(self.master,text.encode())
    def prompt(self):
        self.until(lambda: self.screen.display[self.screen.cursor.y].rstrip()=='rnx>')
    def snapshot(self): return (list(self.screen.display), self.screen.cursor.x, self.screen.cursor.y)
    def defaults(self):
        a=self.screen.cursor.attrs
        assert a.fg=='default' and a.bg=='default' and not a.bold, a
    def save(self, path):
        for name,data in self.raw.items():
            if data:
                path.with_suffix('.'+name+'.ansi').write_bytes(data)
                path.with_suffix('.'+name+'.txt').write_text(repr(data)+'\n')
    def close(self):
        if self.child.poll() is None: self.child.kill()
        self.child.wait(timeout=5); os.close(self.master); self.temp.cleanup()

def render(screen, path, light):
    # The ANSI normal colours from Tango, shown on light and dark backgrounds.
    palette=dict(black='#2e3436',red='#cc0000',green='#4e9a06',brown='#c4a000',
                 blue='#3465a4',magenta='#75507b',cyan='#06989a',white='#d3d7cf')
    bg,fg=('#ffffff','#2e3436') if light else ('#202428','#eeeeec')
    regular=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',18)
    bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',18)
    cjk=ImageFont.truetype('/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',18)
    last=max(i for i,row in enumerate(screen.display) if row.strip())
    image=Image.new('RGB',(1368,(last+2)*26+24),bg); draw=ImageDraw.Draw(image)
    for y in range(last+1):
        for x,cell in screen.buffer[y].items():
            if not cell.data.strip(): continue
            color=palette.get(cell.fg,fg)
            draw.text((20+x*11,y*26+12),cell.data,fill=color,font=cjk if any(ord(c)>0x2e80 for c in cell.data) else (bold if cell.bold else regular))
    image.save(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('binary',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
    a=p.parse_args();a.binary=a.binary.resolve();a.output.mkdir(parents=True,exist_ok=True)
    report={}; kept=[]
    try:
        # Same edits in both modes: exact final screen and cursor, never raw redraw equality.
        screens=[]
        for mode in ('never','always'):
            t=Terminal(a.binary,mode);kept.append(t);t.prompt();states=[]
            def state(): t.pump(); t.defaults(); states.append(t.snapshot())
            t.send('le');state()
            if mode=='always': assert t.screen.buffer[t.screen.cursor.y][5].fg=='default'
            t.send('t');state()
            if mode=='always': assert t.screen.buffer[t.screen.cursor.y][5].fg=='magenta'
            t.send('\x7f');state()
            if mode=='always': assert t.screen.buffer[t.screen.cursor.y][5].fg=='default'
            t.send('\x03');t.prompt();state()
            t.send('"x" + 1');state()
            # Home, right three positions, backspace deletes the closing quote.
            t.send('\x01\x1b[C\x1b[C\x1b[C\x7f');state()
            if mode=='always': assert t.screen.buffer[t.screen.cursor.y][10].fg=='green'
            t.send('\x03');t.prompt();state()
            t.send('\x1b[200~"e\u0301界\t"\x1b[201~');state()
            t.send('\x03');t.prompt();state()
            t.send('if true {\n');state()
            t.send('  42\n}\n');t.prompt();state()
            t.send('let 界 = ;\n');t.prompt();state()
            t.send(':reset\n');t.prompt();state()
            before=t.raw['tty']
            block='/*'+'x'*9996+'*/'
            t.send('\x1b[200~'+block+'\x1b[201~');state()
            # One full coloured token, despite chunks in the transport.
            if mode=='always': assert t.raw['tty'][len(before):].count(block.encode())==1
            t.send('\x03');t.prompt();state()
            t.send('println!("SHOULD_NOT_EXECUTE")');state()
            t.send('\x03');t.prompt();state()
            assert not any(row.strip()=='SHOULD_NOT_EXECUTE' for row in t.screen.display)
            t.save(a.output/('edits-'+mode));screens.append(states)
        assert screens[0]==screens[1]
        report['screen_and_cursor']=f'equal at {len(screens[0])} editing checkpoints, raw captures retained'
        # Auto colour respects environmental overrides, including an empty NO_COLOR.
        for env, coloured in [({},True),({'NO_COLOR':'1'},False),({'NO_COLOR':''},True),({'TERM':'dumb'},False)]:
            t=Terminal(a.binary,'auto',('eval','42'),env=env);kept.append(t)
            t.until(lambda:t.child.poll() is not None)
            assert (b'\x1b[36m' in t.raw['tty'])==coloured, t.raw
        t=Terminal(a.binary,'always',('eval','42'),env={'NO_COLOR':'1'});kept.append(t)
        t.until(lambda:t.child.poll() is not None);assert b'\x1b[36m' in t.raw['tty']
        report['switches']='auto terminal, NO_COLOR nonempty/empty, dumb, always override pass'
        for pipe_out,pipe_err in [(True,False),(False,True)]:
            for mode in ('auto','always'):
                t=Terminal(a.binary,mode,pipe_out=pipe_out,pipe_err=pipe_err);kept.append(t)
                prompt_stream='out' if pipe_out else 'tty'
                t.until(lambda:b'rnx> ' in t.raw[prompt_stream])
                t.send('42\n');t.pump(.2)
                t.send('let x = ;\n');t.pump(.2)
                assert (b'\x1b[36m42' in t.raw[prompt_stream])==(mode=='always' or not pipe_out),t.raw
                error_stream='err' if pipe_err else 'tty'
                assert (b'\x1b[1;31m' in t.raw[error_stream])==(mode=='always' or not pipe_err),t.raw
                assert b'\x1b[?2004h' in t.raw[prompt_stream],t.raw
                t.save(a.output/f'mixed-{pipe_out}-{mode}')
        t=Terminal(a.binary,'always',env={'TERM':'dumb'});kept.append(t)
        t.until(lambda:b'rnx> ' in t.raw['tty']);t.send('42\n');t.pump(.2)
        assert b'\x1b[36m42' in t.raw['tty'] and b'\x1b[?2004h' not in t.raw['tty']
        report['mixed_streams']='stdout pipe and stderr pipe, auto/always, editor preserved; dumb direct input pass'
        class Fixture(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                data=b'{"status":"ready","items":[1,2,3]}'
                self.send_response_only(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def log_message(self,*args): pass
        server=http.server.HTTPServer(('127.0.0.1',0),Fixture)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        t=Terminal(a.binary);kept.append(t);t.prompt()
        for line in [f'let reply = http::get("http://127.0.0.1:{server.server_port}").await?; reply',
                     'host::json_parse(reply.body)?',
                     '["café", "e\\u{301}界\\t\\u{1b}[2J", Some(42)]',
                     'if true {\n  [1, 2, 3]\n}', 'let café = ;']:
            t.send(line+'\n');t.prompt()
        t.send('http::\t\t');t.pump(.3);t.defaults()
        t.save(a.output/'specimen')
        render(t.screen,a.output/'specimen-dark.png',False)
        render(t.screen,a.output/'specimen-light.png',True)
        server.shutdown();server.server_close();worker.join()
        report['specimen_screen']=t.screen.display
        report['binary']=str(a.binary)
        (a.output/'terminal.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        for t in kept:t.close()
if __name__=='__main__':main()
