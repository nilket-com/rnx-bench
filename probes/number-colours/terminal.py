#!/usr/bin/env python3
"""0045 terminal specimens; Tango colours, explicit illustrative faint rendering."""
import sys,pathlib,json,re,collections,subprocess,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'colour'))
from terminal import Terminal
import pyte
from PIL import Image,ImageDraw,ImageFont,ImageColor
root=pathlib.Path(__file__).resolve().parents[2]
out=root/'results/number_colours_0045';out.mkdir(parents=True,exist_ok=True)
before,after=[str(pathlib.Path(p).resolve()) for p in sys.argv[1:3]]
# pyte 0.8.2 has no faint field. Extend the cell and retain SGR 2/22/0,
# skipping extended colour parameters so an RGB channel 2 is not an attribute.
Cell=collections.namedtuple('Cell',pyte.screens.Char._fields+('dim',))
class Screen(pyte.Screen):
    @property
    def default_char(self):return Cell(*super().default_char,False)
    def select_graphic_rendition(self,*attrs):
        if not hasattr(self.cursor.attrs, "dim"): self.cursor.attrs=Cell(*self.cursor.attrs,False)
        dim=self.cursor.attrs.dim
        i=0
        if not attrs:dim=False
        while i<len(attrs):
            n=attrs[i];i+=1
            if n in (0,22):dim=False
            elif n==2:dim=True
            elif n in (38,48) and i<len(attrs):
                kind=attrs[i];i+=1
                i+=3 if kind==2 else 1 if kind==5 else 0
        super().select_graphic_rendition(*attrs)
        self.cursor.attrs=self.cursor.attrs._replace(dim=dim)
class Prompt(Terminal):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.screen=Screen(120,40);self.stream=pyte.ByteStream(self.screen)
    def prompt(self):self.until(lambda:self.screen.display[self.screen.cursor.y].rstrip().endswith('] >'))

def render(screen,path,light):
    bg,fg=('#ffffff','#2e3436') if light else ('#202428','#eeeeec')
    palette=dict(black='#2e3436',red='#cc0000',green='#4e9a06',brown='#c4a000',blue='#3465a4',magenta='#75507b',cyan='#06989a',white='#d3d7cf')
    regular=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',18)
    bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',18)
    last=max(i for i,row in enumerate(screen.display) if row.strip())
    image=Image.new('RGB',(1200,(last+2)*26+24),bg);draw=ImageDraw.Draw(image)
    for y in range(last+1):
        for x,c in screen.buffer[y].items():
            colour=('#'+c.fg) if re.fullmatch('[0-9a-fA-F]{6}',c.fg) else palette.get(c.fg,fg)
            if getattr(c,"dim",False):colour=tuple((a+b)//2 for a,b in zip(ImageColor.getrgb(colour),ImageColor.getrgb(bg)))
            draw.text((20+x*11,y*26+12),c.data,fill=colour,font=bold if c.bold else regular)
    image.save(path)

# The extension preserves/reset faint, and RGB channels never select it.
s=Screen(20,2);stream=pyte.Stream(s);stream.feed('\x1b[2m[\x1b[0m\x1b[1;38;2;1;2;3m7\x1b[22m]')
assert s.buffer[0][0].dim and not s.buffer[0][1].dim and s.buffer[0][1].bold
assert not s.buffer[0][2].dim and not s.buffer[0][2].bold
states=[]
for mode in ('never','always'):
    t=Prompt(after,mode,args=['--no-splash'],env={'RNX_CONFIG':str(out/'missing-config')})
    try:
        t.prompt()
        for n in range(1,10): t.send('let x = 41;\r');t.prompt()
        t.send(':clear\r');t.prompt()
        for line in ['x + 1',':renumber','#{name: "Rune", values: [1, 2, 3]}','1.missing()']:
            t.send(line+'\r');t.prompt()
        states.append(t.snapshot());t.save(out/mode)
        if mode=='always':
            raw=t.raw['tty'];assert b'\x1b[1;32m10\x1b[0m' in raw
            assert b'\x1b[1;34m10\x1b[0m' in raw
            assert b'\x1b[2m[\x1b[0m' in raw
            assert b'\x1b[1;31mruntime error' in raw
            render(t.screen,out/'specimen-dark.png',False);render(t.screen,out/'specimen-light.png',True)
        t.send(':q\r');t.until(lambda:t.child.poll() is not None)
    finally:t.close()
assert states[0]==states[1]
# Plain streams, including unsupported-terminal prompt mode, remain exact.
checks=[]
for args,source in [(['run',str(root/'scripts/bare.rn')],b''),(['run',str(root/'scripts/json.rn')],b''),(['eval','42'],b''),(['eval','1.missing()'],b''),(['--no-splash','repl'],b'let x = 42;\nx\n:renumber\nx\n1.missing()\n:q\n')]:
    for term in ['xterm','dumb']:
        pair=[]
        for binary in [before,after]:
            ran=subprocess.run([binary,'--color=never',*args],input=source,capture_output=True,env=dict(os.environ,TERM=term,RNX_CONFIG=str(out/'missing-config'),RNX_HISTORY='/tmp/rnx-0045/specimen-history'))
            pair.append((ran.returncode,ran.stdout,ran.stderr))
        assert pair[0]==pair[1],(args,term,pair)
        checks.append({'args':args,'TERM':term,'exit':pair[0][0],'stdout':pair[0][1].decode(),'stderr':pair[0][2].decode()})
(out/'checks.json').write_text(json.dumps({'screen_and_cursor':'never and always identical','plain_before_after':checks,'palette':'Tango ANSI normal slots, normal and bold DejaVu Sans Mono','faint':'SGR 2 captured and modelled; specimen blends foreground 50% toward background as an illustration, not a physical-terminal measurement','Windows':'not executed'},indent=2)+'\n')
