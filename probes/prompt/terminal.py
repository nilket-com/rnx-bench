#!/usr/bin/env python3
import sys,pathlib,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'colour'))
from terminal import Terminal, render
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
class Prompt(Terminal):
    def prompt(self):self.until(lambda:self.screen.display[self.screen.cursor.y].rstrip().endswith('] >'))
states=[]
for mode in ('never','always'):
    t=Prompt(str(pathlib.Path(sys.argv[1]).resolve()),mode,args=['--no-splash'])
    try:
        t.prompt();t.send('let value = 42;\r');t.prompt()
        t.send(':clear\r');t.prompt()
        assert t.screen.cursor.y==0 and t.screen.display[0].rstrip()=='[2] >',t.snapshot()
        t.send('value\r');t.prompt();assert '[2] 42' in '\n'.join(t.screen.display)
        t.send(':renumber\r');t.prompt();t.send('value + 1\r');t.prompt()
        states.append(t.snapshot());t.save(out/mode)
        if mode=='always':
            render(t.screen,out/'specimen-dark.png',False);render(t.screen,out/'specimen-light.png',True)
        t.send(':q\r');t.until(lambda:t.child.poll() is not None)
        assert t.raw['tty'].count(b'\x1b[23;2t')==1
    finally:t.close()
assert states[0]==states[1]
(out/'terminal.json').write_text(json.dumps({'clear':'cursor at row 0 with input 2; retained value is 42','colour':'equal screens and cursor','titles':'push/set/pop bytes verified; emulator does not implement the title stack'},indent=2)+'\n')
