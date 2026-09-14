#!/usr/bin/env python3
import sys,pathlib,json,re
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'colour'))
from terminal import Terminal
from PIL import Image,ImageDraw,ImageFont
root=pathlib.Path(__file__).resolve().parents[2];out=root/'results/settings_0043'
class Prompt(Terminal):
    def prompt(self):self.until(lambda:self.screen.display[self.screen.cursor.y].rstrip().endswith('] >'))
def render(screen,path,light):
    bg,fg=('#ffffff','#2e3436') if light else ('#202428','#eeeeec')
    regular=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',18);bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',18)
    last=max(i for i,row in enumerate(screen.display) if row.strip());image=Image.new('RGB',(1368,(last+2)*26+24),bg);draw=ImageDraw.Draw(image)
    for y in range(last+1):
        for x,c in screen.buffer[y].items():
            colour='#'+c.fg if re.fullmatch('[0-9a-fA-F]{6}',c.fg) else fg
            draw.text((20+x*11,y*26+12),c.data,fill=colour,font=bold if c.bold else regular)
    image.save(path)
states=[]
for mode in ['never','always']:
    t=Prompt(str(pathlib.Path(sys.argv[1]).resolve()),mode,env={'RNX_CONFIG':str(root/'probes/settings/config.rn')})
    try:
        t.prompt()
        if mode=='always':assert b'\x1b[1;38;2;152;195;121m[1]' in t.raw['tty']
        for line in ['let name = "Rune";','let values = [1, 2, 3];','#{name, values}',':renumber','values','1.missing()']:
            t.send(line+'\r');t.prompt()
        states.append(t.snapshot());t.save(out/mode)
        if mode=='always':
            assert b'\x1b[38;2;198;120;221mlet' in t.raw['tty']
            render(t.screen,out/'specimen-dark.png',False);render(t.screen,out/'specimen-light.png',True)
        t.send(':q\r');t.until(lambda:t.child.poll() is not None)
    finally:t.close()
assert states[0]==states[1]
(out/'terminal.json').write_text(json.dumps({'screen_and_cursor':'equal under never/always','palette':'six configured RGB foregrounds; captured prompt and keyword bytes pinned','specimens':'same RGB requests on two example backgrounds; not a physical appearance guarantee'},indent=2)+'\n')
