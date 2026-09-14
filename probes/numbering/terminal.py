#!/usr/bin/env python3
"""Record 0040: real PTY numbering, renumbered origins, colours and specimen."""
import argparse,sys,pathlib,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'colour'))
from terminal import Terminal,render
class NumberedTerminal(Terminal):
    def prompt(self, number=None):
        self.until(lambda:self.screen.display[self.screen.cursor.y].rstrip().endswith('rnx>'))
        if number is not None:
            assert self.screen.display[self.screen.cursor.y].rstrip()==f'[{number}] rnx>', self.screen.display

def main():
    p=argparse.ArgumentParser();p.add_argument('binary',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
    a.binary=a.binary.resolve();a.output.mkdir(parents=True,exist_ok=True)
    captures=[];report={}
    for mode in ('never','always'):
        t=NumberedTerminal(a.binary,mode)
        try:
            screens=[]
            t.prompt(1);screens.append(t.snapshot())
            for number,line in enumerate(['let total = 7;', 'let items = [1, 2, 3];', 'fn twice(n) { n * 2 }', 'let old = |v| v.missing_method();'],start=2):
                t.send(line+'\n');t.prompt(number);screens.append(t.snapshot())
            for line,number in [(':renumber',1),('items',2),('old(1)',3),('total + twice(2)',4),(':renumber',1),(':renumber',1),('let broken = ;',2),(':reset',1),(':vars',1)]:
                t.send(line+'\n');t.prompt(number);t.defaults();screens.append(t.snapshot())
            screen='\n'.join(t.screen.display)
            assert 'input 4 of numbering 1' in screen, screen
            assert '[1] [1, 2, 3]' in screen and '[3] 11' in screen, screen
            assert 'error at input 1,' in screen, screen
            t.save(a.output/('session-'+mode))
            captures.append(screens)
            if mode=='always':
                render(t.screen,a.output/'specimen-dark.png',False)
                render(t.screen,a.output/'specimen-light.png',True)
                report['specimen_screen']=t.screen.display
        finally:t.close()
    assert captures[0]==captures[1]
    # The input terminal continues to select the editor even if stdout is
    # redirected; the actual prompt request also selects result markers.
    for mode in ('auto','always'):
        t=NumberedTerminal(a.binary,mode,pipe_out=True)
        try:
            t.until(lambda:b'[1] rnx> ' in t.raw['out'])
            t.send('42\n');t.until(lambda:b'[2] rnx> ' in t.raw['out'])
            raw=t.raw['out']
            if mode=='always':
                assert b'\x1b[1m[1] \x1b[0m\x1b[36m42\x1b[0m' in raw, raw
            else:assert b'[1] 42\n' in raw and b'\x1b[1m' not in raw,raw
            t.save(a.output/('redirected-'+mode))
        finally:t.close()
    report['checkpoints']=len(captures[0]);report['screens_and_cursors']='equal in never and always';report['redirected_stdout']='numbered editor and results, plain in auto and styled in always'
    (a.output/'terminal.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
